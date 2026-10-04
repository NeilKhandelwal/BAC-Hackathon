"""Break Grant County's PAD-US GAP 1-2 acreage into units, with distance from Quincy.

Run from the repo root: .venv/Scripts/python.exe scratch/sensitive_land/grant_breakdown.py
Queries the USGS PAD-US 4.1 flattened feature service (the same layer USGS summarized into the county
table), clips GAP 1-2 polygons to Grant County, and writes scratch/sensitive_land/out/grant_gap12_units.csv.
Network access needed; this is an analysis check, not part of the demo.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[2]
URL = ("https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
       "PADUS_Protection_Status_by_GAP_Status_Code/FeatureServer/0/query")
QUINCY = (-119.852, 47.234)
ACRES_PER_M2 = 1 / 4046.8564224


def fetch(bbox):
    feats, offset = [], 0
    while True:
        params = {"where": "GAP_Sts IN ('1','2')", "geometry": ",".join(map(str, bbox)),
                  "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                  "outFields": "Unit_Nm,MngNm_Desc,GAP_Sts,DesTp_Desc", "returnGeometry": "true", "outSR": 4326,
                  "f": "geojson", "resultOffset": offset, "resultRecordCount": 1000}
        req = urllib.request.Request(URL, data=urllib.parse.urlencode(params).encode())
        with urllib.request.urlopen(req, timeout=300) as r:
            page = json.load(r)
        feats += page.get("features", [])
        if not page.get("properties", {}).get("exceededTransferLimit") and len(page.get("features", [])) < 1000:
            break
        offset += 1000
    return gpd.GeoDataFrame.from_features(feats, crs=4326)


def main():
    counties = gpd.read_file(ROOT / "data/raw/tiger/cb_2024_us_county_500k.zip")
    grant = counties[counties.GEOID == "53025"].to_crs(5070)
    units = fetch(tuple(counties[counties.GEOID == "53025"].total_bounds)).to_crs(5070)
    units["geometry"] = units.geometry.make_valid()
    clipped = gpd.overlay(units, grant[["geometry"]], how="intersection", keep_geom_type=True)
    clipped["acres_in_grant"] = clipped.area * ACRES_PER_M2
    q = gpd.GeoSeries([Point(QUINCY)], crs=4326).to_crs(5070).iloc[0]
    clipped["km_from_quincy"] = clipped.geometry.distance(q) / 1000
    tab = (clipped.groupby(["Unit_Nm", "MngNm_Desc", "GAP_Sts"])
           .agg(acres_in_grant=("acres_in_grant", "sum"), km_from_quincy=("km_from_quincy", "min"))
           .reset_index().sort_values("acres_in_grant", ascending=False))
    out = ROOT / "scratch/sensitive_land/out/grant_gap12_units.csv"
    tab.round(1).to_csv(out, index=False)
    total = tab.acres_in_grant.sum()
    print(f"GAP 1-2 acres in Grant from the feature service: {total:,.0f} (county table: see measure_summary.json)")
    for lim in (10, 25, 50):
        print(f"  within {lim} km of Quincy: {tab[tab.km_from_quincy <= lim].acres_in_grant.sum():,.0f} acres")
    print(tab.head(15).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
