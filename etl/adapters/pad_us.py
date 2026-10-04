"""USGS PAD-US 4.1: share of each county in protected status, from USGS's own county summary table."""
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import EXCLUDED_STATE_FIPS

SOURCE = {"name": "USGS Protected Areas Database of the United States (PAD-US) 4.1, Summary Statistics",
          "version": "PAD-US 4.1 Vector Analysis, counties clipped to Census 2022 boundaries",
          "url": "https://www.sciencebase.gov/catalog/file/get/6759b69fd34edfeb8710a3ea?f=__disk__29%2F74%2F0b"
                 "%2F29740bfde5519713b02c6190b07c47e965ce5d23",
          "item": "https://www.sciencebase.gov/catalog/item/6759b69fd34edfeb8710a3ea",
          "license": "public domain, U.S. Geological Survey",
          "resolution": "USGS flattened polygons summarized to county, acres by GAP status"}
RAW = "padus/PADUS4_1SummaryStatistics_TabularData_CSV.zip"
CSV = "PADUS4_1VectorAnalysis_Uni_Counties_Clip_CENSUS2022.csv"
NOTES = ["pct_protected is the share of the county's total area (land and water) in PAD-US 4.1 GAP status "
         "1 or 2, which USGS describes as managed primarily for biodiversity. pct_protected_gap1to3 adds "
         "GAP 3, managed for multiple uses including conservation and extraction; it is context and not "
         "scored. Both come from USGS's county summary of the PAD-US 4.1 Vector Analysis layer, which USGS "
         "flattened 'to remove overlaps, avoiding overestimation in protected area statistics', so a "
         "wilderness inside a national forest counts once.",
         "The denominator is the county's total area in the same USGS table. It matches Census 2024 land "
         "plus water within 2% for every county but one (Emporia city, VA, 4.4%, a boundary-vintage "
         "difference), so counties with large lakes or coastal water read lower than "
         "a land-only share would.",
         "American Indian lands are GAP 4 in PAD-US, so pct_protected and tribal_land_share don't double "
         "count. County shares are a screen, not a siting check: a 150-acre campus can avoid protected land "
         "inside a county, so a parcel-level check belongs in feasibility."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)


def build(raw_dir):
    with zipfile.ZipFile(Path(raw_dir) / RAW) as z:
        df = pd.read_csv(z.open(CSV), dtype={"GAP_Sts": str}, encoding="utf-8")
    df[["name", "st"]] = df.BndryName.str.rsplit(", ", n=1, expand=True)
    acres = df.groupby(["st", "name"]).GIS_AcrsDb
    total = acres.sum()
    gap12 = df[df.GAP_Sts.isin(["1", "2"])].groupby(["st", "name"]).GIS_AcrsDb.sum()
    gap123 = df[df.GAP_Sts.isin(["1", "2", "3"])].groupby(["st", "name"]).GIS_AcrsDb.sum()

    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip", ignore_geometry=True)
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)]
    keys = pd.MultiIndex.from_arrays([counties.STUSPS, counties.NAMELSAD])
    if keys.duplicated().any() or total.index.duplicated().any():
        raise ValueError("county name keys are not unique")
    missing = keys.difference(total.index)
    if len(missing):
        raise ValueError(f"{len(missing)} counties have no PAD-US row, e.g. {list(missing[:5])}")
    # A wrong name pairing would show up as a large area mismatch. Boundary vintage (Census 2022 clip
    # against 2024 boundaries) moves small independent cities a little: Emporia city, VA is 4.4% off.
    census_acres = (counties.ALAND.to_numpy() + counties.AWATER.to_numpy()) / 4046.8564224
    ratio = total.reindex(keys).to_numpy() / census_acres
    ok = (ratio > 0.95) & (ratio < 1.05)
    if not ok.all():
        raise ValueError(f"PAD-US county area differs from Census by more than 5% for {counties.GEOID[~ok].tolist()[:10]}")

    tot = total.reindex(keys).to_numpy()
    return pd.DataFrame({
        "fips": counties.GEOID.to_numpy(),
        "pct_protected": (gap12.reindex(keys).fillna(0).to_numpy() / tot).clip(0, 1),
        "pct_protected_gap1to3": (gap123.reindex(keys).fillna(0).to_numpy() / tot).clip(0, 1),
    })
