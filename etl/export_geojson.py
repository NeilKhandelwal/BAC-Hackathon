"""Write data/processed/counties.geojson: simplified county shapes for the demo map.

Same counties as the feature table. Feature id and properties.fips are the 5-character FIPS.

Usage: python -m etl.export_geojson
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from etl.fips import EXCLUDED_STATE_FIPS

RAW = Path("data/raw/tiger/cb_2024_us_county_500k.zip")
OUT = Path("data/processed/counties.geojson")
TOLERANCE_DEG = 0.01  # about 1 km; fine for a national choropleth
GRID_DEG = 0.001      # coordinate rounding

if __name__ == "__main__":
    g = gpd.read_file(RAW).to_crs(4326)
    g = g[~g.STATEFP.isin(EXCLUDED_STATE_FIPS)].sort_values("GEOID")
    geometry = shapely.set_precision(g.geometry.simplify(TOLERANCE_DEG).values, GRID_DEG)
    out = gpd.GeoDataFrame({"fips": g.GEOID.values, "county_name": g.NAME.values, "state": g.STUSPS.values},
                           geometry=geometry, index=pd.Index(g.GEOID.values), crs=4326)
    bad = out[out.geometry.is_empty | ~out.geometry.is_valid].fips.tolist()
    if bad:
        raise RuntimeError(f"simplification broke these counties: {bad}")
    table = pd.read_parquet("data/processed/county_features.parquet", columns=["fips"])
    if set(out.fips) != set(table.fips):
        raise RuntimeError("GeoJSON counties differ from the feature table")
    OUT.write_text(json.dumps(json.loads(out.to_json()), separators=(",", ":")))
    print(f"wrote {len(out)} features, {OUT.stat().st_size / 1e6:.1f} MB")
