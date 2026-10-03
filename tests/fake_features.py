"""Write a fake county table with every core column from docs/schema.md.

Random values with about 5% nulls per column, for running the engine before
the real parquet lands. Usage: python tests/fake_features.py OUT.parquet
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

STATES = ["IA", "TX", "VA", "OR", "AZ", "GA", "OH", "NY", "WA", "NE"]

# column -> generator(rng, n)
NUMERIC = {
    "population": lambda r, n: r.lognormal(10, 1.3, n).round(),
    "land_area_sqkm": lambda r, n: r.lognormal(7, 0.6, n),
    "grid_co2_lb_mwh": lambda r, n: r.uniform(50, 1800, n),
    "grid_renewable_share": lambda r, n: r.uniform(0, 0.9, n),
    "queue_active_mw_total": lambda r, n: r.exponential(800, n),
    "queue_active_mw_clean": lambda r, n: r.exponential(600, n),
    "queue_median_age_years": lambda r, n: r.uniform(0.5, 8, n),
    "queue_withdrawal_rate": lambda r, n: r.uniform(0, 1, n),
    "queue_operational_mw_5y": lambda r, n: r.exponential(100, n),
    "drought_share_weeks_d2plus": lambda r, n: r.uniform(0, 0.6, n),
    "fiber_share_locations": lambda r, n: r.uniform(0, 1, n),
    "plant_capacity_mw_100km": lambda r, n: r.lognormal(8, 1.2, n),
    "plant_clean_capacity_mw_100km": lambda r, n: r.lognormal(7, 1.3, n),
    "dc_existing_count": lambda r, n: r.poisson(0.5, n),
    "dc_existing_mw": lambda r, n: r.exponential(20, n),
    "dc_proposed_count": lambda r, n: r.poisson(0.3, n),
    "dc_proposed_mw": lambda r, n: r.exponential(30, n),
    "median_household_income": lambda r, n: r.normal(65000, 15000, n),
    "cdd_hist": lambda r, n: r.uniform(200, 4000, n),
    "cdd_2050_rcp45": lambda r, n: r.uniform(300, 4500, n),
    "cdd_2050_rcp85": lambda r, n: r.uniform(400, 5000, n),
    "hdd_hist": lambda r, n: r.uniform(500, 9000, n),
    "hdd_2050_rcp85": lambda r, n: r.uniform(400, 8000, n),
    "days_above_95f_hist": lambda r, n: r.uniform(0, 90, n),
    "days_above_95f_2050_rcp85": lambda r, n: r.uniform(0, 120, n),
    "dc_pushback_count": lambda r, n: r.poisson(0.1, n),
    "air_nonattainment_count": lambda r, n: r.choice([0, 0, 0, 1, 2], n),
    "water_permit_risk": lambda r, n: r.choice([0, 1, 2], n),
    "state_policy_risk": lambda r, n: r.choice([0, 1, 2, 3], n),
}
NRI = ["nri_risk_score", "nri_drought_score", "nri_inland_flood_score", "nri_coastal_flood_score",
       "nri_wildfire_score", "nri_hurricane_score", "nri_heat_wave_score", "nri_tornado_score",
       "nri_winter_score"]
FLAGS = ["moratorium_active", "moratorium_pending", "moratorium_state_active", "groundwater_managed_area",
         "state_dc_bill_pending", "state_sales_tax_exemption", "state_large_load_tariff"]


def make(n=300, seed=0, null_share=0.05):
    r = np.random.default_rng(seed)
    df = pd.DataFrame({
        "fips": [f"{i:05d}" for i in range(1001, 1001 + n)],
        "county_name": [f"County {i}" for i in range(n)],
        "state": r.choice(STATES, n),
    })
    df["state_fips"] = df["fips"].str[:2]
    for col, gen in NUMERIC.items():
        df[col] = gen(r, n)
    for col in NRI:
        df[col] = r.uniform(0, 100, n)
    for col in FLAGS:
        df[col] = pd.array(r.random(n) < 0.05, dtype="boolean")
    df["centroid_lat"] = r.uniform(25, 49, n)
    df["centroid_lon"] = r.uniform(-124, -67, n)
    df["pop_density_per_sqkm"] = df["population"] / df["land_area_sqkm"]
    df["heat_sink_score"] = df["hdd_hist"] * np.log1p(df["pop_density_per_sqkm"])
    df["dc_pushback_any"] = pd.array(df["dc_pushback_count"] > 0, dtype="boolean")
    df["permitting_discretionary_risk"] = np.nan  # null until the model runs
    df["permitting_drivers"] = None
    df["water_rights_regime"] = r.choice(["riparian", "prior_appropriation", "hybrid"], n)
    for col in df.columns.drop(["fips", "county_name", "state", "state_fips"]):
        mask = r.random(n) < null_share
        df.loc[mask, col] = None
    return df


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    df = make()
    df.to_parquet(out, index=False)
    missing = ["grid_subregion", "solar_ghi_kwh_m2_day", "wind_speed_100m_ms", "water_stress_bws",
               "water_stress_2050", "grid_water_gal_mwh", "saidi_minutes", "dist_ixp_km", "pct_developed",
               "pct_cropland", "pct_forest_wetland", "pct_protected", "greenhouse_acres"]
    out.with_name(out.stem + ".manifest.json").write_text(json.dumps(
        {"rows": len(df), "sources": [{"name": "fake"}], "columns_present": list(df.columns),
         "columns_missing": missing}, indent=2))
    print(out, len(df))
