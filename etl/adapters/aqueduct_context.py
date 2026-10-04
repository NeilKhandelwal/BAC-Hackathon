"""Aqueduct 4.0 context: raw ratio, categories, and area shares beside water_stress_bws and
water_stress_2050, which etl/adapters/aqueduct.py computes and this module leaves alone."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from etl.adapters import aqueduct
from etl.fips import EXCLUDED_STATE_FIPS

SOURCE = {**aqueduct.SOURCE, "name": "WRI Aqueduct 4.0 (context fields)",
          "observation_period": "baseline 1979-2019; 2050 business as usual (SSP3-RCP7.0), 2035-2065",
          "license": "CC BY 4.0, World Resources Institute",
          "resolution": "HydroBASINS level 6, area-weighted to county in EPSG:5070"}
RAW = aqueduct.RAW
NOTES = ["water_stress_bws_cat and water_stress_2050_cat are the Aqueduct category covering the most "
         "county area: -1 arid and low water use, 0 low, 1 low-medium, 2 medium-high, 3 high, 4 "
         "extremely high.",
         "water_stress_bws_raw_median is the area-weighted median of bws_raw, withdrawals over "
         "available supply. It is null when the median basin carries Aqueduct's 9999 near-zero-supply "
         "sentinel.",
         "water_stress_high_share is the county area in category 3 or 4; water_stress_arid_share in "
         "category -1; water_stress_area_coverage the share of county area with baseline data."]


def fetch(raw_dir):
    aqueduct.fetch(raw_dir)


def _overlay(counties, layer, fields, raw_dir):
    basins = gpd.read_file(Path(raw_dir) / aqueduct.GDB, layer=layer, columns=fields,
                           bbox=tuple(counties.to_crs(4269).total_bounds)).to_crs(5070)
    basins["geometry"] = basins.geometry.make_valid()
    pieces = gpd.overlay(counties, basins, how="intersection", keep_geom_type=True)
    pieces["a"] = pieces.geometry.area
    return pd.DataFrame(pieces.drop(columns="geometry"))


def _dominant(p, col):
    x = p.dropna(subset=[col]).groupby(["fips", col]).a.sum().reset_index()
    return x.sort_values("a").drop_duplicates("fips", keep="last").set_index("fips")[col]


def _share(p, mask, valid):
    num = p.a.where(mask, 0).groupby(p.fips).sum()
    den = p.a.where(valid, 0).groupby(p.fips).sum()
    return (num / den).where(den > 0)


def _weighted_median(p, col):
    def wm(g):
        g = g.dropna(subset=[col]).sort_values(col)
        if g.empty:
            return np.nan
        c = g.a.cumsum()
        return g[col].iloc[int(np.searchsorted(c, c.iloc[-1] / 2))]
    return p.groupby("fips")[[col, "a"]].apply(wm)


def build(raw_dir):
    counties = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)].rename(columns={"GEOID": "fips"})
    counties = counties[["fips", "geometry"]].to_crs(5070)
    county_area = counties.set_index("fips").area

    b = _overlay(counties, "baseline_annual", ["bws_raw", "bws_cat"], raw_dir)
    valid = b.bws_cat.between(-1, 4)
    b["bws_cat"] = b.bws_cat.where(valid)
    b["bws_raw"] = b.bws_raw.where(valid & (b.bws_raw >= 0)).replace(9999, np.inf)
    f = _overlay(counties, "future_annual", ["bau50_ws_x_c"], raw_dir)
    f["bau50_ws_x_c"] = f.bau50_ws_x_c.where(f.bau50_ws_x_c.between(-1, 4))

    out = pd.DataFrame({"fips": counties.fips.values}).set_index("fips")
    out["water_stress_bws_raw_median"] = _weighted_median(b, "bws_raw").replace(np.inf, np.nan)
    out["water_stress_bws_cat"] = _dominant(b, "bws_cat")
    out["water_stress_high_share"] = _share(b, b.bws_cat >= 3, valid)
    out["water_stress_arid_share"] = _share(b, b.bws_cat == -1, valid)
    out["water_stress_area_coverage"] = (b.a.where(valid, 0).groupby(b.fips).sum() / county_area).clip(upper=1)
    out["water_stress_2050_cat"] = _dominant(f, "bau50_ws_x_c")
    for col in ("water_stress_bws_cat", "water_stress_2050_cat"):
        out[col] = out[col].round().astype("Int64")
    return out.reset_index()
