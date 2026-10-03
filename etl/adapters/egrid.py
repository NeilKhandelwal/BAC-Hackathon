"""eGRID2023 grid carbon intensity and renewable share by subregion, with state rates kept."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger
from etl.schema import CLEAN_SOURCES

SOURCE = {"name": "EPA eGRID", "version": "eGRID2023 Rev 2",
          "url": "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx"}
RAW = "egrid/egrid2023_data_rev2.xlsx"
SUBREGIONS = "https://www.epa.gov/system/files/other-files/2025-01/egrid2023_subregions.zip"
_NOTES = ["Grid carbon and renewable share are eGRID subregion averages (SRL23 sheet: SRCO2RTA, "
         "SRTRPR), assigned by the county's internal point. Annual average rates, not marginal. "
         "State averages are kept in the *_state columns.",
         "plant_capacity_mw_100km sums eGRID plant nameplate MW within 100 km of the county "
         "internal point. Clean means the plant's primary fuel category is wind, solar, hydro, "
         "nuclear, or geothermal. It measures nearby generation, not spare capacity.",
         "eGRID lists US plants only, so the 100 km sum is truncated for counties near Canada or "
         "Mexico and understates their nearby capacity."]
NOTES = list(_NOTES)


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)
    download(SUBREGIONS, Path(raw_dir) / "egrid/egrid2023_subregions.zip", 1e6, ZIP_MAGIC)


RADIUS_KM = 100


def _internal_points(raw_dir):
    gaz = pd.read_csv(Path(raw_dir) / "tiger/2024_Gaz_counties_national.zip", sep="\t", dtype={"GEOID": str})
    gaz.columns = gaz.columns.str.strip()
    return gaz.set_index("GEOID")[["INTPTLAT", "INTPTLONG"]]


def _subregion_by_fips(raw_dir):
    pts = _internal_points(raw_dir)
    points = gpd.GeoDataFrame({"GEOID": pts.index}, geometry=gpd.points_from_xy(pts.INTPTLONG, pts.INTPTLAT),
                              crs=4326).to_crs(5070)
    regions = gpd.read_file(Path(raw_dir) / "egrid/egrid2023_subregions.zip").to_crs(5070)
    # Nearest, not within: coastal and island points can sit just outside the polygons.
    joined = gpd.sjoin_nearest(points, regions[["Subregion", "geometry"]])
    return joined.drop_duplicates("GEOID").set_index("GEOID").Subregion


def _capacity_within_radius(raw_dir, fips):
    """Nameplate MW of plants within RADIUS_KM of each county internal point: total and clean."""
    plants = pd.read_excel(Path(raw_dir) / RAW, sheet_name="PLNT23", header=1,
                           usecols=["LAT", "LON", "NAMEPCAP", "PLFUELCT"]).dropna()
    pts = _internal_points(raw_dir).loc[fips]
    lat1, lon1 = np.radians(pts.INTPTLAT.values)[:, None], np.radians(pts.INTPTLONG.values)[:, None]
    lat2, lon2 = np.radians(plants.LAT.values)[None, :], np.radians(plants.LON.values)[None, :]
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    near = 2 * 6371.0 * np.arcsin(np.sqrt(a)) <= RADIUS_KM
    mw = plants.NAMEPCAP.values
    return near @ mw, near @ (mw * plants.PLFUELCT.str.lower().isin(CLEAN_SOURCES).values)


def build(raw_dir):
    book = Path(raw_dir) / RAW
    st = pd.read_excel(book, sheet_name="ST23", header=1).set_index("PSTATABB")
    srl = pd.read_excel(book, sheet_name="SRL23", header=1).set_index("SUBRGN")
    tiger = load_tiger(raw_dir)
    out = pd.DataFrame({
        "fips": tiger.GEOID,
        "grid_subregion": tiger.GEOID.map(_subregion_by_fips(raw_dir)),
        "grid_co2_lb_mwh_state": tiger.STUSPS.map(st.STCO2RTA),
        "grid_renewable_share_state": tiger.STUSPS.map(st.STTRPR),  # includes hydro
    })
    fallbacks = int(out.grid_subregion.map(srl.SRCO2RTA).isna().sum())
    NOTES[:] = _NOTES + [f"{fallbacks} counties fell back to the state grid rates for lack of a subregion."]
    out["grid_co2_lb_mwh"] = out.grid_subregion.map(srl.SRCO2RTA).fillna(out.grid_co2_lb_mwh_state)
    out["grid_renewable_share"] = out.grid_subregion.map(srl.SRTRPR).fillna(out.grid_renewable_share_state)
    out["plant_capacity_mw_100km"], out["plant_clean_capacity_mw_100km"] = _capacity_within_radius(raw_dir, out.fips)
    return out
