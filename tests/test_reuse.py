"""Stage 2: industrial reuse and community transition (engine/reuse.py and the app section).

It explains a shortlisted county and never feeds the ranking. Economic need is never presented as
community support.
"""
import re
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from engine import reuse
from engine.explain import explain
from engine.rank import load_features, load_yaml, rank
from tests.fake_features import make

TABLE = Path("data/processed/county_features.parquet")
SITES = Path("data/processed/brownfield_sites.parquet")
APP = "../app/app.py"
SUPPORT_WORDS = re.compile(r"\b(support\w*|welcom\w*|want\w*|favor\w*|eager\w*|receptiv\w*|embrac\w*|"
                           r"enthusias\w*|sentiment|approv\w*)\b", re.I)


@pytest.fixture(scope="module")
def table():
    return pd.read_parquet(TABLE)


@pytest.fixture(scope="module")
def stats(table):
    return reuse.national_stats(table)


def items(p):
    return {i["column"]: i for rows in p["sections"].values() for i in rows}


# --- economic data, complete and partial ---------------------------------------------

def test_complete_economic_profile_with_national_context(table, stats):
    p = reuse.profile(table, "17007", stats)  # Boone, IL: documented manufacturing decline
    i = items(p)
    assert i["mfg_emp_2015"]["display"] == "7,761" and i["mfg_emp_2024"]["display"] == "2,070"
    assert i["mfg_emp_change_2015_2024"]["display"] == "-5,691"
    assert i["mfg_emp_pct_change_2015_2024"]["display"] == "-73%"
    assert i["unemployment_rate_pct_2024"]["display"] == "5.9%"
    assert i["unemployment_rate_pct_2024"]["national_median"] == "3.8%"
    assert i["mfg_emp_change_2015_2024"]["national_percentile"] <= 2
    assert p["missing"] == []
    assert any("5,691" in b for b in reuse.benefits(p))


def test_partially_missing_economic_data_is_shown_as_not_available(table, stats):
    p = reuse.profile(table, "09110", stats)  # Capitol Planning Region, CT: no 2015 QCEW or ERS economic codes
    i = items(p)
    assert i["mfg_emp_2015"]["display"] == "not available"
    assert i["mfg_emp_change_2015_2024"]["national_percentile"] is None
    assert "Manufacturing jobs, 2015 (QCEW, private)" in p["missing"]
    assert i["mfg_emp_2024"]["display"] != "not available"  # what exists still shows
    assert any("suppressed or unavailable" in v for v in reuse.verification(p))


def test_table_without_any_stage2_columns_still_profiles():
    df = make(n=40)
    p = reuse.profile(df, df.fips.iloc[0], reuse.national_stats(df))
    i = items(p)
    assert all(i[c]["display"] == "not available" for c in i if c.startswith("bf_"))  # absent columns
    assert i["coal_retired_mw"]["display"].endswith("MW")  # columns the table has still show
    assert len(p["missing"]) > 20
    assert reuse.benefits(p)[0].startswith("The data shows no strong")


# --- brownfields -------------------------------------------------------------------

def test_missing_site_artifact_returns_none(tmp_path):
    assert reuse.load_sites(tmp_path / "absent.parquet") is None
    assert reuse.county_sites(None, "17007") is None


def test_county_with_zero_brownfields(table, stats):
    p = reuse.profile(table, "53025", stats)  # Grant, WA
    i = items(p)
    assert i["bf_site_count"]["display"] == "0" and i["bf_known_acres"]["display"] == "0.0 acres"
    assert i["bf_acreage_reporting_share"]["display"] == "no properties"
    assert "Acreage reporting coverage" not in p["missing"]
    if SITES.exists():
        assert reuse.county_sites(pd.read_parquet(SITES), "53025").empty


def test_county_with_sites_but_no_reported_acreage(table, stats):
    fips = table[(table.bf_site_count > 0) & table.bf_known_acres.isna()].fips.iloc[0]
    p = reuse.profile(table, fips, stats)
    i = items(p)
    assert i["bf_known_acres"]["display"] == "not reported for any property"  # never 0
    assert i["bf_known_acres_sites"]["display"] == "0"
    assert any("reports acreage" in v for v in reuse.verification(p))


def test_site_table_columns_and_order():
    if not SITES.exists():
        pytest.skip("brownfield_sites.parquet absent; run python -m etl.build_features to generate it")
    s = reuse.county_sites(pd.read_parquet(SITES), "17007")
    assert len(s) == 8
    assert list(s.columns) == list(reuse.SITE_COLUMNS.values())
    acres = s["Reported acres"].dropna()
    assert acres.is_monotonic_decreasing
    assert set(s["Ready for reuse"]) <= {"yes", "no", "not reported"}
    assert s["EPA profile"].str.startswith("https://cimc.epa.gov/").all()


# --- framing and export ------------------------------------------------------------

def test_economic_need_is_never_framed_as_support(table, stats):
    needy = table.sort_values("unemployment_rate_pct_3yr_2022_2024", ascending=False).fips.head(25).tolist()
    for fips in needy + ["17007", "53025"]:
        for line in reuse.benefits(reuse.profile(table, fips, stats)):
            assert not SUPPORT_WORDS.search(line), (fips, line)
    assert "not evidence of community support" in reuse.SUPPORT_DISCLAIMER
    assert any(v.startswith("Local engagement") for v in reuse.VERIFICATION)


def test_brief_covers_rank_evidence_risks_gaps_and_verification(table, stats):
    df, _ = load_features(TABLE)
    conditions = {**load_yaml("engine/conditions/balanced.yaml"), "robustness": {"samples": 0}}
    e = explain(df, conditions, load_yaml("engine/pillars.yaml"), "09110")
    text = reuse.brief(e, reuse.profile(table, "09110", stats))
    for heading in ("## Pillar scores", "## Economic transition", "## Industrial reuse", "## Infrastructure context",
                    "## Why this community could benefit", "## Key risks", "## Missing data",
                    "## What still requires local verification"):
        assert heading in text, heading
    assert text.count(reuse.SUPPORT_DISCLAIMER) == 2
    assert "Manufacturing jobs, 2015 (QCEW, private)" in text.split("## Missing data")[1]
    body = text.replace(reuse.SUPPORT_DISCLAIMER, "").split("## What still requires local verification")[0]
    assert not SUPPORT_WORDS.search(body)


# --- rankings untouched --------------------------------------------------------------

def test_stage2_is_not_an_input_to_the_ranking():
    imports = re.compile(r"from engine import reuse|import engine\.reuse|from engine\.reuse|from \.reuse|import reuse")
    for path in ("engine/rank.py", "engine/explain.py", "engine/__main__.py", "etl/build_features.py"):
        assert not imports.search(Path(path).read_text()), path
    assert "bf_" not in Path("engine/pillars.yaml").read_text()  # no Stage 2 column is scored


def test_default_rankings_match_committed_results():
    df, _ = load_features(TABLE)
    ranked, excluded, report = rank(df, load_yaml("engine/conditions/balanced.yaml"), load_yaml("engine/pillars.yaml"))
    shipped = pd.read_csv("results/balanced.csv", dtype={"fips": str})
    assert ranked.fips.tolist() == shipped.fips.tolist()
    assert (ranked.composite.round(2).values == shipped.composite.values).all()
    assert report["floor_ok"] == 883 and ranked.iloc[0].county_name == "Grant"


# --- app -----------------------------------------------------------------------------

@pytest.fixture
def fake_app(tmp_path, monkeypatch):
    df = make(n=120)
    df.to_parquet(tmp_path / "county_features.parquet", index=False)
    monkeypatch.setenv("BAC_FEATURES", str(tmp_path / "county_features.parquet"))
    monkeypatch.setenv("BAC_GEOJSON", str(tmp_path / "absent.geojson"))
    monkeypatch.setenv("BAC_SITES", str(tmp_path / "absent_sites.parquet"))


def test_app_section_without_site_artifact_or_stage2_columns(fake_app):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    assert [h.value for h in at.header] == ["Industrial reuse and community transition"]
    assert reuse.SUPPORT_DISCLAIMER in [w.value for w in at.warning]
    assert reuse.SITES_ABSENT in [i.value for i in at.info]
    assert "What still requires local verification" in [s.value for s in at.subheader]
    assert "Download county screening brief (Markdown)" in [b.label for b in at.get("download_button")]


@pytest.mark.skipif(not SITES.exists(), reason="brownfield_sites.parquet absent; run python -m etl.build_features")
def test_app_renders_the_site_table_and_map_options_on_the_real_table(monkeypatch):
    monkeypatch.setenv("BAC_SITES", str(SITES.resolve()))
    at = AppTest.from_file(APP, default_timeout=300).run()
    assert not at.exception, at.exception
    assert "EPA lists no brownfield properties in this county." in [c.value for c in at.caption]  # Grant
    search = next(s for s in at.selectbox if s.label == "Find a county")
    search.set_value(next(o for o in search.options if "(17007)" in o)).run()
    assert not at.exception, at.exception
    sites = [d.value for d in at.dataframe if "Property" in d.value.columns]
    assert sites and len(sites[0]) == 8
    assert "Download this county's 8 brownfield properties (CSV)" in [b.label for b in at.get("download_button")]
    color = next(s for s in at.selectbox if s.label == "Color the map by")
    assert color.value == "composite"  # composite stays the default view
    for option in reuse.MAP_OPTIONS:
        next(s for s in at.selectbox if s.label == "Color the map by").set_value(option).run()
        assert not at.exception, (option, at.exception)


# --- readability -------------------------------------------------------------------

def test_decline_percentiles_say_how_to_read_them(table, stats):
    i = items(reuse.profile(table, "17007", stats))
    assert i["mfg_emp_change_2015_2024"]["national_percentile"] <= 2
    assert i["mfg_emp_change_2015_2024"]["reading"] == "Low percentile = steeper decline"
    assert i["unemployment_rate_pct_2024"]["reading"].startswith("High percentile = more unemployment")
    assert "not a good result" in reuse.PERCENTILE_NOTE


def test_brief_states_stage2_is_unscored_post_ranking_screening(table, stats):
    df, _ = load_features(TABLE)
    e = explain(df, {**load_yaml("engine/conditions/balanced.yaml"), "robustness": {"samples": 0}},
                load_yaml("engine/pillars.yaml"), "17007")
    text = reuse.brief(e, reuse.profile(table, "17007", stats))
    assert "unscored, post-ranking screening" in text and reuse.PERCENTILE_NOTE in text
    assert "| How to read |" in text and "Low percentile = steeper decline" in text


def _open(at, fips):
    search = next(s for s in at.selectbox if s.label == "Find a county")
    search.set_value(next(o for o in search.options if f"({fips})" in o)).run()
    assert not at.exception, (fips, at.exception)


def test_app_tables_show_labels_once_and_state_the_scope(monkeypatch):
    monkeypatch.setenv("BAC_SITES", str(Path("absent_sites.parquet").resolve()))
    at = AppTest.from_file(APP, default_timeout=300).run()
    assert not at.exception, at.exception
    captions = [c.value for c in at.caption]
    assert any("Unscored, post-ranking screening" in c and "any county" in c for c in captions)
    assert reuse.SITES_ABSENT in [i.value for i in at.info]  # works without the site file
    scored = [d.value for d in at.dataframe if {"column", "raw", "percentile"} <= set(d.value.columns)]
    assert scored, "expected the permitting and every-scored-column tables"
    for df in scored:
        if "label" in df.columns:  # a label appears only where it differs from the raw name
            assert not (df["label"] == df["column"]).any()
            assert set(df.loc[df["label"] != "", "column"]) <= set(reuse_labels())
    _open(at, "09110")  # Connecticut planning region: partial economic data
    assert reuse.SUPPORT_DISCLAIMER in [w.value for w in at.warning]
    econ = next(d.value for d in at.dataframe if "Measure" in d.value.columns)
    assert (econ["County"] == "not available").any() and "How to read" in econ.columns


def reuse_labels():
    from engine.explain import COLUMN_LABELS
    return COLUMN_LABELS
