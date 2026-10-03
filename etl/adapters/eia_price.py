"""State average industrial retail electricity price from EIA-861, broadcast to counties."""
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger

SOURCE = {"name": "EIA-861 state historical tables", "version": "2024, total electric industry",
          "url": "https://www.eia.gov/electricity/data/state/xls/861/HS861%202010-.xlsx"}
RAW = "eia_price/hs861_2010_onward.xlsx"
NOTES = ["industrial_price_cents_kwh is the 2024 state average industrial retail price "
         "(revenue divided by sales, all providers). It is the same for every county in a state "
         "and is not the rate a large new load would negotiate."]

YEAR = 2024
INDUSTRIAL_PRICE = 13  # column position: Year, STATE, then four columns per sector


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e5, ZIP_MAGIC)


def build(raw_dir):
    sheet = pd.read_excel(Path(raw_dir) / RAW, sheet_name="Total Electric Industry", header=None)
    if list(sheet.iloc[0, 10:14].dropna()) != ["INDUSTRIAL"] or sheet.iloc[2, INDUSTRIAL_PRICE] != "Cents/kWh":
        raise ValueError("EIA-861 state table layout changed; check the industrial price column")
    rows = sheet.iloc[3:]
    price = rows[rows[0] == YEAR].set_index(1)[INDUSTRIAL_PRICE].astype(float)
    tiger = load_tiger(raw_dir)
    return pd.DataFrame({"fips": tiger.GEOID, "industrial_price_cents_kwh": tiger.STUSPS.map(price)})
