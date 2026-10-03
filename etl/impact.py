"""Sustainability impact of one facility in one county: annual CO2 and on-site cooling water.

Formulas, inputs, and the source of every assumption: research/impact.md.

Usage: python -m etl.impact [--mw 300] [--baseline 51107] FIPS [FIPS ...]
"""
import argparse

import pandas as pd

TABLE = "data/processed/county_features.parquet"
HOURS_PER_YEAR = 8760
LB_PER_TONNE = 2204.62
LITRES_PER_GALLON = 3.78541

# Every assumption in one place. research/impact.md gives the source or the reason for each.
LOAD_FACTOR = 0.8  # average IT draw as a share of rated IT load
HOT_CDD = 4000     # Miami-Dade in the county table; stands for IECC climate zone 1A
# cooling -> (value at 0 cooling degree days, value at HOT_CDD), linear in between and beyond
PUE = {"dry": (1.12, 1.38), "evaporative": (1.12, 1.25)}
WUE_L_PER_KWH = {"dry": (0.05, 0.05), "evaporative": (0.1, 1.8)}  # litres per kWh of IT energy
CDD_COLUMN = {"today": "cdd_hist", "2050": "cdd_2050_rcp85"}


def _linear(params, cdd):
    cold, hot = params
    return cold + (hot - cold) * cdd / HOT_CDD


def impact(fips, mw=300, cooling="dry", horizon="today", table=None):
    """Annual energy, CO2, and on-site cooling water for a facility of mw IT load in a county.

    CO2 uses today's grid rate for both horizons; only the climate changes with horizon.
    """
    table = pd.read_parquet(TABLE) if table is None else table
    county = table.set_index("fips").loc[fips]
    cdd = county[CDD_COLUMN[horizon]]
    it_mwh = mw * HOURS_PER_YEAR * LOAD_FACTOR
    pue = _linear(PUE[cooling], cdd)
    facility_mwh = it_mwh * pue
    water_litres = it_mwh * 1000 * _linear(WUE_L_PER_KWH[cooling], cdd)
    return {
        "fips": fips, "county": f"{county.county_name}, {county.state}", "cooling": cooling,
        "horizon": horizon, "cdd": cdd, "grid_co2_lb_mwh": county.grid_co2_lb_mwh,
        "it_mwh": it_mwh, "pue": pue, "facility_mwh": facility_mwh,
        "co2_tonnes": facility_mwh * county.grid_co2_lb_mwh / LB_PER_TONNE,
        "water_million_gal": water_litres / LITRES_PER_GALLON / 1e6,
    }


def compare(fips_list, baseline="51107", mw=300):
    """One row per county, cooling type, and horizon, with differences from the baseline county."""
    table = pd.read_parquet(TABLE)
    rows = []
    for cooling in PUE:
        for horizon in CDD_COLUMN:
            base = impact(baseline, mw, cooling, horizon, table)
            for fips in dict.fromkeys([*fips_list, baseline]):
                row = impact(fips, mw, cooling, horizon, table)
                row["co2_tonnes_vs_baseline"] = row["co2_tonnes"] - base["co2_tonnes"]
                row["water_million_gal_vs_baseline"] = row["water_million_gal"] - base["water_million_gal"]
                rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fips", nargs="+")
    parser.add_argument("--mw", type=float, default=300)
    parser.add_argument("--baseline", default="51107", help="county to difference against; Loudoun, VA")
    args = parser.parse_args()
    result = compare(args.fips, args.baseline, args.mw)
    print(result.round(2).to_string(index=False))
