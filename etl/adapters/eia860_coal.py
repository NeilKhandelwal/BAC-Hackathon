"""EIA-860: retired coal generating capacity by county, a proxy for reusable grid connections."""
import zipfile
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import build_lookup, load_tiger, to_fips

SOURCE = {"name": "EIA-860", "version": "2025 final",
          "url": "https://www.eia.gov/electricity/data/eia860/xls/eia8602025.zip"}
RAW = "eia860/eia8602025.zip"
NOTES = ["coal_retired_mw sums nameplate MW of coal generators with status RE in the EIA-860 "
         "Retired and Canceled sheet. It is 0 for counties with none. Canceled projects are "
         "left out. The sheet covers generators retired since EIA-860 began tracking them."]

COAL = {"BIT", "SUB", "LIG", "ANT", "RC", "WC", "SGC"}
UNMATCHED = []  # (state, county, rows) for retired coal generators that could not be placed


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e7, ZIP_MAGIC)


def build(raw_dir):
    with zipfile.ZipFile(Path(raw_dir) / RAW) as z, z.open("3_1_Generator_Y2025.xlsx") as f:
        r = pd.read_excel(f, sheet_name="Retired and Canceled", header=1)
    coal = r[(r.Status == "RE") & r["Energy Source 1"].isin(COAL)].copy()
    tiger = load_tiger(raw_dir)
    lookup = build_lookup(tiger)
    coal["fips"] = [to_fips(c, s, lookup) for c, s in zip(coal.County, coal.State)]
    missing = coal.fips.isna() & coal.State.isin(set(tiger.STUSPS))
    UNMATCHED[:] = (coal[missing].groupby(["State", "County"], dropna=False).size()
                    .reset_index().itertuples(index=False, name=None))

    out = pd.DataFrame({"fips": tiger.GEOID}).set_index("fips")
    out["coal_retired_mw"] = coal.groupby("fips")["Nameplate Capacity (MW)"].sum()
    return out.fillna(0.0).reset_index()
