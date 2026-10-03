"""Engine tests. Each one pins a rule from docs/conditions.md that a ranking change could silently break."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.__main__ import main
from engine.rank import apply_gates, floor_ok, load_features, load_yaml, percentile, rank, score
from tests.fake_features import make

ROOT = Path(__file__).resolve().parents[1]
PRESETS = sorted((ROOT / "engine/conditions").glob("*.yaml"))


def table(**cols):
    n = len(next(iter(cols.values())))
    df = pd.DataFrame({"fips": [f"{i:05d}" for i in range(n)], "county_name": "x", "state": "IA"})
    for k, v in cols.items():
        df[k] = v
    return df


# Gates

def test_null_never_excludes_but_is_logged_unknown():
    # A county with no fiber data must stay in play; excluding it would punish missing data, not bad sites.
    df = table(fiber_share_locations=[0.9, np.nan, 0.1])
    log = apply_gates(df, {"gates": {"min_fiber_share_locations": 0.4}})
    assert list(log["failed_gates"]) == ["", "", "min_fiber_share_locations"]
    assert list(log["unknown_gates"]) == ["", "min_fiber_share_locations", ""]


def test_gate_column_absent_from_table_flags_every_county_unknown():
    df = table(population=[100_000, 200_000])
    log = apply_gates(df, {"gates": {"max_queue_median_age_years": 5}})
    assert (log["failed_gates"] == "").all()
    assert (log["unknown_gates"] == "max_queue_median_age_years").all()


def test_moratorium_gate_excludes_only_true_flags():
    df = table(moratorium_active=pd.array([True, False, None], dtype="boolean"))
    log = apply_gates(df, {"gates": {"exclude_moratorium_active": True}})
    assert list(log["failed_gates"]) == ["exclude_moratorium_active", "", ""]


def test_hazard_gate_cuts_on_national_percentile_not_raw_score():
    # Scores 1..100: at a 90th-percentile cap, exactly the 10 most exposed counties fail.
    df = table(nri_inland_flood_score=np.arange(1, 101, dtype=float))
    log = apply_gates(df, {"gates": {"hazard_percentile_max": {"nri_inland_flood_score": 90}}})
    failed = log["failed_gates"] != ""
    assert failed.sum() == 10
    assert failed.iloc[-10:].all()


def test_water_stress_gate_applies_only_to_water_cooled_facilities():
    df = table(water_stress_bws=[4.0])
    gates = {"max_water_stress_if_evaporative": 2}
    assert apply_gates(df, {"gates": gates, "facility": {"cooling": "dry"}})["failed_gates"][0] == ""
    assert apply_gates(df, {"gates": gates, "facility": {"cooling": "evaporative"}})["failed_gates"][0] != ""


def test_states_include_and_exclude():
    df = table(population=[1, 1, 1])
    df["state"] = ["IA", "TX", "VA"]
    log = apply_gates(df, {"gates": {"states_include": ["IA", "TX"], "states_exclude": ["TX"]}})
    assert list(log["failed_gates"]) == ["", "states_exclude", "states_include"]


# Scoring

def test_lower_better_gives_the_smallest_value_the_top_percentile():
    p = percentile(pd.Series([900.0, 100.0, 500.0]), "lower_better")
    assert p.idxmax() == 1 and p.idxmin() == 0


def test_pillar_mean_ignores_null_columns():
    df = table(a=[1.0, 2.0, 3.0], b=[3.0, np.nan, 1.0])
    pillars = {"p": [{"column": "a", "direction": "higher_better"}, {"column": "b", "direction": "higher_better"}]}
    out, _, _, _ = score(df, pillars, {"p": 1})
    # County 1 has b null, so its pillar is its percentile on a alone, not dragged to zero or the median.
    assert out["pillar_p"][1] == pytest.approx(percentile(df["a"])[1])


def test_missing_column_is_skipped_and_empty_pillar_dropped_with_weights_renormalized():
    df = table(a=[1.0, 2.0, 3.0], c=[3.0, 2.0, 1.0])
    pillars = {
        "p1": [{"column": "a", "direction": "higher_better"}, {"column": "not_there", "direction": "higher_better"}],
        "p2": [{"column": "also_not_there", "direction": "higher_better"}],
        "p3": [{"column": "c", "direction": "higher_better"}],
    }
    out, cols, warns, _ = score(df, pillars, {"p1": 0.25, "p2": 0.5, "p3": 0.25})
    assert cols == ["pillar_p1", "pillar_p3"]
    assert any("not_there" in w for w in warns)
    assert any("p2: no available columns" in w for w in warns)
    assert any("renormalized" in w for w in warns)
    # p2's half of the weight is spread evenly over p1 and p3, not silently counted as zero.
    expected = 0.5 * out["pillar_p1"] + 0.5 * out["pillar_p3"]
    assert np.allclose(out["composite"], expected)


def test_manifest_missing_columns_are_dropped_even_if_present(tmp_path):
    df = table(a=[1.0, 2.0])
    df.to_parquet(tmp_path / "county_features.parquet")
    (tmp_path / "county_features.manifest.json").write_text(json.dumps({"columns_missing": ["a"]}))
    loaded, warns = load_features(tmp_path / "county_features.parquet")
    assert "a" not in loaded.columns
    assert warns


# Floor rule

def test_floor_rule_ranks_a_balanced_county_above_a_lopsided_one_with_higher_composite():
    # County 0 is best on p1 but worst on p2; county 1 is middling on both.
    # The brief says don't optimize a single metric, so the middling county must win.
    n = 10
    p1 = np.linspace(10, 100, n)
    p2 = np.linspace(100, 10, n)
    p1[0], p2[0] = 100.0, 0.0
    p1[1], p2[1] = 55.0, 55.0
    df = table(p1=p1, p2=p2)
    pillars = {"a": [{"column": "p1"}], "b": [{"column": "p2"}]}
    conditions = {"weights": {"a": 0.9, "b": 0.1}, "pillar_floor_percentile": 20, "gates": {}}
    ranked, _, report = rank(df, conditions, pillars)
    row0 = ranked.set_index("fips").loc["00000"]
    row1 = ranked.set_index("fips").loc["00001"]
    assert row0["composite"] > row1["composite"]
    assert not row0["floor_ok"] and row1["floor_ok"]
    assert row1["rank"] < row0["rank"]


def test_floor_zero_disables_the_rule():
    scores = pd.DataFrame({"pillar_a": np.arange(10.0)})  # lowest is the 10th percentile
    assert floor_ok(scores, ["pillar_a"], 0).all()
    assert not floor_ok(scores, ["pillar_a"], 20).all()


# End to end

@pytest.mark.parametrize("preset", PRESETS, ids=lambda p: p.stem)
def test_cli_runs_every_preset_on_the_fake_table(tmp_path, preset):
    df = make(n=200)
    df.to_parquet(tmp_path / "county_features.parquet", index=False)
    out = tmp_path / f"{preset.stem}.csv"
    main(["rank", "--conditions", str(preset), "--features", str(tmp_path / "county_features.parquet"),
          "--out", str(out)])
    ranked = pd.read_csv(out, dtype={"fips": str})
    excluded = pd.read_csv(tmp_path / f"{preset.stem}_excluded.csv", dtype={"fips": str})
    assert len(ranked) + len(excluded) == len(df)
    assert ranked["rank"].tolist() == list(range(1, len(ranked) + 1))
    # floor-passing counties all come first
    assert ranked["floor_ok"].astype(bool).is_monotonic_decreasing


# Horizon

HORIZON_PILLARS = {"climate": [{"column": "cdd_hist", "direction": "lower_better",
                                "horizon_2050": "cdd_2050_{scenario}"}]}


def test_2050_scores_on_the_scenario_column_not_today():
    # Today county 0 is coolest; by 2050 under rcp85 it is the hottest. A 30-year asset should see that.
    df = table(cdd_hist=[100.0, 200.0, 300.0], cdd_2050_rcp85=[900.0, 400.0, 500.0], cdd_2050_rcp45=[1.0, 2.0, 3.0])
    today, *_ = score(df, HORIZON_PILLARS, {"climate": 1}, 2026)
    future, _, _, swapped = score(df, HORIZON_PILLARS, {"climate": 1}, 2050, "rcp85")
    assert today["composite"].idxmax() == 0
    assert future["composite"].idxmin() == 0
    assert swapped == ["cdd_2050_rcp85"]


def test_2050_falls_back_to_today_with_a_warning_when_the_future_column_is_absent():
    df = table(cdd_hist=[100.0, 200.0])
    out, _, warns, swapped = score(df, HORIZON_PILLARS, {"climate": 1}, 2050, "rcp45")
    assert swapped == []
    assert any("cdd_2050_rcp45 missing, scoring cdd_hist" in w for w in warns)
    assert out["composite"].notna().all()


def test_horizon_delta_is_2050_minus_2026_and_null_without_future_data():
    df = table(cdd_hist=[100.0, 200.0, 300.0], cdd_2050_rcp85=[900.0, 400.0, 500.0])
    conditions = {"weights": {"climate": 1}, "gates": {}, "horizon": 2026, "scenario": "rcp85"}
    ranked, _, _ = rank(df, conditions, HORIZON_PILLARS)
    d = ranked.set_index("fips")["horizon_delta"]
    assert d["00000"] < 0 < d["00001"]  # county 0 loses its edge by 2050, county 1 gains
    ranked, _, _ = rank(df.drop(columns="cdd_2050_rcp85"), conditions, HORIZON_PILLARS)
    assert ranked["horizon_delta"].isna().all()
