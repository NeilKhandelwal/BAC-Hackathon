"""DOE/NETL Inflation Reduction Act energy communities, 2024 edition, as two county flags."""
from pathlib import Path

import pandas as pd

from etl.arcgis import fetch_csv
from etl.fips import CT_OLD_TO_REGION, ct_rates_to_regions, load_tiger

BASE = "https://arcgis.netl.doe.gov/server/rest/services/Hosted"
SOURCE = {"name": "DOE/NETL IRA Energy Community Data Layers", "version": "2024 (dataset_version 2024.1)",
          "url": f"{BASE}/2024_MSAs_NonMSAs_that_are_Energy_Communities/FeatureServer/0"}
RAW = "netl/msa_energy_communities_2024.csv"
COAL_URL = f"{BASE}/2024_Coal_Closure_Energy_Communities/FeatureServer/0"
NOTES = ["energy_community_coal_closure is true when a census tract in the county had a qualifying "
         "closure itself: a coal mine closed since 1999 or a coal generator retired since 2009 "
         "(453 counties in the table). Tracts that qualify only by adjoining a closure tract don't count. They "
         "would add 364 counties, many across a county or state line from the closure, such as "
         "Loudoun, VA.",
         "energy_community_ffe is true when the county's MSA or non-MSA meets both the fossil fuel "
         "employment threshold and the unemployment test for 2024.",
         "Both layers list only qualifying areas, so absent counties are false, not null. 2024 is "
         "the latest edition NETL publishes. Layers use 2020 geography, so each Connecticut "
         "planning region takes the flag of the old county it mostly overlaps."]


def fetch(raw_dir):
    fetch_csv(SOURCE["url"], Path(raw_dir) / RAW, out_fields="geoid_cty_2020,ec_qual_status",
              order_by="objectid")
    fetch_csv(COAL_URL, Path(raw_dir) / "netl/coal_closure_tracts_2024.csv",
              out_fields="geoid_tract_2020,geoid_county_2020,mine_closure,generator_closure,adjacent_to_closure",
              order_by="objectid")


def build(raw_dir):
    raw = Path(raw_dir) / "netl"
    msa = pd.read_csv(raw / "msa_energy_communities_2024.csv", dtype=str)
    coal = pd.read_csv(raw / "coal_closure_tracts_2024.csv", dtype=str)
    if set(msa.ec_qual_status) != {"Yes"}:
        raise ValueError(f"expected only qualifying counties, got {set(msa.ec_qual_status)}")
    closure = coal[(coal.mine_closure == "Yes") | (coal.generator_closure == "Yes")]
    fips = load_tiger(raw_dir).GEOID
    # Score the old Connecticut counties too, then move them onto planning regions.
    keys = pd.Index(sorted({f for f in fips if not f.startswith("09")} | set(CT_OLD_TO_REGION)))
    out = pd.DataFrame({"fips": keys,
                        "energy_community_coal_closure": keys.isin(set(closure.geoid_county_2020)),
                        "energy_community_ffe": keys.isin(set(msa.geoid_cty_2020))})
    out = ct_rates_to_regions(out)
    out = out[out.fips.isin(set(fips))]
    # The build casts only core columns, so match etl/schema.py's nullable dtype here.
    flags = ["energy_community_coal_closure", "energy_community_ffe"]
    return out.astype({c: "boolean" for c in flags})
