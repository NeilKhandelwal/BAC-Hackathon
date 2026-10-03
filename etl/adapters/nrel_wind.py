"""NREL WIND Toolkit mean wind speed at 100 m, averaged over each county."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from affine import Affine
from rasterstats import zonal_stats

from etl.download import ZIP_MAGIC, download
from etl.fips import EXCLUDED_STATE_FIPS

SOURCE = {"name": "NREL WIND Toolkit", "version": "CONUS 100 m mean wind speed, 2 km grid",
          "url": "https://www.nlr.gov/docs/libraries/gis/us-wind-data.zip"}
RAW = "nrel/us-wind-data.zip"
TIF = "us-wind-data/wtk_conus_100m_mean_masked.tif"


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e8, ZIP_MAGIC, timeout=900)


def build(raw_dir):
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)]
    with rasterio.open(f"zip://{Path(raw_dir) / RAW}!{TIF}") as src:
        t = src.transform
        # The file is stored south-up, which rasterstats can't window. Flip it to north-up.
        speed = src.read(1)[::-1]  # m/s
        north_up = Affine(t.a, 0, t.c, 0, -t.e, t.f + t.e * src.height)
        # all_touched so that counties smaller than a 2 km cell still get a value
        stats = zonal_stats(counties.to_crs(src.crs), speed, affine=north_up,
                            nodata=src.nodata, stats="mean", all_touched=True)
    return pd.DataFrame({"fips": counties.GEOID.values,
                         "wind_speed_100m_ms": [s["mean"] for s in stats]})
