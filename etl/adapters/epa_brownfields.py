"""EPA brownfield properties (ACRES) as potential reuse sites, counted per county.

EPA publishes no single national ACRES table, so three public EPA layers are joined on the ACRES
property ID: Cleanups in My Community (identity, coordinates, grant flags, ready-for-reuse),
RE-Powering Mapper Sites 2022 (acreage, grid and rail distances), and Brownfield Properties Over
100 Acres (curated large sites). These are potential reuse sites, not confirmed available land and
not confirmed suitable for a data center.

build() returns the county table and keeps the site table in SITES. build_features calls
write_artifacts() to save it, so build() itself writes nothing.
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from etl.arcgis import fetch_csv
from etl.fips import EXCLUDED_STATE_FIPS

EPA = "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services"
CIMC = EPA + "/Cleanups_in_my_Community_Sites/FeatureServer/0"
REPM = EPA + "/RE_Powering_Mapper_Sites_2022/FeatureServer/0"
BIG = EPA + "/Brownfield_Properties_Over_100_Acres_view/FeatureServer/0"
SOURCE = {"name": "EPA brownfield properties (ACRES)",
          "version": "Cleanups in My Community sites (refreshed twice monthly); RE-Powering Mapper Sites 2022; "
                     "Brownfield Properties Over 100 Acres",
          "url": CIMC, "urls": [CIMC, REPM, BIG],
          "observation_period": "CIMC snapshot at retrieval; acreage from the 2022 RE-Powering snapshot or "
                                "the curated large-site layer",
          "license": "Public domain (U.S. EPA)", "resolution": "property points, point-in-polygon to county"}
RAW = "epa/cimc_brownfield_sites.csv"
NOTES = ["bf_* columns count EPA ACRES brownfield properties, deduplicated on property ID. They mark "
         "potential reuse, not available land and not data-center suitability.",
         "bf_known_acres sums reported acreage only and is null when a county has properties but none "
         "report acreage. It is 0 only when the county has no properties. Read it with "
         "bf_acreage_reporting_share.",
         "RE-Powering acreage of 0 is unknown. Acreage above 10,000 acres (larger than any property in "
         "EPA's curated 100+ acre layer; these are community-wide assessment records) or above the "
         "county's land area is nulled and flagged in brownfield_sites.parquet.",
         "bf_redevelopment_started_count counts EPA-reported redevelopment start dates. The only "
         "national field (100+ acre layer) was empty at retrieval, so it is 0 everywhere. No "
         "redevelopment reported never means the site is vacant.",
         "No national public layer carries brownfield cleanup completion dates."]

CIMC_FIELDS = ("BF_PROPERTY_ID,BF_PROPERTY_NAME,PRIMARY_NAME,REGISTRY_ID,LOCATION_ADDRESS,CITY_NAME,STATE_CODE,"
               "COUNTY_NAME,LATITUDE,LONGITUDE,BF_ASSESS_IND,BF_CLEANUP_IND,BF_TBA_IND,BF_128A_IND,BF_IC_CODE,"
               "BF_READY_FOR_REUSE_IND,DATA_REFRESH_DT")
LAYERS = {  # raw file -> (layer, where, fields, order_by)
    "epa/cimc_brownfield_sites.csv": (CIMC, "BF_PROPERTY_ID IS NOT NULL", CIMC_FIELDS, "OBJECTID"),
    "epa/repowering_2022_brownfields.csv": (REPM, "Program='Brownfields'",
                                            "SiteID,Acreage,SSDist,SSVoltage,TransDist,TLkV,RailDist", "OBJECTID"),
    "epa/brownfields_over_100_acres.csv": (BIG, "1=1", "*", "ObjectId"),
}
AREA_WIDE_ACRES = 10_000  # above the largest property in EPA's curated 100+ acre layer (9,114)
ACRES_PER_SQKM = 247.105
SITES = None  # site table from the last build()


def fetch(raw_dir):
    for raw, (layer, where, fields, order_by) in LAYERS.items():
        dest = Path(raw_dir) / raw
        if dest.exists():
            continue
        expected = requests.get(layer + "/query", params={"where": where, "returnCountOnly": "true", "f": "json"},
                                timeout=120).json()["count"]
        fetch_csv(layer, dest, where=where, out_fields=fields, order_by=order_by)
        got = len(pd.read_csv(dest, usecols=[0]))
        if got != expected:
            dest.unlink()
            raise RuntimeError(f"{layer}: paged {got} rows, layer reports {expected}")


def _id(s):
    return s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def _date(s):
    n = pd.to_numeric(s, errors="coerce")
    return pd.to_datetime(n, unit="ms", errors="coerce").fillna(
        pd.to_datetime(s.where(n.isna()), errors="coerce")).dt.date.astype("string")


def sites(raw_dir):
    """Deduplicated brownfield properties in the contiguous US with their county FIPS."""
    raw = Path(raw_dir)
    c = pd.read_csv(raw / "epa/cimc_brownfield_sites.csv", dtype=str)
    r = pd.read_csv(raw / "epa/repowering_2022_brownfields.csv", dtype=str)
    b = pd.read_csv(raw / "epa/brownfields_over_100_acres.csv", dtype=str)
    flags = ["BF_ASSESS_IND", "BF_CLEANUP_IND", "BF_TBA_IND", "BF_128A_IND"]
    c["property_id"] = _id(c.BF_PROPERTY_ID)
    any_y = c.groupby("property_id")[flags].agg(lambda s: s.fillna("").str.upper().eq("Y").any())
    c = c.sort_values(["property_id", "REGISTRY_ID"]).drop_duplicates("property_id").set_index("property_id")
    c[flags] = any_y[flags]

    s = pd.DataFrame(index=c.index)
    s["property_name"] = c.BF_PROPERTY_NAME.fillna(c.PRIMARY_NAME).astype("string")
    s["address"], s["city"] = c.LOCATION_ADDRESS.astype("string"), c.CITY_NAME.astype("string")
    s["state"], s["county_name_source"] = c.STATE_CODE.astype("string"), c.COUNTY_NAME.astype("string")
    s["frs_registry_id"] = _id(c.REGISTRY_ID)
    s["lat"], s["lon"] = pd.to_numeric(c.LATITUDE, errors="coerce"), pd.to_numeric(c.LONGITUDE, errors="coerce")
    s["ready_for_reuse"] = c.BF_READY_FOR_REUSE_IND.fillna("").str.upper().map({"Y": True, "N": False}).astype("boolean")
    s["assessment_funding"] = c.BF_ASSESS_IND.astype("boolean")
    s["cleanup_grant"] = c.BF_CLEANUP_IND.astype("boolean")
    s["targeted_assessment"] = c.BF_TBA_IND.astype("boolean")
    s["state_tribal_128a"] = c.BF_128A_IND.astype("boolean")
    s["institutional_controls"] = c.BF_IC_CODE.astype("string")
    s["cimc_refresh_date"] = _date(c.DATA_REFRESH_DT)

    r["property_id"] = _id(r.SiteID)
    r = r.drop_duplicates("property_id").set_index("property_id")
    acres = pd.to_numeric(r.Acreage, errors="coerce")
    s["acreage_repowering_2022"] = acres.where(acres > 0).reindex(s.index)
    for src, dst in (("SSDist", "substation_dist_mi"), ("SSVoltage", "substation_voltage_kv"),
                     ("TransDist", "transmission_line_dist_mi"), ("TLkV", "transmission_line_kv"),
                     ("RailDist", "rail_dist_mi")):
        s[dst] = pd.to_numeric(r[src], errors="coerce").reindex(s.index)
    b["property_id"] = _id(b.Property_ID)
    b = b.drop_duplicates("property_id").set_index("property_id")
    s["acreage_large_site_layer"] = pd.to_numeric(b.Property_Size, errors="coerce").reindex(s.index)
    s["in_large_site_layer"] = s.index.isin(b.index)
    s["ready_for_anticipated_use_date"] = _date(b.RAU_date).reindex(s.index)
    s["redevelopment_start_date"] = _date(b.Redevelopment_Start_Date).reindex(s.index)
    s["planned_future_use"] = b.Actual_or_Planned_Future_Use.str.strip().astype("string").reindex(s.index)
    # The curated large-site layer is newer than the 2022 RE-Powering snapshot.
    s["acreage_reported"] = s.acreage_large_site_layer.fillna(s.acreage_repowering_2022)
    s["acreage_source"] = pd.Series(pd.NA, index=s.index, dtype="string")
    s.loc[s.acreage_repowering_2022.notna(), "acreage_source"] = "RE-Powering Mapper 2022"
    s.loc[s.acreage_large_site_layer.notna(), "acreage_source"] = "Brownfield Properties Over 100 Acres"
    s["redevelopment_status"] = pd.Series("none_reported", index=s.index, dtype="string")
    s.loc[s.redevelopment_start_date.notna(), "redevelopment_status"] = "redevelopment_started_reported"

    counties = gpd.read_file(raw / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)][["GEOID", "ALAND", "geometry"]]
    pts = gpd.GeoDataFrame(index=s.index, geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326).to_crs(counties.crs)
    hit = gpd.sjoin(pts, counties, predicate="within")
    hit = hit[~hit.index.duplicated()]
    s["fips"] = hit.GEOID.reindex(s.index).astype("string")
    s = s[s.fips.notna()].copy()
    land_acres = s.fips.map(counties.set_index("GEOID").ALAND) / 1e6 * ACRES_PER_SQKM
    bad = (s.acreage_reported > land_acres) | (s.acreage_reported > AREA_WIDE_ACRES)
    s["acreage_implausible"] = bad.astype("boolean")
    s["acreage_reported"] = s.acreage_reported.mask(bad).astype("Float64")
    s["cimc_profile_url"] = "https://cimc.epa.gov/ords/cimc/f?p=CIMC:31::::Y,31:P31_ID:" + s.index.to_series()
    return s.rename_axis("property_id").reset_index()


def build(raw_dir):
    global SITES
    s = sites(raw_dir)
    g = s.groupby("fips")
    agg = pd.DataFrame({
        "bf_site_count": g.size(),
        "bf_known_acres": g.acreage_reported.sum(min_count=1).astype("float64"),
        "bf_acreage_reporting_share": g.acreage_reported.apply(lambda x: x.notna().mean()),
        "bf_sites_50plus_acres": g.acreage_reported.apply(lambda x: int((x >= 50).sum())),
        "bf_ready_for_reuse_count": g.ready_for_reuse.apply(lambda x: int(x.fillna(False).sum())),
        "bf_redevelopment_started_count": g.redevelopment_status.apply(
            lambda x: int((x == "redevelopment_started_reported").sum())),
    })
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip", ignore_geometry=True)
    fips = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)].GEOID.sort_values()
    out = agg.reindex(fips)
    for col in ("bf_site_count", "bf_sites_50plus_acres", "bf_ready_for_reuse_count", "bf_redevelopment_started_count"):
        out[col] = out[col].fillna(0).astype("Int64")
    out.loc[out.bf_site_count == 0, "bf_known_acres"] = 0.0  # no sites: a confirmed zero
    out["bf_acreage_reporting_share"] = out.bf_acreage_reporting_share.astype("float64")
    SITES = s
    return out.rename_axis("fips").reset_index()


def write_artifacts(out_dir):
    """Save the site table from the last build(). Called by build_features after the table is written."""
    if SITES is not None:
        SITES.to_parquet(Path(out_dir) / "brownfield_sites.parquet", index=False)
        return [str(Path(out_dir) / "brownfield_sites.parquet")]
    return []
