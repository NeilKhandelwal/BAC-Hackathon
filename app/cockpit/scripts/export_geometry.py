"""Write full-resolution county polygons as GeoJSON for scripts/build-geometry.ts.

Reads the Census 2025 cartographic boundary file that the ETL downloads. It does
not simplify: simplifying one county at a time breaks shared borders, so
simplification happens later on the topology, where neighbors share each edge.

Usage, from app/cockpit: npm run geometry
"""

import sys
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from etl.fips import EXCLUDED_STATE_FIPS  # noqa: E402

RAW = ROOT / "data/raw/census/cb_2025_us_county_500k.zip"

if __name__ == "__main__":
    out = Path(sys.argv[1])
    g = gpd.read_file(RAW).to_crs(4326)
    g = g[~g.STATEFP.isin(EXCLUDED_STATE_FIPS)].sort_values("GEOID")
    g = gpd.GeoDataFrame(
        {"fips": g.GEOID.values, "county_name": g.NAME.values, "state": g.STUSPS.values},
        geometry=g.geometry.values,
        crs=4326,
    )
    out.write_text(g.to_json(drop_id=True))
    print(f"wrote {len(g)} full-resolution counties to {out}")
