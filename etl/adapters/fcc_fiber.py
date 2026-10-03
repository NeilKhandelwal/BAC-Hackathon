"""Share of broadband serviceable locations with fiber, from the Esri mirror of FCC BDC."""
from pathlib import Path

import numpy as np
import pandas as pd

from etl.arcgis import fetch_csv
from etl.fips import ct_rates_to_regions

SOURCE = {"name": "FCC Broadband Data Collection (Esri Living Atlas county layer)",
          "version": "December 2024",
          "url": "https://services8.arcgis.com/peDZJliSvYims39Q/arcgis/rest/services/FCC_Broadband_Data_Collection_December_2024_View/FeatureServer/1"}
RAW = "fcc/fcc_county.csv"
NOTES = ["fiber_share_locations measures last-mile fiber, a proxy for backbone access."]


def fetch(raw_dir):
    fetch_csv(SOURCE["url"], Path(raw_dir) / RAW)


def build(raw_dir):
    df = pd.read_csv(Path(raw_dir) / RAW, dtype={"GEOID": str})
    share = df.ServedBSLsFiber / df.TotalBSLs.replace(0, np.nan)
    return ct_rates_to_regions(pd.DataFrame({"fips": df.GEOID, "fiber_share_locations": share}))
