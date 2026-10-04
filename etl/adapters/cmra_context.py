"""CMRA context: RCP4.5 heating degree days and hot days, and days above 100F. Same service
and Connecticut handling as etl/adapters/cmra.py, which this module leaves alone."""
from pathlib import Path

import pandas as pd

from etl.adapters import cmra
from etl.arcgis import fetch_csv
from etl.fips import ct_rates_to_regions

SOURCE = {**cmra.SOURCE, "name": "CMRA climate projections (context fields)",
          "observation_period": "historic and mid-century LOCA CMIP5 periods as in cmra.py",
          "license": "Public (NOAA / U.S. Global Change Research Program / Esri)",
          "resolution": "county (2019 vintage; CT old counties re-keyed to planning regions)"}
RAW = "cmra/cmra_counties_context.csv"
NOTES = ["hdd_2050_rcp45, days_above_95f_2050_rcp45, and the days_above_100f_* columns come from the "
         "same CMRA layer as the scored climate columns. LOCA-downscaled CMIP5, not CMIP6."]
COLUMNS = {"RCP45MID_MEAN_HDD": "hdd_2050_rcp45", "RCP45MID_MEAN_TMAX95F": "days_above_95f_2050_rcp45",
           "HISTORIC_MEAN_TMAX100F": "days_above_100f_hist", "RCP45MID_MEAN_TMAX100F": "days_above_100f_2050_rcp45",
           "RCP85MID_MEAN_TMAX100F": "days_above_100f_2050_rcp85"}


def fetch(raw_dir):
    fetch_csv(cmra.SOURCE["url"], Path(raw_dir) / RAW, out_fields=",".join(["GEOID", *COLUMNS]))


def build(raw_dir):
    df = pd.read_csv(Path(raw_dir) / RAW, dtype={"GEOID": str}, usecols=["GEOID", *COLUMNS])
    df = df.rename(columns={"GEOID": "fips", **COLUMNS})
    for c in COLUMNS.values():
        df[c] = pd.to_numeric(df[c], errors="coerce").where(lambda v: v >= 0)
    return ct_rates_to_regions(df)
