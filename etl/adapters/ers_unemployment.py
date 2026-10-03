"""County unemployment rate from BLS LAUS, as republished by USDA ERS."""
from pathlib import Path

import pandas as pd

from etl.download import download
from etl.fips import ct_rates_to_regions

SOURCE = {"name": "USDA ERS county unemployment (BLS LAUS)", "version": "2000-2023 file, 2023 annual average",
          "url": "https://www.ers.usda.gov/media/5497/unemployment-and-median-household-income-for-the-united-states-states-and-counties-2000-23.csv"}
RAW = "ers/unemployment_2000_23.csv"
NOTES = ["Unemployment is the ERS republication of BLS LAUS. www.bls.gov returns 403 to scripts.",
         "ERS reports the 8 old Connecticut counties. Each planning region takes the rate of "
         "the county it mostly overlaps (etl/fips.py CT_REGION_TO_OLD)."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6)


def build(raw_dir):
    ers = pd.read_csv(Path(raw_dir) / RAW, dtype={"FIPS_Code": str}, encoding="latin1")
    rate = ers[ers.Attribute == "Unemployment_rate_2023"]
    rate = rate[~rate.FIPS_Code.str.zfill(5).str.endswith("000")]  # drop US and state rows
    out = pd.DataFrame({"fips": rate.FIPS_Code.str.zfill(5),
                        "unemployment_rate_pct_2023": rate.Value.astype(float)})
    return ct_rates_to_regions(out)
