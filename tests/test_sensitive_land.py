"""Checks for the PAD-US and tribal land adapters. Skipped when their raw files are absent."""
from pathlib import Path

import pytest

RAW = Path("data/raw")
NEEDED = {"pad_us": ["padus/PADUS4_1SummaryStatistics_TabularData_CSV.zip", "tiger/cb_2024_us_county_500k.zip"],
          "tribal_lands": ["tiger/tl_2024_us_aiannh.zip", "tiger/cb_2024_us_county_500k.zip"]}


def _build(name):
    missing = [p for p in NEEDED[name] if not (RAW / p).exists()]
    if missing:
        pytest.skip(f"raw files absent: {missing}")
    from importlib import import_module
    return import_module(f"etl.adapters.{name}").build(RAW).set_index("fips")


def test_pad_us_shares_cover_every_county_and_match_the_manual_check():
    d = _build("pad_us")
    assert len(d) == 3109 and d.notna().all().all()
    assert ((d >= 0) & (d <= 1)).all().all()
    assert (d.pct_protected <= d.pct_protected_gap1to3 + 1e-12).all()
    # Grant's GAP 1-2 acreage, broken down by unit in research/sensitive_land.md, is 12.8%.
    assert d.at["53025", "pct_protected"] == pytest.approx(0.128, abs=0.002)
    assert d.at["36033", "pct_protected"] > 0.3  # Franklin NY: Adirondack Forest Preserve


def test_tribal_land_share_counts_reservations_and_trust_land_only():
    d = _build("tribal_lands")
    assert len(d) == 3109 and ((d.tribal_land_share >= 0) & (d.tribal_land_share <= 1)).all()
    # No tribal land in Grant County; TIGER/Line and cartographic county edges leave a sliver near 1e-6.
    assert d.at["53025", "tribal_land_share"] < 1e-4
    assert d.at["36033", "tribal_land_share"] > 0  # St. Regis Mohawk Reservation
    assert d.at["53077", "tribal_land_share"] > 0.3  # Yakima County: Yakama Nation
    assert d.at["40143", "tribal_land_share"] < 0.5  # Tulsa: statistical areas excluded


def test_frozen_table_carries_the_land_columns():
    import pandas as pd
    t = pd.read_parquet("data/processed/county_features.parquet").set_index("fips")
    for c in ("pct_protected", "pct_protected_gap1to3", "tribal_land_share", "pct_cropland",
              "pct_cultivated_crops", "pct_developed", "pct_forest_wetland"):
        assert c in t and t[c].between(0, 1).all(), c
    assert t.at["53025", "pct_protected"] == pytest.approx(0.128, abs=0.002)


def test_sensitive_land_gates_are_off_by_default_and_exclude_when_set():
    from engine.rank import load_features, load_yaml, rank
    df, _ = load_features("data/processed/county_features.parquet")
    pillars = load_yaml("engine/pillars.yaml")
    base = {**load_yaml("engine/conditions/balanced.yaml"), "robustness": {"samples": 0}}
    assert base["gates"]["max_pct_protected"] is None and base["gates"]["max_tribal_land_share"] is None
    _, _, report = rank(df, base, pillars)
    gated = {**base, "gates": {**base["gates"], "max_pct_protected": 0.25, "max_tribal_land_share": 0.25}}
    ranked, excluded, report_g = rank(df, gated, pillars)
    assert report_g["passed"] < report["passed"]
    assert "53025" in set(ranked.fips)  # Grant: 12.8% protected, no tribal land
    hit = excluded.failed_gates.str.contains("max_pct_protected|max_tribal_land_share")
    assert hit.any()
