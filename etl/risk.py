"""Risk profile of one county: each risk-relevant value and how it compares nationally.

The written assessment is research/risk.md. Reads the committed county table.

Usage: python -m etl.risk [--baseline 51107] [--mw 300] FIPS [FIPS ...]
"""
import argparse

import pandas as pd

from etl import impact

# (risk, column, direction in which the value gets worse)
RISKS = [
    ("Inland flooding", "nri_inland_flood_score", "high"),
    ("Coastal flooding", "nri_coastal_flood_score", "high"),
    ("Hurricane", "nri_hurricane_score", "high"),
    ("Heat wave", "nri_heat_wave_score", "high"),
    ("Winter weather", "nri_winter_score", "high"),
    ("Tornado", "nri_tornado_score", "high"),
    ("Wildfire", "nri_wildfire_score", "high"),
    ("Drought", "nri_drought_score", "high"),
    ("Water stress", "water_stress_bws", "high"),
    ("Water stress 2050", "water_stress_2050", "high"),
    ("Cooling degree days", "cdd_hist", "high"),
    ("Cooling degree days 2050", "cdd_2050_rcp85", "high"),
    ("Days above 95F", "days_above_95f_hist", "high"),
    ("Days above 95F 2050", "days_above_95f_2050_rcp85", "high"),
    ("Power price", "industrial_price_cents_kwh", "high"),
    ("Grid carbon", "grid_co2_lb_mwh", "high"),
    ("Nearby generation", "plant_capacity_mw_100km", "low"),
    ("Queue withdrawal rate", "queue_withdrawal_rate", "high"),
    ("Queue age", "queue_median_age_years", "high"),
    ("Fiber", "fiber_share_locations", "low"),
    ("Existing data centers", "dc_existing_count", "low"),
    ("Workforce", "population", "low"),
    ("Air nonattainment", "air_nonattainment_count", "high"),
    ("Water permit risk", "water_permit_risk", "high"),
    ("State policy risk", "state_policy_risk", "high"),
]


def profile(fips, table=None):
    """One row per risk: the county's value and the share of counties that are better off."""
    table = pd.read_parquet(impact.TABLE) if table is None else table
    county = table.set_index("fips").loc[fips]
    rows = []
    for risk, column, worse in RISKS:
        values = table[column].astype(float)
        value = float(county[column]) if pd.notna(county[column]) else None
        # Share of counties with a strictly better value. Ties don't count against the county.
        better = (values < value) if worse == "high" else (values > value)
        rows.append({"risk": risk, "column": column, "value": value,
                     "worse_than_pct": None if value is None else round(100 * better.sum() / values.notna().sum(), 1)})
    return pd.DataFrame(rows)


def worst(fips, n=3, table=None):
    """The n risks on which the county compares worst nationally."""
    return profile(fips, table).sort_values("worse_than_pct", ascending=False).head(n)


def energy_cost(fips, baseline="51107", mw=300, cooling="dry", table=None):
    """Annual electricity cost at the state industrial price, and the gap to the baseline county."""
    table = pd.read_parquet(impact.TABLE) if table is None else table
    price = table.set_index("fips").industrial_price_cents_kwh
    usd = {f: impact.impact(f, mw, cooling, table=table)["facility_mwh"] * price[f] * 10  # cents/kWh -> $/MWh
           for f in (fips, baseline)}
    return {"usd_per_year": usd[fips], "baseline_usd_per_year": usd[baseline],
            "difference_usd_per_year": usd[fips] - usd[baseline]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fips", nargs="+")
    parser.add_argument("--baseline", default="51107", help="county to compare energy cost against; Loudoun, VA")
    parser.add_argument("--mw", type=float, default=300)
    args = parser.parse_args()
    for fips in args.fips:
        print(fips)
        print(profile(fips).to_string(index=False))
        print({k: round(v) for k, v in energy_cost(fips, args.baseline, args.mw).items()})
