"""WRI Aqueduct 4.0 water stress: baseline and 2050 business as usual, area-weighted to counties."""
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import EXCLUDED_STATE_FIPS

SOURCE = {"name": "WRI Aqueduct 4.0", "version": "2023-07-05 release",
          "url": "https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip"}
RAW = "aqueduct/aqueduct-4-0-water-risk-data.zip"
GDB = "aqueduct/Aqueduct40_waterrisk_download_Y2023M07D05/GDB/Aq40_Y2023D07M05.gdb"
NOTES = ["water_stress_bws and water_stress_2050 are Aqueduct scores on the 0-5 category scale "
         "(bws_score and bau50_ws_x_s), not the raw withdrawal ratio: 0-1 low, 1-2 low-medium, "
         "2-3 medium-high, 3-4 high, 4-5 extremely high. Aqueduct scores 'arid and low water "
         "use' basins as 5. Each county takes the area-weighted mean over the part of it that "
         "has data. 2050 is the business-as-usual scenario.",
         "Water stress is flat to 2050 for many counties because the score saturates: 727 of the "
         "1,254 US basins have identical baseline and 2050 scores, and every one of them sits at "
         "0 or at the cap of 5. Elsewhere the raw withdrawal ratio rises by a median of 10 "
         "percent. Both layers use the same basins and the same score definition."]

# layer -> (score field, output column)
LAYERS = {"baseline_annual": ("bws_score", "water_stress_bws"),
          "future_annual": ("bau50_ws_x_s", "water_stress_2050")}


def fetch(raw_dir):
    archive = download(SOURCE["url"], Path(raw_dir) / RAW, 1e8, ZIP_MAGIC, timeout=900)
    if not (Path(raw_dir) / GDB).exists():
        with zipfile.ZipFile(archive) as z:
            z.extractall(Path(raw_dir) / "aqueduct", [n for n in z.namelist() if "/GDB/" in n])


def _area_weighted(counties, basins, field):
    """Mean of field over each county, weighted by overlap area, ignoring basins with no data."""
    basins = basins[basins[field].between(0, 5)].to_crs(5070)
    basins["geometry"] = basins.geometry.make_valid()
    pieces = gpd.overlay(counties, basins[[field, "geometry"]], how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.geometry.area
    pieces["weighted"] = pieces[field] * pieces.area
    sums = pieces.groupby("fips")[["weighted", "area"]].sum()
    return (sums.weighted / sums.area).clip(0, 5)  # rounding can land a hair above 5


def build(raw_dir):
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)].rename(columns={"GEOID": "fips"})
    bbox = tuple(counties.total_bounds)
    counties = counties[["fips", "geometry"]].to_crs(5070)
    out = pd.DataFrame({"fips": counties.fips.values})
    for layer, (field, column) in LAYERS.items():
        basins = gpd.read_file(Path(raw_dir) / GDB, layer=layer, columns=[field], bbox=bbox)
        out[column] = out.fips.map(_area_weighted(counties, basins, field))
    return out
