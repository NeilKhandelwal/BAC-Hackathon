"""Quality report for the county table: validation checks, per-source coverage, column profiles.

Written to data/processed/county_features_quality_report.json by etl/build_features.py. It reads
the finished table and never changes it.
"""
import json
import re

import pandas as pd

from etl.schema import CORE, STRETCH, V2_CONTEXT

EXPECTED_ROWS = 3109
EXPECTED_STATES = 49
CT_REGIONS = [f"091{i}0" for i in range(1, 10)]
CT_OLD = [f"090{i:02d}" for i in range(1, 16, 2)]
OUT_OF_SCOPE = ("02", "15", "60", "66", "69", "72", "78")

# Expected ranges for the v2 context columns, by name pattern.
RANGES = [
    (r"^mfg_emp_pct_change", (-1, None)),          # signed fraction, before the percent rule
    (r"_pct(_\d|_3yr|$)", (0, 100)),
    (r"(_share|_coverage)(_|$)", (0, 1)),
    (r"^nri_.*_score$", (0, 100)),
    (r"_cat$", (-1, 4)),
    (r"^rucc_2023$", (1, 9)),
    (r"^mfg_emp_change|^queue_.*_change", (None, None)),
    (r"(_count|_mw|_mw_|_projects|_emp|_estabs|_acres|_persons|labor_force|_freq|_total|^hdd|^days_above|"
     r"_raw_median|jobs_lost|_online_5y)", (0, None)),
]


def _check(name, passed, detail=""):
    return {"name": name, "passed": bool(passed), "detail": detail}


def _range(column):
    for pattern, rng in RANGES:
        if re.search(pattern, column):
            return rng
    return None


def range_violations(table, columns):
    out = {}
    for c in columns:
        if c not in table or pd.api.types.is_bool_dtype(table[c]) or not pd.api.types.is_numeric_dtype(table[c]):
            continue
        rng = _range(c)
        if rng is None or rng == (None, None):
            continue
        v = pd.to_numeric(table[c], errors="coerce").dropna()
        lo, hi = rng
        bad = pd.Series(False, index=v.index)
        if lo is not None:
            bad |= v < lo - 1e-9
        if hi is not None:
            bad |= v > hi + 1e-9
        if bad.any():
            out[c] = {"expected": [lo, hi], "violations": int(bad.sum()),
                      "examples": table.loc[bad[bad].index, "fips"].head(5).tolist()}
    return out


def checks(table, manifest):
    t = table.set_index("fips", drop=False)
    v2 = [c for c in V2_CONTEXT if c in t]
    out = [
        _check("row_count", len(t) == EXPECTED_ROWS, f"{len(t)} rows"),
        _check("fips_unique", t.fips.is_unique),
        _check("fips_5_char_string", t.fips.astype(str).str.fullmatch(r"\d{5}").all()),
        _check("state_count", t.state.nunique() == EXPECTED_STATES, f"{t.state.nunique()} states"),
        _check("no_ak_hi_territories", not t.fips.str.startswith(OUT_OF_SCOPE).any()),
        _check("ct_planning_regions_only", t.fips.isin(CT_REGIONS).sum() == 9 and not t.fips.isin(CT_OLD).any()),
        _check("no_failed_adapters", not manifest.get("errors"), manifest.get("errors") or "none"),
        _check("v2_context_columns_present", len(v2) == len(V2_CONTEXT),
               sorted(set(V2_CONTEXT) - set(v2)) or "all present"),
        _check("v2_context_columns_not_scored_core", not set(V2_CONTEXT) & set(CORE)),
    ]
    if {"mfg_emp_2024", "mfg_emp_suppressed_2024"} <= set(t):
        bad = sum(int((t[f"mfg_emp_suppressed_{y}"].fillna(False) & t[f"mfg_emp_{y}"].notna()).sum())
                  for y in (2015, 2019, 2024, 2025))
        out.append(_check("qcew_suppressed_is_null_not_zero", bad == 0, f"{bad} violations"))
        bad = int((t.mfg_emp_pct_change_2015_2024.notna() & ~(t.mfg_emp_2015 > 0)).sum())
        out.append(_check("qcew_pct_change_null_without_positive_base", bad == 0, f"{bad} violations"))
        diff = (t.mfg_emp_2024 - t.mfg_emp_2015 - t.mfg_emp_change_2015_2024).abs().max()
        out.append(_check("qcew_change_equals_difference", pd.isna(diff) or diff < 1e-6, f"max abs diff {diff}"))
    if {"unemployment_rate_pct_2024", "unemployed_persons_2024", "labor_force_2024"} <= set(t):
        gap = (100 * t.unemployed_persons_2024 / t.labor_force_2024 - t.unemployment_rate_pct_2024).abs().max()
        out.append(_check("laus_rate_is_percent_and_matches_counts", gap < 0.1, f"max abs gap {gap:.3f} points"))
    if "rucc_2023" in t:
        out.append(_check("rucc_covers_every_county", t.rucc_2023.notna().all(),
                          f"{int(t.rucc_2023.isna().sum())} null"))
    if {"bf_site_count", "bf_known_acres"} <= set(t):
        zero_sites_not_zero = int(((t.bf_site_count == 0) & (t.bf_known_acres != 0)).sum())
        null_without_sites = int((t.bf_known_acres.isna() & (t.bf_site_count == 0)).sum())
        out.append(_check("brownfield_acres_zero_only_without_sites",
                          zero_sites_not_zero == 0 and null_without_sites == 0,
                          f"{zero_sites_not_zero} zero-site counties with acres, {null_without_sites} null without sites"))
    for pre in ("dc_existing", "dc_proposed"):
        if f"{pre}_mw_reported" in t:
            bad = int(((t[f"{pre}_count"] == 0) & (t[f"{pre}_mw_reported"] != 0)).sum())
            out.append(_check(f"{pre}_mw_reported_zero_without_facilities", bad == 0, f"{bad} violations"))
    if "moratorium_municipal_count" in t:
        muni_only = int(((t.moratorium_municipal_count > 0) & ~t.moratorium_active.fillna(False)).sum())
        out.append(_check("municipal_rows_do_not_set_county_flag", True,
                          f"{muni_only} counties have municipal restrictions without a county moratorium flag"))
    for h in ("hurricane", "coastal_flood"):
        col = f"nri_{h}_not_applicable"
        if col in t:
            na = t[col].fillna(False)
            bad = int((na & ((t[f"nri_{h}_score"] != 0) | (t[f"nri_{h}_annual_freq"] != 0))).sum())
            out.append(_check(f"nri_{h}_not_applicable_is_zero", bad == 0, f"{bad} violations"))
    viol = range_violations(t, v2)
    out.append(_check("v2_context_ranges", not viol, viol or "all v2 context columns within expected ranges"))
    return out


def _profile(s):
    p = {"dtype": str(s.dtype), "nulls": int(s.isna().sum())}
    if pd.api.types.is_bool_dtype(s):
        p["true"] = int(s.fillna(False).sum())
    elif pd.api.types.is_numeric_dtype(s):
        v = pd.to_numeric(s, errors="coerce").dropna()
        if len(v):
            p.update(min=float(v.min()), median=float(v.median()), max=float(v.max()), zeros=int((v == 0).sum()))
    return p


def report(table, manifest):
    c = checks(table, manifest)
    return {
        "built_at": manifest.get("built_at"),
        "rows": len(table),
        "checks": c,
        "checks_failed": [x["name"] for x in c if not x["passed"]],
        "adapter_errors": manifest.get("errors", {}),
        "joins": manifest.get("joins", {}),
        "columns": {col: _profile(table[col]) for col in table.columns},
        "core_columns": len([x for x in CORE if x in table]),
        "stretch_columns_present": len([x for x in STRETCH if x in table]),
        "crosswalk_limitations": [
            "Connecticut: QCEW 2015/2019 and ERS economic typology codes exist only for the old "
            "counties, so CT manufacturing change columns and those flags are null.",
            "Municipal moratoria in incorporated places map to the county holding the place's 2024 "
            "Census internal point.",
        ],
    }


def write_report(table, manifest, path):
    path.write_text(json.dumps(report(table, manifest), indent=2, default=str) + "\n")
