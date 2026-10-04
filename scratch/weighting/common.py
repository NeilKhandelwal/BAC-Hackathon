"""Shared loading for the weighting analyses. Reads engine/ and etl/ without modifying them."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import engine.rank as er  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
IMG = ROOT / "docs/img"
FEATURES = ROOT / "data/processed/county_features.parquet"
# Counties every report names, so results stay comparable across phases.
FOCUS = {"53025": "Grant, WA", "53011": "Clark, WA", "36033": "Franklin, NY", "36019": "Clinton, NY", "25003": "Berkshire, MA",
         "51107": "Loudoun, VA", "48113": "Dallas, TX"}


def load(preset="balanced"):
    """County table, conditions, pillar mapping, and the boolean gate-pass mask for a preset."""
    df, _ = er.load_features(FEATURES)
    cond = er.load_yaml(ROOT / f"engine/conditions/{preset}.yaml")
    pillars = er.load_yaml(ROOT / "engine/pillars.yaml")
    log = er.apply_gates(df, cond)
    passed = (log["failed_gates"] == "").to_numpy()
    return df, cond, pillars, passed


def names(df):
    return (df["county_name"] + ", " + df["state"]).set_axis(df["fips"])


def rank_in(series, fips, ascending=True):
    """1-based rank of fips within series (indexed by fips), or None when it isn't there."""
    if fips not in series.index:
        return None
    return int(series.rank(ascending=ascending, method="min")[fips])


def setup_out():
    OUT.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 220, "display.max_columns", 40)
