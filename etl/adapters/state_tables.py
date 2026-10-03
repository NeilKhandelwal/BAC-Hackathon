"""Hand-coded permitting lookup tables: water rights regime, managed groundwater, state policy.

The tables are researched by hand and committed under data/processed/. This adapter only joins
them and derives water_permit_risk and state_policy_risk per docs/schema.md.
"""
from pathlib import Path

import pandas as pd

from etl.fips import load_tiger

SOURCE = {"name": "Hand-coded state permitting tables", "version": "see source_url per row",
          "url": "data/processed/state_policy.csv"}
RAW = "../processed/state_policy.csv"
OPTIONAL = True  # if the tables are absent, the build warns and leaves the columns null
NOTES = ["groundwater_managed_area was researched for Arizona, Texas, and Colorado only. It is "
         "null in the other prior-appropriation and hybrid states, and false in riparian states. "
         "Low-confidence rows (small partial overlaps) count as not managed. A null flag does not "
         "raise water_permit_risk.",
         "state_policy_risk is null for the 13 states where any of its three inputs is unknown.",
         "Water regimes come from a 2016 National Agricultural Law Center table. KS, ND, NE, OR, "
         "and TX are coded hybrid although that source lists them as prior appropriation. A Texas "
         "priority groundwater area triggers a conservation district; it does not restrict "
         "pumping by itself. A false large-load tariff flag is weaker for states outside the EEI "
         "utility list. Most state policy rows are medium or low confidence; see the confidence "
         "column in data/processed/state_policy.csv."]

TABLES = Path("data/processed")
POLICY = ["state_dc_bill_pending", "state_sales_tax_exemption", "state_large_load_tariff"]
REGIME_RISK = {"riparian": 0, "hybrid": 1, "prior_appropriation": 1}
BOOL = {"true": True, "false": False, "yes": True, "no": False, "1": True, "0": False}


def fetch(raw_dir):
    pass  # nothing to download


def build(raw_dir):
    tiger = load_tiger(raw_dir)
    water = pd.read_csv(TABLES / "state_water_regime.csv", dtype=str).set_index("state")
    managed = pd.read_csv(TABLES / "groundwater_managed_counties.csv", dtype={"fips": str})
    policy = pd.read_csv(TABLES / "state_policy.csv", dtype=str).set_index("state")

    out = pd.DataFrame({"fips": tiger.GEOID})
    out["water_rights_regime"] = tiger.STUSPS.map(water.water_rights_regime.str.strip())
    listed = set(managed[managed.confidence.isin(["high", "medium"])].fips.str.zfill(5))
    researched = tiger.STUSPS.isin(set(managed.state)) | (out.water_rights_regime == "riparian")
    out["groundwater_managed_area"] = out.fips.isin(listed).astype("boolean").where(researched)
    risk = out.water_rights_regime.map(REGIME_RISK).astype("Int64")
    out["water_permit_risk"] = risk.mask((risk == 1) & out.groundwater_managed_area.fillna(False), 2)

    for column in POLICY:
        # An empty cell means unknown, not false.
        flags = policy[column].str.strip().str.lower().map(BOOL).astype("boolean")
        out[column] = tiger.STUSPS.map(flags).astype("boolean")
    bill, exempt, tariff = (out[c].astype("Int64") for c in POLICY)
    out["state_policy_risk"] = bill + (1 - exempt) + tariff  # null if any input is null
    return out
