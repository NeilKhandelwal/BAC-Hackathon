"""CMRA degree days and hot days, historical and mid-century. LOCA-downscaled CMIP5."""
from pathlib import Path

import pandas as pd

from etl.arcgis import fetch_csv
from etl.fips import ct_rates_to_regions

SOURCE = {"name": "CMRA climate projections", "version": "LOCA CMIP5, mid-century 2036-2065",
          "url": "https://services3.arcgis.com/0Fs3HcaFfvzXvm7w/arcgis/rest/services/Climate_Mapping_Resilience_and_Adaptation_(CMRA)_Climate_and_Coastal_Inundation_Projections/FeatureServer/0"}
RAW = "cmra/cmra_counties.csv"
NOTES = ["CMRA reports the 8 old Connecticut counties. Each planning region takes the values "
         "of the county it mostly overlaps (etl/fips.py CT_REGION_TO_OLD).",
         "CMRA has no heating degree days for 65 of the coldest counties (ND, MN, CO, and "
         "others). hdd_* and heat_sink_score are null there."]

COLUMNS = {
    "HISTORIC_MEAN_CDD": "cdd_hist", "RCP45MID_MEAN_CDD": "cdd_2050_rcp45",
    "RCP85MID_MEAN_CDD": "cdd_2050_rcp85", "HISTORIC_MEAN_HDD": "hdd_hist",
    "RCP85MID_MEAN_HDD": "hdd_2050_rcp85", "HISTORIC_MEAN_TMAX95F": "days_above_95f_hist",
    "RCP85MID_MEAN_TMAX95F": "days_above_95f_2050_rcp85",
}


def fetch(raw_dir):
    fetch_csv(SOURCE["url"], Path(raw_dir) / RAW, out_fields=",".join(["GEOID", *COLUMNS]))


def build(raw_dir):
    df = pd.read_csv(Path(raw_dir) / RAW, dtype={"GEOID": str}, usecols=["GEOID", *COLUMNS])
    return ct_rates_to_regions(df.rename(columns={"GEOID": "fips", **COLUMNS}))
