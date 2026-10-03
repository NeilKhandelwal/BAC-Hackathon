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
    out = score(df, pillars, {"p": 1}).scores
    # County 1 has b null, so its pillar is its percentile on a alone, not dragged to zero or the median.
    assert out["pillar_p"][1] == pytest.approx(percentile(df["a"])[1])


def test_missing_column_is_skipped_and_empty_pillar_dropped_with_weights_renormalized():
    df = table(a=[1.0, 2.0, 3.0], c=[3.0, 2.0, 1.0])
    pillars = {
        "p1": [{"column": "a", "direction": "higher_better"}, {"column": "not_there", "direction": "higher_better"}],
        "p2": [{"column": "also_not_there", "direction": "higher_better"}],
        "p3": [{"column": "c", "direction": "higher_better"}],
    }
    out, cols, warns, *_ = score(df, pillars, {"p1": 0.25, "p2": 0.5, "p3": 0.25})
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
    future, _, _, swapped, *_ = score(df, HORIZON_PILLARS, {"climate": 1}, 2050, "rcp85")
    assert today["composite"].idxmax() == 0
    assert future["composite"].idxmin() == 0
    assert swapped == ["cdd_2050_rcp85"]


def test_2050_falls_back_to_today_with_a_warning_when_the_future_column_is_absent():
    df = table(cdd_hist=[100.0, 200.0])
    out, _, warns, swapped, *_ = score(df, HORIZON_PILLARS, {"climate": 1}, 2050, "rcp45")
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


def test_rank_delta_2050_tracks_rank_movement_among_gate_passed_counties():
    df = table(cdd_hist=[100.0, 200.0, 300.0], cdd_2050_rcp85=[900.0, 400.0, 500.0])
    ranked, _, _ = rank(df, {"weights": {"climate": 1}, "gates": {}}, HORIZON_PILLARS)
    d = ranked.set_index("fips")["rank_delta_2050"]
    assert d["00000"] == 2  # first today, third by 2050
    assert d["00001"] == -1


# Explanations

def test_top_reasons_names_the_columns_that_lift_the_composite():
    # County 0 is best on a and worst on b; with a weighted heavily, a must lead its reasons.
    df = table(a=[3.0, 2.0, 1.0], b=[1.0, 2.0, 3.0])
    pillars = {"pa": [{"column": "a"}], "pb": [{"column": "b"}]}
    ranked, _, _ = rank(df, {"weights": {"pa": 0.9, "pb": 0.1}, "gates": {}}, pillars)
    assert ranked.set_index("fips").loc["00000", "top_reasons"].split(";")[0] == "a"


def test_explain_returns_raw_values_percentiles_gates_and_raw_2050_change():
    from engine.explain import explain
    df = table(cdd_hist=[100.0, 200.0, 300.0], cdd_2050_rcp85=[900.0, 400.0, 500.0],
               fiber_share_locations=[0.9, np.nan, 0.1])
    cond = {"name": "t", "weights": {"climate": 1}, "gates": {"min_fiber_share_locations": 0.4}}
    e = explain(df, cond, HORIZON_PILLARS, "1")
    assert e["passed_gates"] and e["unknown_gates"] == ["min_fiber_share_locations"]
    assert e["pillars"]["climate"]["columns"][0]["raw"] == 200.0
    # Raw change is what tells the 2050 story; percentiles alone hide uniform warming.
    assert e["horizon_2050_raw"]["cdd_hist"]["delta"] == 200.0
    e2 = explain(df, cond, HORIZON_PILLARS, "00002")
    assert not e2["passed_gates"] and e2["rank"] is None and e2["failed_gates"] == ["min_fiber_share_locations"]


# Robustness

def robust_setup(**kw):
    # County 0 wins under heavy weight on a; county 1 under heavy weight on b.
    rng = np.random.default_rng(1)
    a, b = rng.uniform(0, 50, 30), rng.uniform(0, 50, 30)
    a[0], b[0] = 100.0, 60.0
    a[1], b[1] = 60.0, 100.0
    df = table(a=a, b=b)
    pillars = {"pa": [{"column": "a"}], "pb": [{"column": "b"}]}
    cond = {"weights": {"pa": 0.8, "pb": 0.2}, "gates": {},
            "robustness": {"samples": 500, "concentration": 20, "top_n": 1, **kw}}
    return df, pillars, cond


def test_robustness_rewards_the_county_that_wins_under_most_plausible_weights():
    df, pillars, cond = robust_setup()
    r = rank(df, cond, pillars)[0].set_index("fips")["robustness"]
    assert r["00000"] > 0.9 and r["00001"] < 0.1
    assert r.sum() == pytest.approx(1.0)  # top_n=1, so each draw credits exactly one county


def test_robustness_is_reproducible_with_a_seed_and_loosens_with_low_concentration():
    df, pillars, cond = robust_setup()
    r1 = rank(df, cond, pillars)[0]["robustness"]
    r2 = rank(df, cond, pillars)[0]["robustness"]
    assert r1.equals(r2)
    df, pillars, loose = robust_setup(concentration=0.5)
    r = rank(df, loose, pillars)[0].set_index("fips")["robustness"]
    assert r["00001"] > 0.1  # wide draws sometimes favor b


def test_robustness_respects_the_floor_rule():
    # County 0 has the top composite in every draw but fails the floor, so it is never in the top 1.
    n = 10
    a, b = np.linspace(10, 90, n), np.linspace(90, 10, n)
    a[0], b[0] = 100.0, 0.0
    a[1], b[1] = 60.0, 60.0
    df = table(a=a, b=b)
    cond = {"weights": {"pa": 0.9, "pb": 0.1}, "gates": {}, "pillar_floor_percentile": 20,
            "robustness": {"samples": 200, "top_n": 1}}
    r = rank(df, cond, {"pa": [{"column": "a"}], "pb": [{"column": "b"}]})[0].set_index("fips")["robustness"]
    assert r["00000"] == 0


def test_report_counts_exposed_counties_for_each_hazard_gate():
    df = table(nri_coastal_flood_score=[0.0] * 8 + [5.0, 50.0])
    cond = {"weights": {"p": 1}, "gates": {"hazard_percentile_max": {"nri_coastal_flood_score": 85}}}
    _, _, report = rank(df, cond, {"p": [{"column": "nri_coastal_flood_score"}]})
    assert report["hazard_gate_nonzero_counties"] == {"hazard_percentile_max.nri_coastal_flood_score": 2}
    assert report["gate_failures"]["hazard_percentile_max.nri_coastal_flood_score"] == 2


def test_top_reasons_ignores_a_heavy_single_column_pillar_tied_for_most_counties():
    # Mirrors air_nonattainment_count: alone in a heavy pillar and 0 almost everywhere.
    # It says nothing about why one clean county beats another, so it must not lead.
    n = 20
    df = table(tied=[0.0] * (n - 1) + [2.0], a=np.arange(n, dtype=float), b=np.arange(n, dtype=float))
    pillars = {"permit": [{"column": "tied", "direction": "lower_better"}],
               "other": [{"column": "a"}, {"column": "b"}]}
    ranked, _, _ = rank(df, {"weights": {"permit": 0.5, "other": 0.5}, "gates": {}}, pillars)
    assert ranked.iloc[0]["top_reasons"].split(";")[0] in ("a", "b")


# Power deliverability

def test_nearby_capacity_gate_scales_with_facility_size():
    # 1,000 MW nearby can plausibly feed a 100 MW campus at 5x but not a 300 MW one.
    df = table(plant_capacity_mw_100km=[1000.0, 2000.0, np.nan])
    gates = {"min_nearby_capacity_multiple": 5}
    small = apply_gates(df, {"gates": gates, "facility": {"mw": 100}})
    big = apply_gates(df, {"gates": gates, "facility": {"mw": 300}})
    assert list(small["failed_gates"]) == ["", "", ""]
    assert list(big["failed_gates"]) == ["min_nearby_capacity_multiple", "", ""]
    assert big["unknown_gates"][2] == "min_nearby_capacity_multiple"  # null is unknown, not a failure


def test_nearby_capacity_gate_without_facility_mw_fails_loudly():
    df = table(plant_capacity_mw_100km=[1000.0])
    with pytest.raises(ValueError, match="facility.mw"):
        apply_gates(df, {"gates": {"min_nearby_capacity_multiple": 5}, "facility": {}})


def test_top_reasons_lists_only_columns_above_the_median():
    # The worst county has nothing lifting it; naming its least-bad column as a "reason" would mislead.
    df = table(a=[1.0, 2.0, 3.0, 4.0], b=[1.0, 2.0, 3.0, 4.0])
    pillars = {"p": [{"column": "a"}, {"column": "b"}]}
    ranked = rank(df, {"weights": {"p": 1}, "gates": {}}, pillars)[0].set_index("fips")
    assert ranked.loc["00000", "top_reasons"] == ""
    assert set(ranked.loc["00003", "top_reasons"].split(";")) == {"a", "b"}


# Review fixes from PR #4

def test_horizon_accepts_numeric_strings_and_rejects_unsupported_years():
    # A UI or JSON round trip turns 2050 into "2050"; that must not silently score today's climate.
    df = table(cdd_hist=[100.0, 200.0, 300.0], cdd_2050_rcp85=[900.0, 400.0, 500.0])
    base = {"weights": {"climate": 1}, "gates": {}}
    as_int = rank(df, {**base, "horizon": 2050}, HORIZON_PILLARS)[0]
    as_str = rank(df, {**base, "horizon": "2050"}, HORIZON_PILLARS)[0]
    assert as_int["composite"].tolist() == as_str["composite"].tolist()
    for bad in (2040, "soon", None):
        with pytest.raises(ValueError, match="horizon"):
            rank(df, {**base, "horizon": bad}, HORIZON_PILLARS)


def test_floor_ignores_pillars_weighted_zero():
    # All weight on a: the best county on a must rank first even though it is worst on b,
    # which the user said doesn't matter.
    n = 10
    a, b = np.linspace(10, 90, n), np.linspace(90, 10, n)
    a[0], b[0] = 100.0, 0.0
    df = table(a=a, b=b)
    cond = {"weights": {"pa": 1.0, "pb": 0.0}, "gates": {}, "pillar_floor_percentile": 20,
            "robustness": {"samples": 0}}
    ranked = rank(df, cond, {"pa": [{"column": "a"}], "pb": [{"column": "b"}]})[0]
    assert ranked.iloc[0]["fips"] == "00000" and ranked.iloc[0]["floor_ok"]


def test_robustness_is_null_with_a_warning_when_the_field_is_not_larger_than_top_n():
    # With 5 eligible counties and top_n 10, every county would read 1.0, which says nothing.
    df = table(a=np.arange(5, dtype=float))
    cond = {"weights": {"p": 1}, "gates": {}, "robustness": {"samples": 100, "top_n": 10}}
    ranked, _, report = rank(df, cond, {"p": [{"column": "a"}]})
    assert ranked["robustness"].isna().all()
    assert any("robustness not computed" in w for w in report["warnings"])


def test_floor_failing_counties_never_fill_empty_top_n_slots():
    # 7 counties pass the floor and top_n is 8. The old code filled the eighth slot with a
    # floor-failing county in every draw, crediting it as robust. Now the field is too small
    # to say anything, so every county is null, failers included.
    a = np.array([100.0] * 3 + [50.0] * 7)                     # failers lead on the heavy pillar
    b = np.array([0.0, -1.0, -2.0] + list(np.linspace(40, 90, 7)))  # failers sit at pctl 10-30 on b
    df = table(a=a, b=b)
    cond = {"weights": {"pa": 0.9, "pb": 0.1}, "gates": {}, "pillar_floor_percentile": 35,
            "robustness": {"samples": 200, "top_n": 8}}
    ranked, _, report = rank(df, cond, {"pa": [{"column": "a"}], "pb": [{"column": "b"}]})
    assert ranked["floor_ok"].sum() == 7
    assert ranked["robustness"].isna().all()
    cond["robustness"]["top_n"] = 2  # a field larger than top_n: hits go to floor-passers only
    r = rank(df, cond, {"pa": [{"column": "a"}], "pb": [{"column": "b"}]})[0].set_index("fips")
    assert (r.loc[["00000", "00001", "00002"], "robustness"] == 0).all()
    assert r["robustness"].sum() == pytest.approx(2.0)


def test_explain_text_survives_null_robustness_and_composite():
    from engine.explain import explain, format_text
    df = table(a=[1.0, 2.0, 3.0])
    cond = {"name": "t", "weights": {"p": 1}, "gates": {}, "robustness": {"samples": 0}}
    text = format_text(explain(df, cond, {"p": [{"column": "a"}]}, "00001"))
    assert "robustness n/a" in text


def test_unknown_gate_keys_and_missing_gate_columns_warn():
    # A misspelled hard exclusion that excludes nothing is a silent wrong answer.
    df = table(nri_wildfire_score=[1.0, 2.0])
    cond = {"weights": {"p": 1}, "gates": {"max_grid_co2": 100,
                                           "hazard_percentile_max": {"nri_wildfire": 50}}}
    _, _, report = rank(df, cond, {"p": [{"column": "nri_wildfire_score"}]})
    assert any("gates.max_grid_co2 is not a known gate" in w for w in report["warnings"])
    assert any("nri_wildfire is not in the table" in w for w in report["warnings"])


def test_scalar_states_include_raises_a_clear_error():
    df = table(population=[1, 2])
    with pytest.raises(ValueError, match="states_include must be a list"):
        apply_gates(df, {"gates": {"states_include": "IA"}})


def test_coverage_counts_scored_columns_absent_from_the_table():
    # Two of four mapped columns don't exist, so no county can claim full coverage.
    df = table(a=[1.0, 2.0], b=[1.0, np.nan])
    pillars = {"p": [{"column": "a"}, {"column": "b"}, {"column": "c"}, {"column": "d"}]}
    out = score(df, pillars, {"p": 1}).scores
    assert out["coverage"].tolist() == [0.5, 0.25]


def test_explain_with_a_precomputed_result_matches_a_fresh_run():
    # The app passes its cached rank result; that shortcut must not change the answer.
    from engine.explain import explain
    df = make(n=120)
    cond = load_yaml(PRESETS[0])
    pillars = load_yaml(ROOT / "engine/pillars.yaml")
    result = rank(df, cond, pillars)
    for fips in (result[0]["fips"].iloc[0], result[1]["fips"].iloc[0]):  # one ranked, one excluded
        assert explain(df, cond, pillars, fips, result=result) == explain(df, cond, pillars, fips)


def test_top_reasons_are_computed_for_ranked_counties_only():
    df = make(n=120)
    ranked, excluded, _ = rank(df, load_yaml(PRESETS[0]), load_yaml(ROOT / "engine/pillars.yaml"))
    assert ranked["top_reasons"].map(lambda v: isinstance(v, str)).all()
    assert "top_reasons" not in excluded.columns


# CLI errors

@pytest.mark.parametrize("cmd", ["rank", "explain"])
def test_cli_reports_bad_conditions_in_one_line_and_exits_2(tmp_path, capsys, cmd):
    # A user editing a conditions file needs the reason, not a stack trace.
    make(n=50).to_parquet(tmp_path / "f.parquet", index=False)
    cond = load_yaml(PRESETS[0])
    cond["horizon"] = 2040
    (tmp_path / "c.yaml").write_text(__import__("yaml").safe_dump(cond))
    extra = ["--out", str(tmp_path / "o.csv")] if cmd == "rank" else ["--fips", "01001"]
    with pytest.raises(SystemExit) as exit_info:
        main([cmd, "--conditions", str(tmp_path / "c.yaml"), "--features", str(tmp_path / "f.parquet"), *extra])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert err[-1] == "error: horizon must be 2026 or 2050, got 2040"
    assert not any("Traceback" in line for line in err)


def test_cli_explain_unknown_fips_exits_2(tmp_path, capsys):
    make(n=50).to_parquet(tmp_path / "f.parquet", index=False)
    with pytest.raises(SystemExit) as exit_info:
        main(["explain", "--conditions", str(PRESETS[0]), "--features", str(tmp_path / "f.parquet"), "--fips", "99999"])
    assert exit_info.value.code == 2
    assert capsys.readouterr().err.strip() == "error: fips 99999 not in the feature table"


# Floor exemption

def exempt_setup():
    # County 0 leads the composite but sits at the bottom of the permitting pillar only.
    n = 10
    a = np.linspace(40, 90, n)
    permit = np.linspace(90, 40, n)
    a[0], permit[0] = 100.0, 0.0
    df = table(a=a, permit=permit)
    pillars = {"pa": [{"column": "a"}], "permitting": [{"column": "permit"}]}
    cond = {"weights": {"pa": 0.8, "permitting": 0.2}, "gates": {}, "pillar_floor_percentile": 20,
            "robustness": {"samples": 300, "top_n": 2}}
    return df, pillars, cond


def test_a_county_below_the_floor_only_on_an_exempt_pillar_stays_in_the_floor_passing_group():
    # Permitting is three coarse state-level integers; one step must not drop a strong county
    # below every floor-passing county. Without the exemption it does.
    df, pillars, cond = exempt_setup()
    ranked = rank(df, cond, pillars)[0]
    strict = ranked.set_index("fips").loc["00000"]
    assert not strict["floor_ok"] and strict["rank"] > ranked["floor_ok"].sum()  # below every floor-passer
    exempt = rank(df, {**cond, "pillar_floor_exempt": ["permitting"]}, pillars)[0].set_index("fips").loc["00000"]
    assert exempt["floor_ok"] and exempt["rank"] == 1


def test_floor_exemption_flows_through_to_robustness():
    df, pillars, cond = exempt_setup()
    strict = rank(df, cond, pillars)[0].set_index("fips")["robustness"]
    exempt = rank(df, {**cond, "pillar_floor_exempt": ["permitting"]}, pillars)[0].set_index("fips")["robustness"]
    assert strict["00000"] == 0 and exempt["00000"] > 0.9


def test_rank_delta_2050_uses_the_same_floor_exemption():
    # rank_delta_2050 must equal the rank movement you'd see running each horizon on its own.
    df, _, cond = exempt_setup()
    df["cdd_hist"] = np.linspace(100, 1000, len(df))
    df["cdd_2050_rcp85"] = np.linspace(1000, 100, len(df))
    pillars = {"pa": [{"column": "a"}], "climate": HORIZON_PILLARS["climate"], "permitting": [{"column": "permit"}]}
    cond = {**cond, "weights": {"pa": 0.6, "climate": 0.2, "permitting": 0.2}, "pillar_floor_exempt": ["permitting"]}
    both = rank(df, cond, pillars)[0].set_index("fips")
    r26 = rank(df, {**cond, "horizon": 2026}, pillars)[0].set_index("fips")["rank"]
    r50 = rank(df, {**cond, "horizon": 2050}, pillars)[0].set_index("fips")["rank"]
    assert (both["rank_delta_2050"] == (r50 - r26).reindex(both.index)).all()


def test_floor_exempt_rejects_unknown_pillar_names_and_non_lists():
    df, pillars, cond = exempt_setup()
    with pytest.raises(ValueError, match="unknown pillars: permiting"):
        rank(df, {**cond, "pillar_floor_exempt": ["permiting"]}, pillars)
    with pytest.raises(ValueError, match="must be a list"):
        rank(df, {**cond, "pillar_floor_exempt": "permitting"}, pillars)


def test_explain_marks_exempt_pillars():
    from engine.explain import explain, format_text
    df, pillars, cond = exempt_setup()
    e = explain(df, {**cond, "name": "t", "pillar_floor_exempt": ["permitting"]}, pillars, "00000")
    assert e["pillar_floor_exempt"] == ["permitting"] and e["pillars"]["permitting"]["floor_exempt"]
    assert "permitting (floor exempt)" in format_text(e)


def test_every_preset_exempts_permitting_and_ships_no_model_gate():
    for preset in PRESETS:
        c = load_yaml(preset)
        assert c["pillar_floor_exempt"] == ["permitting"], preset.stem
        assert c["gates"]["max_permitting_risk"] is None, preset.stem  # the model is dropped


# Industrial reuse and economic opportunity

def twin_counties(**changes):
    """Two fake counties identical in every column except the ones in changes, which county 1 takes."""
    df = make(n=200, null_share=0.0)
    df.loc[1, df.columns.drop(["fips", "county_name"])] = df.loc[0, df.columns.drop(["fips", "county_name"])]
    for col, (v0, v1) in changes.items():
        df.loc[0, col], df.loc[1, col] = v0, v1
    sc = score(df, load_yaml(ROOT / "engine/pillars.yaml"), load_yaml(PRESETS[0])["weights"]).scores
    return sc.loc[0], sc.loc[1]


def test_retired_coal_capacity_raises_the_grid_pillar():
    # A retired plant's interconnection can be reused, so more retired MW means easier power.
    a, b = twin_counties(coal_retired_mw=(0.0, 800.0))
    assert b["pillar_grid_infrastructure"] > a["pillar_grid_infrastructure"]
    assert b["pillar_community"] == a["pillar_community"]  # infrastructure only, no community claim


def test_higher_unemployment_raises_the_community_pillar():
    # Stated value: a campus brings more benefit where jobs are scarce.
    a, b = twin_counties(unemployment_rate_pct_2023=(2.5, 7.0))
    assert b["pillar_community"] > a["pillar_community"]


def test_steeper_population_decline_raises_the_community_pillar():
    # Stated value: more benefit, and more available workforce, where population is falling.
    a, b = twin_counties(pop_change_pct_2010_2024=(10.0, -15.0))
    assert b["pillar_community"] > a["pillar_community"]
    assert b["pillar_grid_infrastructure"] == a["pillar_grid_infrastructure"]
