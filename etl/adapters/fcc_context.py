"""FCC BDC context: all-technology served share and total serviceable locations. Reads the same
raw file as etl/adapters/fcc_fiber.py and leaves fiber_share_locations alone."""
from pathlib import Path

import numpy as np
import pandas as pd

from etl.adapters import fcc_fiber
from etl.fips import CT_OLD_TO_REGION, ct_rates_to_regions

SOURCE = {**fcc_fiber.SOURCE, "name": "FCC Broadband Data Collection (context fields)",
          "observation_period": "BDC filing in the Esri layer at retrieval",
          "license": "FCC data are public; layer published by Esri", "resolution": "county"}
RAW = fcc_fiber.RAW
NOTES = ["broadband_served_share_locations is the share of serviceable locations served at 100/20 "
         "Mbps or better by any technology. Like fiber_share_locations it is last-mile availability, "
         "not backbone capacity.",
         "broadband_locations_total is a count, so it isn't copied from an old Connecticut county "
         "onto planning regions; it is null for CT."]


def fetch(raw_dir):
    fcc_fiber.fetch(raw_dir)


def build(raw_dir):
    df = pd.read_csv(Path(raw_dir) / RAW, dtype={"GEOID": str})
    total = df.TotalBSLs.replace(0, np.nan)
    shares = ct_rates_to_regions(pd.DataFrame({"fips": df.GEOID,
                                               "broadband_served_share_locations": df.ServedBSLs / total}))
    counts = pd.Series(df.TotalBSLs.values, index=df.GEOID)
    counts = counts[~counts.index.isin(CT_OLD_TO_REGION)]
    shares["broadband_locations_total"] = shares.fips.map(counts).round().astype("Int64")
    return shares
