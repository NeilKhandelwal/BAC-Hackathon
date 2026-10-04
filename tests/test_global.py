"""The engine runs on a non-county table, and the committed country table is what it claims to be."""
import json

import pandas as pd
import pytest

from engine.__main__ import main
from engine.explain import explain, format_text
from engine.rank import load_features, load_yaml, rank

GLOBAL = "data/processed/global_country_features.parquet"
COND = "engine/conditions/global_balanced.yaml"
PILLARS = "engine/pillars_global.yaml"
UNIT = {"key": "iso3", "name": "country", "group": "region"}


def fake_countries():
    return pd.DataFrame({
        "iso3": ["AAA", "BBB", "CCC", "DDD"],
        "country": ["A", "B", "C", "D"],
        "region": ["North", "North", "South", "South"],
        "x": [1.0, 2.0, 3.0, 4.0],
    })


def test_non_fips_key_is_not_zero_padded(tmp_path):
    # A five-digit pad would turn "USA" into "00USA" and break every join on the key.
    fake_countries().to_parquet(tmp_path / "t.parquet")
    df, _ = load_features(tmp_path / "t.parquet", key="iso3")
    assert df["iso3"].tolist() == ["AAA", "BBB", "CCC", "DDD"]


def test_region_gates_act_on_the_unit_group_column():
    # Without the unit block the gate would read a missing "state" column and mark every row unknown.
    cond = {"unit": UNIT, "weights": {"p": 1}, "gates": {"states_exclude": ["South"]}}
    ranked, excluded, _ = rank(fake_countries(), cond, {"p": [{"column": "x"}]})
    assert sorted(excluded["iso3"]) == ["CCC", "DDD"]
    assert ranked["iso3"].tolist() == ["BBB", "AAA"]
    assert {"iso3", "country", "region"} <= set(ranked.columns)
    ranked, _, _ = rank(fake_countries(), {**cond, "gates": {"states_include": ["South"]}}, {"p": [{"column": "x"}]})
    assert ranked["iso3"].tolist() == ["DDD", "CCC"]


def test_explain_finds_a_row_by_its_unit_key():
    cond = {"unit": UNIT, "weights": {"p": 1}, "name": "t"}
    e = explain(fake_countries(), cond, {"p": [{"column": "x"}]}, "DDD")
    assert (e["iso3"], e["country"], e["region"], e["rank"]) == ("DDD", "D", "South", 1)
    assert format_text(e, UNIT).startswith("D, South (DDD)")


def test_country_table_is_countries_keyed_by_iso3():
    df = pd.read_parquet(GLOBAL)
    assert df["iso3"].str.fullmatch(r"[A-Z]{3}").all() and df["iso3"].is_unique
    assert len(df) == json.load(open(GLOBAL.replace(".parquet", ".manifest.json")))["rows"]
    # World Bank aggregates and territories would distort every percentile.
    assert not set(df["iso3"]) & {"WLD", "EUU", "HIC", "LMC", "SAS", "PRI", "HKG", "GRL"}
    assert {"USA", "CHN", "IND", "TWN"} <= set(df["iso3"])


def test_country_table_keeps_nulls_null():
    # The World Bank omits Taiwan, so its population is unknown, not zero.
    df = pd.read_parquet(GLOBAL).set_index("iso3")
    assert pd.isna(df.at["TWN", "population"])
    assert pd.isna(df.at["SGP", "water_stress_bws"])  # Aqueduct has no score for Singapore


def test_clean_grid_beats_coal_grid_on_carbon():
    df = pd.read_parquet(GLOBAL).set_index("iso3")
    assert df.at["NOR", "grid_co2_g_kwh"] < df.at["FRA", "grid_co2_g_kwh"] < df.at["POL", "grid_co2_g_kwh"]
    assert df.at["POL", "grid_co2_g_kwh"] < df.at["ZAF", "grid_co2_g_kwh"]


def test_generation_gate_excludes_grids_too_small_for_the_facility():
    # 300 MW at 0.8 load factor is about 2.1 TWh a year; below 20 TWh it is over a tenth of the grid.
    cond = load_yaml(COND)
    df, _ = load_features(GLOBAL, key="iso3")
    ranked, excluded, _ = rank(df, cond, load_yaml(PILLARS))
    gen = df.set_index("iso3")["electricity_generation_twh"]
    assert (gen[ranked["iso3"]].dropna() >= 20).all()
    assert "min_electricity_generation_twh" in excluded.set_index("iso3").at["ISL", "failed_gates"]
    assert not {"LIE", "MCO", "AND", "SMR"} & set(ranked["iso3"])  # null generation, caught by population
    assert "USA" in set(ranked["iso3"])


def test_committed_global_results_match_a_fresh_run(tmp_path):
    main(["rank", "--conditions", COND, "--pillars", PILLARS, "--features", GLOBAL,
          "--out", str(tmp_path / "g.csv")])
    fresh, committed = pd.read_csv(tmp_path / "g.csv"), pd.read_csv("results/global_balanced.csv")
    assert fresh["iso3"].tolist() == committed["iso3"].tolist()
    assert fresh["composite"].tolist() == pytest.approx(committed["composite"].tolist(), abs=0.01)
