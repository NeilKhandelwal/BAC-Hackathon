"""eGRID2023 grid carbon intensity and renewable share by subregion, with state rates kept."""
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger

SOURCE = {"name": "EPA eGRID", "version": "eGRID2023 Rev 2",
          "url": "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx"}
RAW = "egrid/egrid2023_data_rev2.xlsx"
SUBREGIONS = "https://www.epa.gov/system/files/other-files/2025-01/egrid2023_subregions.zip"
NOTES = ["Grid carbon and renewable share are eGRID subregion averages (SRL23 sheet: SRCO2RTA, "
         "SRTRPR), assigned by the county's internal point. Annual average rates, not marginal. "
         "State averages are kept in the *_state columns."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)
    download(SUBREGIONS, Path(raw_dir) / "egrid/egrid2023_subregions.zip", 1e6, ZIP_MAGIC)


def _subregion_by_fips(raw_dir):
    gaz = pd.read_csv(Path(raw_dir) / "tiger/2024_Gaz_counties_national.zip", sep="\t", dtype={"GEOID": str})
    gaz.columns = gaz.columns.str.strip()
    points = gpd.GeoDataFrame(gaz[["GEOID"]], geometry=gpd.points_from_xy(gaz.INTPTLONG, gaz.INTPTLAT),
                              crs=4326).to_crs(5070)
    regions = gpd.read_file(Path(raw_dir) / "egrid/egrid2023_subregions.zip").to_crs(5070)
    # Nearest, not within: coastal and island points can sit just outside the polygons.
    joined = gpd.sjoin_nearest(points, regions[["Subregion", "geometry"]])
    return joined.drop_duplicates("GEOID").set_index("GEOID").Subregion


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
    out["grid_co2_lb_mwh"] = out.grid_subregion.map(srl.SRCO2RTA).fillna(out.grid_co2_lb_mwh_state)
    out["grid_renewable_share"] = out.grid_subregion.map(srl.SRTRPR).fillna(out.grid_renewable_share_state)
    return out
