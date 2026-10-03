"""FracTracker Alliance data center tracker: facility counts, pushback, and moratoria.

License: free for non-commercial use with credit to FracTracker Alliance.
"""
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.fips import build_lookup, load_tiger, to_fips

SOURCE = {"name": "FracTracker Alliance US Data Centers Tracker", "version": "live feature service",
          "url": "https://www.fractracker.org/data-centers"}
RAW = "fractracker/ft_all.csv"
NOTES = ["Facility counts and MW are 0 for counties with no tracked facility. Facilities join by "
         "county name, then by lat/lon when the name fails.",
         "moratorium_active and moratorium_pending count FracTracker categories 'moratorium' and "
         "'ban' only, not zoning restrictions, and skip entries whose end_date is before "
         "2026-10-03. "
         "Municipal and tribal moratoria are not rolled up to the county."]

EXISTING = {"Operating", "Expanding"}
PROPOSED = {"Proposed", "Approved/Permitted/Under construction", "Pre-proposal"}
BLOCKING = {"moratorium", "ban"}
AS_OF = pd.Timestamp("2026-10-03")  # fixed so that a rebuild of the same raw files can't change
UNMATCHED = []


def fetch(raw_dir):
    if not (Path(raw_dir) / "fractracker/ft_moratoria.csv").exists():
        subprocess.run([sys.executable, "etl/fetch_fractracker.py"], check=True)


def _facility_fips(ft, raw_dir, tiger):
    lookup = build_lookup(tiger)
    fips = pd.Series([to_fips(c, s, lookup) for c, s in zip(ft.county, ft.state)], index=ft.index)
    missing = fips.isna() & ft.lat.notna() & ft.long.notna()
    if missing.any():
        counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")[["GEOID", "geometry"]]
        points = gpd.GeoDataFrame(geometry=gpd.points_from_xy(ft.long[missing], ft.lat[missing]),
                                  index=ft.index[missing], crs=counties.crs)
        hit = gpd.sjoin(points, counties, predicate="within").GEOID
        fips.loc[hit.index] = hit
    return fips.where(fips.isin(set(tiger.GEOID)))


def build(raw_dir):
    raw = Path(raw_dir) / "fractracker"
    tiger = load_tiger(raw_dir)
    ft = pd.read_csv(raw / "ft_all.csv", low_memory=False)
    ft["fips"] = _facility_fips(ft, raw_dir, tiger)
    in_scope = ft.state.isin(set(tiger.STUSPS))
    UNMATCHED[:] = (ft[ft.fips.isna() & in_scope].groupby(["state", "county"], dropna=False).size()
                    .reset_index().itertuples(index=False, name=None))
    ft = ft.dropna(subset="fips")
    ft["mw"] = pd.to_numeric(ft.mw, errors="coerce").fillna(0.0)  # source nulls count as 0 MW
    existing, proposed = ft[ft.status.isin(EXISTING)], ft[ft.status.isin(PROPOSED)]
    pushback = ft[ft.community_pushback.str.lower() == "yes"]

    out = pd.DataFrame({"fips": tiger.GEOID, "state_fips": tiger.STATEFP}).set_index("fips")
    out["dc_existing_count"] = existing.groupby("fips").size()
    out["dc_existing_mw"] = existing.groupby("fips").mw.sum()
    out["dc_proposed_count"] = proposed.groupby("fips").size()
    out["dc_proposed_mw"] = proposed.groupby("fips").mw.sum()
    out["dc_pushback_count"] = pushback.groupby("fips").size()
    out = out.fillna(0)
    out["dc_pushback_any"] = out.dc_pushback_count > 0

    m = pd.read_csv(raw / "ft_moratoria.csv", dtype=str)
    ended = pd.to_datetime(m.end_date, errors="coerce") < AS_OF
    m = m[m.category.isin(BLOCKING) & ~ended]

    def flagged(level, status):
        return set(m[(m.level_ == level) & (m.status == status)].GEOID)

    out["moratorium_active"] = out.index.isin(flagged("county", "active"))
    out["moratorium_pending"] = out.index.isin(flagged("county", "pending"))
    out["moratorium_state_active"] = out.state_fips.isin(flagged("state", "active"))
    return out.drop(columns="state_fips").reset_index()
