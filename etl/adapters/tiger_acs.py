"""Identity columns from Census TIGER 2024, population and income from ACS 2019-2023."""
from pathlib import Path

import numpy as np
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger

SOURCE = {"name": "Census TIGER and ACS 5-year", "version": "TIGER 2024, ACS 2019-2023",
          "url": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"}
RAW = "tiger/cb_2024_us_county_500k.zip"

GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip"
# The ACS API now needs a key. The table-based summary files don't.
ACS = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-{}.dat"


def fetch(raw_dir):
    raw = Path(raw_dir) / "tiger"
    download(SOURCE["url"], raw / "cb_2024_us_county_500k.zip", 1e6, ZIP_MAGIC)
    download(GAZ, raw / "2024_Gaz_counties_national.zip", 1e5, ZIP_MAGIC)
    for table in ("b01003", "b19013"):
        download(ACS.format(table), raw / f"acsdt5y2023-{table}.dat", 1e6)


def _acs(raw_dir, table):
    df = pd.read_csv(Path(raw_dir) / f"tiger/acsdt5y2023-{table}.dat", sep="|", dtype={"GEO_ID": str})
    df = df[df.GEO_ID.str.startswith("0500000US")]
    values = df[f"{table.upper()}_E001"].astype(float)
    # Negative values are ACS sentinels for suppressed estimates.
    return pd.Series(values.where(values >= 0).values, index=df.GEO_ID.str[-5:])


def build(raw_dir):
    t = load_tiger(raw_dir)
    gaz = pd.read_csv(Path(raw_dir) / "tiger/2024_Gaz_counties_national.zip", sep="\t", dtype={"GEOID": str})
    gaz.columns = gaz.columns.str.strip()
    gaz = gaz.set_index("GEOID")
    out = pd.DataFrame({
        "fips": t.GEOID, "county_name": t.NAME, "state": t.STUSPS, "state_fips": t.STATEFP,
        "population": t.GEOID.map(_acs(raw_dir, "b01003")),
        "land_area_sqkm": t.ALAND / 1e6,
        "centroid_lat": t.GEOID.map(gaz.INTPTLAT), "centroid_lon": t.GEOID.map(gaz.INTPTLONG),
        "median_household_income": t.GEOID.map(_acs(raw_dir, "b19013")),
    })
    out["pop_density_per_sqkm"] = out.population / out.land_area_sqkm.replace(0, np.nan)
    return out
