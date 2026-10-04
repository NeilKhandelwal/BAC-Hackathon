"""Census TIGER/Line AIANNH: share of each county inside federally recognized reservations and
off-reservation trust land. A context column; it is not scored."""
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import EXCLUDED_STATE_FIPS

SOURCE = {"name": "Census TIGER/Line American Indian/Alaska Native/Native Hawaiian Areas", "version": "2024",
          "url": "https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip",
          "license": "public domain, US Census Bureau",
          "resolution": "TIGER/Line legal boundaries, intersected with cartographic county polygons in EPSG:5070"}
RAW = "tiger/tl_2024_us_aiannh.zip"
# Federally recognized reservations (D2, D8) and off-reservation trust land (D3, D5). Left out: state
# reservations (D4), statistical areas (D0, D6, D9, E1), and Hawaiian home lands (F1).
CLASSES = ["D2", "D3", "D5", "D8"]
NOTES = ["tribal_land_share is the share of the county polygon inside federally recognized American "
         "Indian reservations or off-reservation trust land (TIGER 2024 AIANNH classes D2, D3, D5, D8), "
         "unioned so overlaps count once. It measures area inside legal boundaries, not tribal "
         "ownership: reservations can contain non-tribal fee land. Statistical areas such as Oklahoma "
         "tribal statistical areas are excluded. TIGER/Line tribal edges against generalized cartographic "
         "county edges leave slivers below 0.01% in some counties (Grant WA reads about 0.0001%). Context "
         "only; not scored."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)


def build(raw_dir):
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)].rename(columns={"GEOID": "fips"})
    counties = counties[["fips", "geometry"]].to_crs(5070)
    areas = gpd.read_file(Path(raw_dir) / RAW)
    areas = areas[areas.CLASSFP.isin(CLASSES)].to_crs(5070)
    areas["geometry"] = areas.geometry.make_valid()
    union = gpd.GeoDataFrame(geometry=[areas.union_all()], crs=5070)
    pieces = gpd.overlay(counties, union, how="intersection", keep_geom_type=True)
    inside = pieces.geometry.area.groupby(pieces.fips.values).sum()
    share = (inside / counties.set_index("fips").area).reindex(counties.fips).fillna(0.0).clip(0, 1)
    return pd.DataFrame({"fips": counties.fips.values, "tribal_land_share": share.values})
