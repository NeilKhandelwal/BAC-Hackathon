"""FracTracker context: reported MW with reporting completeness, stopped projects, and municipal,
state-pending, and non-moratorium county restrictions.

Uses the same raw files and the same facility-to-county matching as etl/adapters/fractracker.py
(its _facility_fips), so the facility set is identical to the one behind dc_existing_count. Main's
adapter doesn't deduplicate facilities, and neither does this one. It leaves dc_existing_mw,
dc_proposed_mw, the counts, the pushback columns, and the moratorium flags alone.
"""
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from etl.adapters import fractracker
from etl.adapters.fractracker import AS_OF, BLOCKING, EXISTING, PROPOSED, _facility_fips
from etl.download import ZIP_MAGIC, download
from etl.fips import load_tiger

PLACES_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip"
SOURCE = {**fractracker.SOURCE, "name": "FracTracker Alliance US Data Centers Tracker (context fields)",
          "observation_period": "live tracker snapshot at retrieval; moratoria ending before 2026-10-03 skipped",
          "license": "Free for non-commercial use with credit to FracTracker Alliance",
          "resolution": "facility points and jurisdictions, aggregated to county"}
RAW = fractracker.RAW
NOTES = ["dc_*_mw_reported sums MW only for facilities that report it, parsing '10,000' as 10000 "
         "and a range like '100-200' as its midpoint. It is 0 when the county has no facilities "
         "and null when it has facilities but none report MW. Read it with dc_*_mw_reporting_share. "
         "dc_existing_mw and dc_proposed_mw keep main's rule (unparseable or missing MW counts as 0).",
         "dc_stopped_count counts facilities with status Cancelled or Suspended.",
         "moratorium_municipal_count and moratorium_municipal_pending_count count active and pending "
         "municipal rows of any category (moratorium, ban, zoning restriction, curative amendment). "
         "County-subdivision rows carry the county in their GEOID. Incorporated places are assigned "
         "to the county holding the place's 2024 Census internal point, so a city spanning counties "
         "counts once. Municipal rows never set moratorium_active.",
         "county_dc_restriction_active is a county-level active row whose category is not moratorium "
         "or ban, such as a zoning restriction. moratorium_state_pending is a state-level pending "
         "moratorium or ban. Rows whose end_date is before 2026-10-03 are skipped, as in main."]
STOPPED = {"Cancelled", "Suspended"}


def fetch(raw_dir):
    fractracker.fetch(raw_dir)
    download(PLACES_URL, Path(raw_dir) / "tiger/2024_Gaz_place_national.zip", 1e5, ZIP_MAGIC)


def parse_mw(v):
    """'10,000' -> 10000.0; '100-200' -> 150.0; blank or text -> NaN."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).replace(",", "").strip()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return np.nan
    return (nums[0] + nums[1]) / 2 if len(nums) >= 2 and "-" in s else nums[0]


def place_counties(raw_dir, counties):
    """Census place GEOID -> county FIPS holding its internal point."""
    p = pd.read_csv(Path(raw_dir) / "tiger/2024_Gaz_place_national.zip", sep="\t", dtype=str)
    p.columns = p.columns.str.strip()
    pts = gpd.GeoDataFrame(p[["GEOID"]], crs=4269, geometry=gpd.points_from_xy(
        pd.to_numeric(p.INTPTLONG), pd.to_numeric(p.INTPTLAT))).to_crs(counties.crs)
    hit = gpd.sjoin(pts, counties[["GEOID", "geometry"]].rename(columns={"GEOID": "county"}), predicate="within")
    return hit.drop_duplicates("GEOID").set_index("GEOID").county


def build(raw_dir):
    raw = Path(raw_dir) / "fractracker"
    tiger = load_tiger(raw_dir)
    ft = pd.read_csv(raw / "ft_all.csv", low_memory=False)
    ft["fips"] = _facility_fips(ft, raw_dir, tiger)
    ft = ft.dropna(subset="fips")
    ft["mw_num"] = ft.mw.map(parse_mw)

    out = pd.DataFrame({"fips": tiger.GEOID, "state_fips": tiger.STATEFP}).set_index("fips")
    for prefix, statuses in (("dc_existing", EXISTING), ("dc_proposed", PROPOSED)):
        g = ft[ft.status.isin(statuses)].groupby("fips")
        n = g.size().reindex(out.index, fill_value=0)
        out[f"{prefix}_mw_reported"] = g.mw_num.sum(min_count=1).reindex(out.index).mask(n == 0, 0.0)
        out[f"{prefix}_mw_reporting_share"] = g.mw_num.apply(lambda s: s.notna().mean()).reindex(out.index)
    out["dc_stopped_count"] = ft[ft.status.isin(STOPPED)].groupby("fips").size().reindex(
        out.index, fill_value=0).astype("Int64")

    m = pd.read_csv(raw / "ft_moratoria.csv", dtype=str)
    m = m[~(pd.to_datetime(m.end_date, errors="coerce") < AS_OF)]
    county_rows = m[(m.level_ == "county") & (m.status == "active") & ~m.category.isin(BLOCKING)]
    out["county_dc_restriction_active"] = out.index.isin(set(county_rows.GEOID))
    state_pending = m[(m.level_ == "state") & (m.status == "pending") & m.category.isin(BLOCKING)]
    out["moratorium_state_pending"] = out.state_fips.isin(set(state_pending.GEOID))

    muni = m[m.level_ == "municipality"].copy()
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")
    is_cousub = muni.GEOID.str.len() == 10
    muni.loc[is_cousub, "county"] = muni.GEOID[is_cousub].str[:5]
    muni.loc[~is_cousub, "county"] = muni.GEOID[~is_cousub].map(place_counties(raw_dir, counties))
    for col, status in (("moratorium_municipal_count", "active"), ("moratorium_municipal_pending_count", "pending")):
        out[col] = muni[muni.status == status].groupby("county").size().reindex(out.index, fill_value=0).astype("Int64")
    for col in ("county_dc_restriction_active", "moratorium_state_pending"):
        out[col] = out[col].astype("boolean")
    return out.drop(columns="state_fips").reset_index()
