"""Census population estimates: population change from the 2010 census to July 2024."""
from pathlib import Path

import pandas as pd

from etl.download import download
from etl.fips import ct_rates_to_regions

SOURCE = {"name": "Census county population estimates", "version": "Vintage 2020 and Vintage 2024",
          "url": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv"}
RAW = "popest/co-est2024-alldata.csv"
URL_2020 = "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/totals/co-est2020-alldata.csv"
NOTES = ["Population change chains two vintages: 2010 census to the July 2020 estimate "
         "(Vintage 2020), then the 2020 base to July 2024 (Vintage 2024).",
         "Connecticut's 2010-2020 factor comes from the old county each planning region "
         "mostly overlaps (etl/fips.py CT_REGION_TO_OLD)."]


def fetch(raw_dir):
    download(URL_2020, Path(raw_dir) / "popest/co-est2020-alldata.csv", 1e6)
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6)


def _counties(path, columns):
    df = pd.read_csv(path, encoding="latin1", dtype={"STATE": str, "COUNTY": str},
                     usecols=["SUMLEV", "STATE", "COUNTY", *columns])
    df = df[df.SUMLEV == 50]
    # Vintage 2020 writes "X" for two Alaska areas created after 2010.
    df[columns] = df[columns].apply(pd.to_numeric, errors="coerce")
    return df.assign(fips=df.STATE + df.COUNTY)


def build(raw_dir):
    raw = Path(raw_dir) / "popest"
    v20 = _counties(raw / "co-est2020-alldata.csv", ["CENSUS2010POP", "POPESTIMATE2020"])
    v24 = _counties(raw / "co-est2024-alldata.csv", ["ESTIMATESBASE2020", "POPESTIMATE2024"])
    # The two vintages use different Connecticut geography, so chain growth factors, not counts.
    g1 = ct_rates_to_regions(v20.assign(g=v20.POPESTIMATE2020 / v20.CENSUS2010POP)[["fips", "g"]])
    g2 = v24.POPESTIMATE2024 / v24.ESTIMATESBASE2020
    g = g1.set_index("fips").g * pd.Series(g2.values, index=v24.fips)
    return pd.DataFrame({"fips": g.index, "pop_change_pct_2010_2024": 100 * (g.values - 1)})
