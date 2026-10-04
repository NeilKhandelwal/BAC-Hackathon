"""ETL v2 context columns: units, missingness, joins, and that main's columns don't move.

Unit tests use small synthetic files. Built-table tests read data/processed and skip when it
lacks the v2 columns. Run `python -m etl.build_features` first.
"""
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from etl.adapters import bls_qcew, fractracker_context, lbnl_queue_alt
from etl.schema import CORE, STRETCH, V2_CONTEXT

OUT = Path("data/processed")
BASE_COMMIT = "1575003"  # origin/main before the port
# Area overlays and raster zonal means move in the last digits across geopandas, shapely, and
# rasterio versions. A clean rebuild of 1575003 itself differs by up to 1e-12 in water stress and
# by 0.0005 m/s in one wind cell. Everything else must match exactly.
LIBRARY_SENSITIVE = {"water_stress_bws": 1e-9, "water_stress_2050": 1e-9, "wind_speed_100m_ms": 1e-3}


@pytest.fixture(scope="module")
def table():
    t = pd.read_parquet(OUT / "county_features.parquet")
    if "rucc_2023" not in t:
        pytest.skip("county table predates the v2 port; run python -m etl.build_features")
    return t.set_index("fips", drop=False)


@pytest.fixture(scope="module")
def quality():
    return json.loads((OUT / "county_features_quality_report.json").read_text())


@pytest.fixture(scope="module")
def manifest():
    return json.loads((OUT / "county_features.manifest.json").read_text())


# --- registration -------------------------------------------------------------

def test_v2_columns_are_stretch_not_core_and_not_scored():
    assert set(V2_CONTEXT) <= set(STRETCH)
    assert not set(V2_CONTEXT) & set(CORE)
    pillars = Path("engine/pillars.yaml").read_text()
    assert not [c for c in V2_CONTEXT if f"column: {c}\n" in pillars]


# --- unit rules -----------------------------------------------------------------

def _qcew_file(path, rows):
    cols = ["area_fips", "own_code", "industry_code", "agglvl_code", "disclosure_code",
            "annual_avg_estabs", "annual_avg_emplvl"]
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)


def test_qcew_suppressed_cells_are_null_not_zero(tmp_path):
    _qcew_file(tmp_path / "m.csv", [["01001", "5", "31-33", "74", "N", 7, 0],
                                    ["01003", "5", "31-33", "74", "", 20, 500],
                                    ["46113", "5", "31-33", "74", "", 2, 40]])
    rows = bls_qcew.county_rows(tmp_path / "m.csv", "5", "74")
    assert pd.isna(rows.emp["01001"]) and rows.suppressed["01001"]
    assert rows.estabs["01001"] == 7          # establishments survive suppression
    assert rows.emp["01003"] == 500
    assert "46102" in rows.index and "46113" not in rows.index  # Shannon -> Oglala Lakota


def test_queue_alt_excludes_standalone_storage_and_counts_hybrids_once():
    q = pd.DataFrame({"type_1": ["Solar", "Battery", "Battery", "Gas"],
                      "type_2": ["Battery", None, "Solar", None], "type_3": [None] * 4,
                      "mw_1": [100.0, 50.0, 80.0, 300.0], "mw_2": [40.0, np.nan, np.nan, np.nan],
                      "mw_3": [np.nan] * 4})
    assert lbnl_queue_alt.clean_generation_mw(q).tolist() == [100.0, 0.0, 0.0, 0.0]


def test_fractracker_mw_parsing():
    assert fractracker_context.parse_mw("10,000") == 10000.0
    assert fractracker_context.parse_mw("100-200") == 150.0
    assert np.isnan(fractracker_context.parse_mw(np.nan))
    assert np.isnan(fractracker_context.parse_mw("unknown"))


# --- built table --------------------------------------------------------------

def test_one_row_per_county_and_one_to_one_joins(table, manifest):
    assert len(table) == 3109 and table.fips.is_unique
    for name in ("bls_laus", "bls_qcew", "usda_ers", "epa_brownfields", "nri_context",
                 "aqueduct_context", "cmra_context", "fcc_context", "fractracker_context", "lbnl_queue_alt"):
        assert name in manifest["joins"], name
        assert not manifest["joins"][name]["fips_not_in_table"], name


def test_main_columns_unchanged_from_1575003(table):
    """Every column main had at 1575003 keeps its position, dtype, and values."""
    try:
        blob = subprocess.run(["git", "show", f"{BASE_COMMIT}:data/processed/county_features.parquet"],
                              capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"git history for {BASE_COMMIT} not available")
    base = pd.read_parquet(io.BytesIO(blob))
    now = table.reset_index(drop=True)
    assert list(now.columns[: len(base.columns)]) == list(base.columns)
    changed = []
    for col in base.columns:
        a, b = base[col], now[col]
        if str(a.dtype) != str(b.dtype):
            changed.append((col, "dtype"))
        elif col in LIBRARY_SENSITIVE:
            if not np.allclose(a.astype(float), b.astype(float), atol=LIBRARY_SENSITIVE[col], equal_nan=True):
                changed.append((col, "values"))
        elif not a.equals(b):
            changed.append((col, "values"))
    assert not changed, f"main columns changed: {changed}"


def test_unemployment_columns_are_percents(table):
    for col in ("unemployment_rate_pct_2024", "unemployment_rate_pct_3yr_2022_2024"):
        v = table[col].dropna()
        assert v.between(0, 100).all() and v.max() > 5, col  # a 0-1 fraction would top out near 0.2
    r = table.loc["51107"]  # Loudoun, VA: LAUS 2024 annual average
    assert r.unemployment_rate_pct_2024 == pytest.approx(2.5)
    assert r.unemployed_persons_2024 == 6409 and r.labor_force_2024 == 252275
    assert table.unemployment_rate_pct_2023.notna().sum() > 3000  # the ERS field is still there


def test_qcew_semantics_in_table(table):
    for y in (2015, 2019, 2024, 2025):
        assert not (table[f"mfg_emp_suppressed_{y}"].fillna(False) & table[f"mfg_emp_{y}"].notna()).any()
    assert not (table.mfg_emp_pct_change_2015_2024.notna() & ~(table.mfg_emp_2015 > 0)).any()
    boone = table.loc["17007"]  # documented decline: Belvidere assembly plant idled in 2023
    assert (boone.mfg_emp_2015, boone.mfg_emp_2024) == (7761, 2070)
    assert boone.mfg_emp_pct_change_2015_2024 == pytest.approx(-0.7333, abs=1e-4)
    assert table.mfg_emp_share_2024.dropna().between(0, 1).all()


def test_rurality_covers_every_county(table):
    assert table.rucc_2023.notna().all()
    assert table.rucc_2023.between(1, 9).all()
    assert (table.metro_2023 == (table.rucc_2023 <= 3)).all()
    ct = table[table.fips.str.startswith("091")]
    assert ct.ers_high_manufacturing_2025.isna().all()  # old-county codes aren't moved to regions


def test_brownfield_sites_unique_and_reconcile_to_counties(table, manifest):
    if not (OUT / "brownfield_sites.parquet").exists():  # generated by the ETL, never committed
        pytest.skip("brownfield_sites.parquet absent; run python -m etl.build_features to generate it")
    sites = pd.read_parquet(OUT / "brownfield_sites.parquet")
    assert sites.property_id.is_unique and sites.fips.notna().all()
    assert str(OUT / "brownfield_sites.parquet") in manifest["artifacts"]
    counts = sites.groupby("fips").size().reindex(table.index, fill_value=0)
    assert (counts.values == table.bf_site_count.values).all()
    acres = sites.groupby("fips").acreage_reported.sum(min_count=1).reindex(table.index)
    has_sites = table.bf_site_count > 0
    assert np.allclose(acres[has_sites].fillna(-1), table.bf_known_acres[has_sites].fillna(-1))


def test_missing_acreage_is_null_and_zero_only_without_sites(table):
    no_sites = table.bf_site_count == 0
    assert (table.bf_known_acres[no_sites] == 0).all()
    unknown = table.bf_known_acres.isna()
    assert (table.bf_site_count[unknown] > 0).all()
    assert (table.bf_acreage_reporting_share[unknown] == 0).all()


def test_municipal_restrictions_do_not_set_county_flag(table):
    muni_only = (table.moratorium_municipal_count > 0) & ~table.moratorium_active
    assert muni_only.any()
    assert table.moratorium_municipal_count.sum() > 0


def test_reported_mw_semantics(table):
    for pre in ("dc_existing", "dc_proposed"):
        none = table[f"{pre}_count"] == 0
        assert (table[f"{pre}_mw_reported"][none] == 0).all()
        unknown = table[f"{pre}_mw_reported"].isna()
        assert (table[f"{pre}_count"][unknown] > 0).all()


def test_nri_not_applicable_handling(table):
    for h in ("hurricane", "coastal_flood"):
        na = table[f"nri_{h}_not_applicable"].fillna(False)
        assert na.any()
        assert (table.loc[na, f"nri_{h}_score"] == 0).all()
        assert (table.loc[na, f"nri_{h}_annual_freq"] == 0).all()
    assert bool(table.loc["19161", "nri_coastal_flood_not_applicable"])  # Sac County, IA: inland
    freq = [c for c in table.columns if c.startswith("nri_") and c.endswith("_annual_freq")]
    assert len(freq) == 8 and all((table[c].dropna() >= 0).all() for c in freq)
    assert table.nri_wildfire_annual_freq.max() <= 1  # an annual probability
    assert set(table.nri_risk_rating.dropna()) <= {"Very Low", "Relatively Low", "Relatively Moderate",
                                                    "Relatively High", "Very High", "Insufficient Data"}


def test_provenance_and_quality_report(manifest, quality):
    adapters = {s.get("adapter") for s in manifest["sources"]}
    assert {"bls_laus", "bls_qcew", "usda_ers", "epa_brownfields", "lbnl_queue_alt"} <= adapters
    for s in manifest["sources"]:
        if s.get("adapter") in {"bls_laus", "bls_qcew", "usda_ers", "epa_brownfields"}:
            for key in ("url", "version", "fetched_at", "observation_period", "license"):
                assert s.get(key), (s["adapter"], key)
    assert quality["rows"] == 3109
    assert not quality["checks_failed"], quality["checks_failed"]
    assert set(V2_CONTEXT) <= set(quality["columns"])
    # The BLS contact address comes from BLS_CONTACT_EMAIL and must never reach an output file.
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", json.dumps(manifest) + json.dumps(quality))
