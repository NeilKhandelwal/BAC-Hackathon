"""Queue-semantics correction and the audit findings behind it (research/etl_semantics_audit.md).

energy_carbon scores clean generation excluding storage and capacity delivered 2021-2025 by online
date. The legacy queue columns stay in the table, unscored. FracTracker findings at the end are
documented follow-ups, asserted as production behaves today.
"""
import importlib.util
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import yaml

from engine.explain import COLUMN_LABELS, explain
from engine.rank import load_features, load_yaml, rank
from etl.adapters.lbnl_queue_alt import clean_generation_mw, is_standalone_storage
from etl.schema import CORE
from tests.conftest import RAW, require_raw

AUDIT = Path("research/etl_semantics_audit")
_spec = importlib.util.spec_from_file_location("run_audit", AUDIT / "run_audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)
SCORED = {"queue_active_mw_clean_excl_storage", "queue_operational_mw_online_5y"}
LEGACY = {"queue_active_mw_clean", "queue_operational_mw_5y"}


@pytest.fixture(scope="module")
def table():
    return pd.read_parquet("data/processed/county_features.parquet").set_index("fips", drop=False)


@pytest.fixture(scope="module")
def summary():
    return json.loads((AUDIT / "audit_summary.json").read_text())


def _queue(rows):
    return pd.DataFrame(rows, columns=["type_clean", "type_1", "type_2", "type_3", "mw_1", "mw_2", "mw_3"])


# --- scoring mapping ----------------------------------------------------------------

def test_energy_carbon_scores_the_corrected_queue_measures():
    pillars = yaml.safe_load(Path("engine/pillars.yaml").read_text())
    energy = {m["column"] for m in pillars["energy_carbon"]}
    assert SCORED <= energy
    scored = {m["column"] for metrics in pillars.values() for m in metrics}
    assert not LEGACY & scored


def test_legacy_queue_columns_are_kept_for_traceability(table):
    assert LEGACY <= set(CORE)
    assert table.queue_active_mw_clean.sum() > table.queue_active_mw_clean_excl_storage.sum()
    assert table.queue_operational_mw_online_5y.sum() > table.queue_operational_mw_5y.sum()


# --- clean generation excluding storage ------------------------------------------------

def test_storage_is_never_clean_generation():
    q = _queue([["Battery", "Battery", None, None, 200.0, np.nan, np.nan],
                ["Other Storage", "Other Storage", None, None, 50.0, np.nan, np.nan],
                ["Pumped Storage", "Pumped Storage", None, None, 400.0, np.nan, np.nan]])
    assert clean_generation_mw(q).tolist() == [0.0, 0.0, 0.0]
    assert audit.main_clean_mask(q).tolist() == [True, True, False]  # legacy counted battery and other storage


def test_each_clean_component_counts_once_and_storage_component_never():
    q = _queue([["Solar+Battery", "Solar", "Battery", None, 100.0, 40.0, np.nan],
                ["Solar+Wind+Battery", "Solar", "Wind", "Battery", 100.0, 50.0, 30.0]])
    assert clean_generation_mw(q).tolist() == [100.0, 150.0]


def test_missing_component_mw_counts_as_zero():
    # 233 active Solar+Battery rows list type_1 = type_2 = Battery with no solar MW.
    q = _queue([["Solar+Battery", "Battery", "Battery", None, 150.0, np.nan, np.nan],
                ["Wind+Battery", "Wind", "Battery", None, np.nan, 20.0, np.nan]])
    assert clean_generation_mw(q).tolist() == [0.0, 0.0]


def test_clean_component_of_a_gas_or_other_hybrid_counts_when_reported():
    q = _queue([["Solar+Gas", "Solar", "Gas", None, 200.0, 50.0, np.nan],
                ["Gas+Solar", "Gas", "Solar", None, 300.0, np.nan, np.nan]])
    assert clean_generation_mw(q).tolist() == [200.0, 0.0]
    assert not audit.main_clean_mask(q).any()  # the legacy rule dropped both


def test_standalone_storage_includes_other_storage():
    s = pd.Series(["Battery", "Other Storage", "Battery+Other Storage", "Solar+Battery", "Pumped Storage", None])
    assert is_standalone_storage(s).tolist() == [True, True, True, False, True, False]


def test_committed_table_separates_storage_from_clean_generation(table):
    harris = table.loc["48201"]  # Harris County, TX: almost all storage
    assert harris.queue_active_mw_clean > 7000 and harris.queue_active_mw_clean_excl_storage < 100
    assert round(table.queue_active_mw_clean_excl_storage.sum() / 1e3, 1) == 993.2
    assert round(table.queue_active_mw_storage_standalone.sum() / 1e3, 1) == 391.4


# --- delivered capacity by online date -----------------------------------------------

def test_legacy_operational_rule_keys_on_queue_entry():
    q = pd.DataFrame({"q_status": ["operational"] * 3, "q_year": [2016, 2019, np.nan],
                      "on_date": ["2023-06-01", "2020-03-01", "2022-01-01"]})
    assert audit.main_operational_mask(q).tolist() == [False, True, True]


def test_online_date_falls_back_to_proposed_date_only_when_missing():
    q = pd.DataFrame({"on_date": ["2023-01-01", None, None], "prop_date": ["2019-01-01", "2024-05-01", None]})
    online, fallback = audit.online_date(q)
    assert online.dt.year.tolist()[:2] == [2023, 2024] and pd.isna(online.iloc[2])
    assert fallback.tolist() == [False, True, False]


def test_committed_table_counts_recent_deliveries_from_older_queue_entries(table):
    riverside = table.loc["06065"]
    assert riverside.queue_operational_mw_5y == 0 and riverside.queue_operational_mw_online_5y > 3000
    assert round(table.queue_operational_mw_online_5y.sum() / 1e3, 1) == 152.3
    assert table.queue_operational_online_date_fallback_share.dropna().between(0, 1).all()


def test_fallback_is_substantial_in_iso_ne_and_the_west(summary):
    q = summary["queue"]["operational"]
    assert q["online5y_projects_dated_by_prop_date"] == 214
    reg = pd.read_csv(AUDIT / "outputs/queue_online_date_by_region.csv").set_index("region") \
        if (AUDIT / "outputs/queue_online_date_by_region.csv").exists() else None
    if reg is not None:
        assert reg.loc["ISO-NE", "share_missing_on_date"] == 1.0 and reg.loc["West", "share_missing_on_date"] > 0.8


# --- results, labels, and provenance ---------------------------------------------------

def test_committed_results_match_the_corrected_mapping(table):
    df, _ = load_features("data/processed/county_features.parquet")
    conditions = load_yaml("engine/conditions/balanced.yaml")
    ranked, _, report = rank(df, {**conditions, "robustness": {"samples": 0}}, load_yaml("engine/pillars.yaml"))
    shipped = pd.read_csv("results/balanced.csv", dtype={"fips": str})
    assert ranked.fips.head(10).tolist() == shipped.fips.head(10).tolist()
    assert shipped.iloc[0].county_name == "Grant"


def test_audit_harness_reproduced_both_mappings(summary):
    assert summary["harness"] == {"corrected_reproduces_results": True,
                                  "legacy_reproduces_pre_correction_results": True}
    rows = pd.DataFrame(summary["rankings"])
    assert rows.gate_failures_equal_legacy.all()
    assert (rows.groupby("preset").winner.nunique() == 1).all()


def test_explanations_label_scored_storage_and_legacy_measures(table):
    df, _ = load_features("data/processed/county_features.parquet")
    conditions = {**load_yaml("engine/conditions/balanced.yaml"), "robustness": {"samples": 0}}
    e = explain(df, conditions, load_yaml("engine/pillars.yaml"), "53025")
    labels = {c["column"]: c["label"] for c in e["pillars"]["energy_carbon"]["columns"]}
    assert labels["queue_active_mw_clean_excl_storage"].startswith("Clean generation in the queue, excluding storage")
    assert labels["queue_operational_mw_online_5y"].startswith("Delivered or estimated online")
    assert {COLUMN_LABELS["queue_active_mw_storage_standalone"], COLUMN_LABELS["queue_active_mw_clean"],
            COLUMN_LABELS["queue_operational_mw_5y"]} <= set(e["context"])
    assert all("not scored" in k for k in e["context"])


# --- FracTracker findings (documented follow-ups, not changed here) ---------------------

@pytest.fixture(scope="module")
def moratoria():
    require_raw("fractracker/ft_moratoria.csv")
    return pd.read_csv(f"{RAW}/fractracker/ft_moratoria.csv", dtype=str)


@pytest.mark.parametrize("fips", ["13115", "37021", "21209"])  # Floyd GA, Buncombe NC, Scott KY
def test_expired_county_moratoria_listed_active_are_not_gated(moratoria, table, fips):
    rows = moratoria[(moratoria.GEOID == fips) & (moratoria.level_ == "county")]
    assert (rows.status == "active").all() and (pd.to_datetime(rows.end_date) < pd.Timestamp("2026-10-03")).all()
    assert not table.loc[fips, "moratorium_active"]


def test_municipal_restrictions_never_set_county_flag(moratoria, table):
    county_level = set(moratoria[moratoria.level_ == "county"].GEOID)
    ended = pd.to_datetime(moratoria.end_date, errors="coerce") < pd.Timestamp("2026-10-03")
    muni = moratoria[(moratoria.level_ == "municipality") & (moratoria.status == "active")
                     & (moratoria.GEOID.str.len() == 10) & ~ended]
    muni_only = sorted(set(muni.GEOID.str[:5]) - county_level & set(table.index))
    assert muni_only and not table.loc[muni_only, "moratorium_active"].any()


def test_name_first_matching_puts_st_louis_city_facilities_in_st_louis_county(table):
    require_raw("fractracker/ft_all.csv", "tiger/cb_2024_us_county_500k.zip")
    ft = pd.read_csv(f"{RAW}/fractracker/ft_all.csv", dtype=str)
    tucker = ft[ft.facility_name.str.contains("210 North Tucker", na=False)].iloc[0]
    counties = gpd.read_file(f"{RAW}/tiger/cb_2024_us_county_500k.zip")
    pt = gpd.GeoDataFrame(geometry=gpd.points_from_xy([float(tucker.long)], [float(tucker.lat)]), crs=4326)
    assert gpd.sjoin(pt.to_crs(counties.crs), counties, predicate="within").GEOID.iloc[0] == "29510"
    assert table.loc["29510", "dc_existing_count"] == 0 and table.loc["29189", "dc_existing_count"] >= 4


def test_main_mw_parse_drops_ranges_and_thousands_separators(table):
    carson = table.loc["48065"]  # Carson County, TX: Fermi America, "11,000-17,000" MW
    assert carson.dc_proposed_mw_reported - carson.dc_proposed_mw >= 14000
