"""NLCD 2021 land cover shares by county, from IPUMS NHGIS's county land cover summaries."""
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.fips import CT_REGION_TO_OLD, EXCLUDED_STATE_FIPS

SOURCE = {"name": "IPUMS NHGIS land cover summaries (NLCD)", "version": "NLCD 2021, 2020 county boundaries "
          "(TIGER/Line 2020)",
          "url": "https://secure-assets.ipums.org/nhgis/environmental/nhgis_county2020_tl2020_nlcd_timebycolumn.zip",
          "license": "IPUMS NHGIS terms: free account, cite, don't redistribute "
                     "(https://www.nhgis.org/citation-and-use-nhgis-data)",
          "citation": "Manson, S., Schroeder, J., Van Riper, D., Knowles, K., Kugler, T., Roberts, F., and Ruggles, "
                      "S. IPUMS National Historical Geographic Information System. Minneapolis, MN: IPUMS.",
          "resolution": "NLCD 30 m classes summarized to county polygons by NHGIS (exactextractr)"}
RAW = "nhgis/nhgis_county2020_tl2020_nlcd_timebycolumn.zip"
OPTIONAL = True  # the raw file needs a free IPUMS NHGIS account; without it the build warns and the columns stay null
CSV = "nhgis_county2020_tl2020_nlcd.csv"
YEAR = 2021
# column -> NLCD classes
CLASSES = {"pct_cropland": [81, 82], "pct_cultivated_crops": [82], "pct_developed": [21, 22, 23, 24],
           "pct_forest_wetland": [41, 42, 43, 90, 95]}
NOTES = [f"pct_cropland is the share of the county in NLCD {YEAR} classes 81 (pasture/hay) and 82 (cultivated "
         "crops); pct_cultivated_crops is class 82 alone and is context only. pct_developed is classes 21-24 and "
         "pct_forest_wetland classes 41-43, 90, and 95. Shares are of the whole county polygon, water included, "
         "as NHGIS computes them.",
         "The NHGIS summaries use 2020 county boundaries, so Connecticut appears as its 8 old counties. Each "
         "planning region takes the shares of the county it mostly overlaps (etl/fips.py CT_REGION_TO_OLD).",
         "NLCD measures land cover, not soil quality: cropland is not the same as prime farmland, which needs "
         "NRCS soil survey data. The raw file requires a free IPUMS NHGIS account and is not redistributed."]


def fetch(raw_dir):
    path = Path(raw_dir) / RAW
    if not path.exists():
        raise FileNotFoundError(f"{path}: download it while logged in to IPUMS NHGIS ({SOURCE['url']})")


def build(raw_dir):
    with zipfile.ZipFile(Path(raw_dir) / RAW) as z:
        df = pd.read_csv(z.open(CSV), dtype={"GEOID": str})
    df = df.set_index("GEOID")
    shares = pd.DataFrame({col: df[[f"PROP_{c}_{YEAR}" for c in classes]].sum(axis=1)
                           for col, classes in CLASSES.items()})

    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip", ignore_geometry=True)
    fips = counties.GEOID[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)]
    source = fips.map(lambda f: CT_REGION_TO_OLD.get(f, f))
    missing = sorted(set(source) - set(shares.index))
    if missing:
        raise ValueError(f"{len(missing)} counties have no NHGIS row, e.g. {missing[:5]}")
    out = shares.reindex(source.to_numpy()).clip(0, 1)
    out.insert(0, "fips", fips.to_numpy())
    return out.reset_index(drop=True)
