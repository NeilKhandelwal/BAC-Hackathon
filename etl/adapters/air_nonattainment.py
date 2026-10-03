"""EPA Green Book: counties in nonattainment for 8-hour ozone or PM2.5 in the current year.

Also writes the lookup table data/processed/air_nonattainment.csv.
"""
from pathlib import Path

import pandas as pd

from etl.download import download
from etl.fips import ct_rates_to_regions, load_tiger

SOURCE = {"name": "EPA Green Book", "version": "county nonattainment history, export 2026-09-30",
          "url": "https://www3.epa.gov/airquality/greenbook/downld/phistory.xls"}
RAW = "greenbook/phistory.xls"
NOTES = ["air_nonattainment_count counts ozone and PM2.5 once each when any part of the county "
         "is in nonattainment in 2026 under a standard that is not revoked."]

YEAR = "pw_2026"
LOOKUP = Path("data/processed/air_nonattainment.csv")


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e5, b"\xd0\xcf\x11\xe0")  # OLE2 .xls


def build(raw_dir):
    h = pd.read_excel(Path(raw_dir) / RAW, dtype=str)
    h = h[h[YEAR].notna() & h.revoked_naaqs.isna()]
    h["fips"] = h.fips_state + h.fips_cnty
    ozone = set(h[h.pollutant.str.startswith("8-Hour Ozone")].fips)
    pm25 = set(h[h.pollutant.str.startswith("PM-2.5")].fips)

    flags = pd.DataFrame({"fips": sorted(ozone | pm25)})
    flags["ozone_8hr"] = flags.fips.isin(ozone)
    flags["pm25"] = flags.fips.isin(pm25)
    # The Green Book lists the 8 old Connecticut counties. Regions whose county is unlisted drop.
    flags = ct_rates_to_regions(flags).dropna()
    out = pd.DataFrame({"fips": load_tiger(raw_dir).GEOID}).merge(flags, on="fips", how="left")
    out[["ozone_8hr", "pm25"]] = out[["ozone_8hr", "pm25"]].fillna(False).astype(bool)

    lookup = out[out.ozone_8hr | out.pm25].assign(source_url=SOURCE["url"])
    lookup.to_csv(LOOKUP, index=False)
    return pd.DataFrame({"fips": out.fips, "air_nonattainment_count": out.ozone_8hr.astype(int) + out.pm25.astype(int)})
