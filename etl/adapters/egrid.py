"""eGRID2023 state-level grid carbon intensity and renewable share, broadcast to counties."""
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger

SOURCE = {"name": "EPA eGRID", "version": "eGRID2023 Rev 2",
          "url": "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx"}
RAW = "egrid/egrid2023_data_rev2.xlsx"
NOTES = ["Grid carbon and renewable share are state averages (ST23 sheet: STCO2RTA, STTRPR), "
         "the same for every county in a state. Annual average rates, not marginal."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)


def build(raw_dir):
    st = pd.read_excel(Path(raw_dir) / RAW, sheet_name="ST23", header=1).set_index("PSTATABB")
    tiger = load_tiger(raw_dir)
    return pd.DataFrame({
        "fips": tiger.GEOID,
        "grid_co2_lb_mwh": tiger.STUSPS.map(st.STCO2RTA),
        "grid_renewable_share": tiger.STUSPS.map(st.STTRPR),  # includes hydro
    })
