"""Naive v0 ranking: gates, percentile pillar scores, weighted composite, floor rule.

Pure functions, no network. Semantics follow docs/conditions.md with the null
rule decided for v0: a pillar mean ignores null columns, and a pillar with no
available columns is dropped and the remaining weights are renormalized.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# Gate name -> (column, test). The test returns True where the county fails.
# Each test sees only non-null values; nulls are logged as unknown.
SIMPLE_GATES = {
    "max_grid_co2_lb_mwh": ("grid_co2_lb_mwh", lambda v, t: v > t),
    "min_renewable_share": ("grid_renewable_share", lambda v, t: v < t),
    "max_queue_median_age_years": ("queue_median_age_years", lambda v, t: v > t),
    "min_fiber_share_locations": ("fiber_share_locations", lambda v, t: v < t),
    "max_permitting_risk": ("permitting_discretionary_risk", lambda v, t: v > t),
    "min_population": ("population", lambda v, t: v < t),
}
FLAG_GATES = {
    "exclude_moratorium_active": "moratorium_active",
    "exclude_moratorium_state_active": "moratorium_state_active",
    "exclude_air_nonattainment": "air_nonattainment_count",
}


def load_yaml(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


def load_features(path):
    """Read the county table and drop columns the manifest lists as missing."""
    path = Path(path)
    df = pd.read_parquet(path)
    df["fips"] = df["fips"].astype(str).str.zfill(5)
    manifest = path.with_name(path.stem + ".manifest.json")
    warnings = []
    if manifest.exists():
        missing = json.loads(manifest.read_text()).get("columns_missing", [])
        present = [c for c in missing if c in df.columns]
        df = df.drop(columns=present)
        if missing:
            warnings.append(f"manifest lists {len(missing)} missing columns: {', '.join(missing)}")
    else:
        warnings.append(f"no manifest at {manifest}; using columns as found")
    return df, warnings


def percentile(values, direction="higher_better", transform=None):
    """National percentile rank, 0-100, direction-adjusted so 100 is best. Nulls stay null."""
    v = pd.to_numeric(values, errors="coerce").astype(float)
    if transform == "log1p":
        v = np.log1p(v)  # monotonic, so it never changes a rank; kept so the mapping reads as specified
    elif transform:
        raise ValueError(f"unsupported transform: {transform}")
    if direction == "lower_better":
        v = -v
    elif direction != "higher_better":
        raise ValueError(f"unknown direction: {direction}")
    return v.rank(pct=True, method="average") * 100


def apply_gates(df, conditions):
    """Return a per-county gate log: failed_gates and unknown_gates, semicolon lists."""
    gates = conditions.get("gates") or {}
    failed = pd.Series([[] for _ in range(len(df))], index=df.index)
    unknown = pd.Series([[] for _ in range(len(df))], index=df.index)

    def record(name, column, fails):
        # fails is a boolean Series with NaN where the input is null
        col = df[column] if column in df.columns else pd.Series(np.nan, index=df.index)
        is_null = col.isna()
        for i in df.index[is_null]:
            unknown[i].append(name)
        for i in df.index[~is_null & fails.fillna(False).astype(bool)]:
            failed[i].append(name)

    def values(column):
        if column not in df.columns:
            return pd.Series(np.nan, index=df.index)
        return df[column]

    include = gates.get("states_include") or []
    exclude = gates.get("states_exclude") or []
    if include:
        record("states_include", "state", ~values("state").isin(include))
    if exclude:
        record("states_exclude", "state", values("state").isin(exclude))

    for name, (column, test) in SIMPLE_GATES.items():
        t = gates.get(name)
        if t is not None:
            v = pd.to_numeric(values(column), errors="coerce")
            record(name, column, test(v, t))

    for name, column in FLAG_GATES.items():
        if gates.get(name):
            v = pd.to_numeric(values(column).astype("float"), errors="coerce")
            record(name, column, v > 0)

    cooling = (conditions.get("facility") or {}).get("cooling", "dry")
    t = gates.get("max_water_stress_if_evaporative")
    if t is not None and cooling in ("evaporative", "hybrid"):
        v = pd.to_numeric(values("water_stress_bws"), errors="coerce")
        record("max_water_stress_if_evaporative", "water_stress_bws", v > t)

    for column, pmax in (gates.get("hazard_percentile_max") or {}).items():
        if pmax is not None:
            # raw national percentile of the hazard score, higher means more hazard
            p = percentile(values(column), "higher_better")
            record(f"hazard_percentile_max.{column}", column, p > pmax)

    return pd.DataFrame({
        "failed_gates": failed.map(";".join),
        "unknown_gates": unknown.map(";".join),
    }, index=df.index)


def resolve_columns(df, pillars, horizon=2026, scenario="rcp85"):
    """Pick the column each metric scores on for this horizon.

    Returns ({pillar: [(column, metric)]}, warnings, swapped). A metric whose
    column is absent is skipped. Under horizon 2050, a metric with a
    horizon_2050 key scores on that column, or falls back to today's column
    with a warning when the 2050 column is absent.
    """
    warnings, swapped, resolved = [], [], {}
    for pillar, metrics in pillars.items():
        cols = []
        for m in metrics:
            col = m["column"]
            future = m.get("horizon_2050")
            if horizon == 2050 and future:
                future = future.format(scenario=scenario)
                if future in df.columns:
                    swapped.append(future)
                    col = future
                elif col in df.columns:
                    warnings.append(f"{pillar}: {future} missing, scoring {col} for 2050")
            if col not in df.columns:
                warnings.append(f"{pillar}: column {col} missing, skipped")
                continue
            cols.append((col, m))
        resolved[pillar] = cols
    return resolved, warnings, swapped


def score(df, pillars, weights, horizon=2026, scenario="rcp85"):
    """Pillar scores and the weighted composite for every county.

    Returns (scores, pillar_cols, warnings, swapped).
    """
    resolved, warnings, swapped = resolve_columns(df, pillars, horizon, scenario)
    out = pd.DataFrame(index=df.index)
    used_columns = []
    for pillar, cols in resolved.items():
        if not cols:
            warnings.append(f"{pillar}: no available columns, pillar dropped")
            continue
        pcts = [percentile(df[c], m.get("direction", "higher_better"), m.get("transform")) for c, m in cols]
        used_columns += [c for c, _ in cols]
        out[f"pillar_{pillar}"] = pd.concat(pcts, axis=1).mean(axis=1, skipna=True)

    pillar_cols = [c for c in out.columns if c.startswith("pillar_")]
    w = pillar_weights(weights, pillar_cols)
    dropped = [p for p in weights if f"pillar_{p}" not in pillar_cols and weights[p]]
    if dropped or not np.isclose(sum(float(v or 0) for v in weights.values()), 1.0):
        warnings.append(f"weights renormalized over {len(pillar_cols)} pillars (dropped: {', '.join(dropped) or 'none'})")
    out["composite"] = composite(out[pillar_cols], w)
    out["coverage"] = df[used_columns].notna().mean(axis=1) if used_columns else 0.0
    return out, pillar_cols, warnings, swapped


def pillar_weights(weights, pillar_cols):
    """Weights for the pillars that have data, renormalized to sum to 1."""
    w = pd.Series({c: float(weights.get(c.removeprefix("pillar_"), 0) or 0) for c in pillar_cols})
    if w.sum() <= 0:
        raise ValueError("no pillar with positive weight has any data")
    return w / w.sum()


def composite(pillar_scores, w):
    """Weighted sum of pillars. A county with a null pillar renormalizes over the pillars it has."""
    avail = pillar_scores.notna().mul(w, axis=1).sum(axis=1)
    return pillar_scores.fillna(0).mul(w, axis=1).sum(axis=1) / avail.replace(0, np.nan)


def floor_ok(scores, pillar_cols, floor):
    """True where every non-null pillar is at or above the floor, as a national percentile of the pillar score."""
    if not floor:
        return pd.Series(True, index=scores.index)
    pp = scores[pillar_cols].rank(pct=True, method="average") * 100
    return ~(pp < floor).any(axis=1)


def rank(df, conditions, pillars):
    """Run the engine. Returns (ranked, excluded, report)."""
    report = {"warnings": []}
    horizon = conditions.get("horizon", 2026)
    scenario = conditions.get("scenario", "rcp85")
    weights = conditions.get("weights") or {}

    log = apply_gates(df, conditions)
    scores, pillar_cols, warns, swapped = score(df, pillars, weights, horizon, scenario)
    report["warnings"] += warns

    # horizon_delta: composite under 2050 minus under 2026. Null when no 2050 column exists.
    other, _, _, other_swapped = score(df, pillars, weights, 2026 if horizon == 2050 else 2050, scenario)
    s2026, s2050 = (other, scores) if horizon == 2050 else (scores, other)
    scores["horizon_delta"] = s2050["composite"] - s2026["composite"] if (swapped or other_swapped) else np.nan
    scores["floor_ok"] = floor_ok(scores, pillar_cols, conditions.get("pillar_floor_percentile", 0))

    ids = [c for c in ("fips", "county_name", "state") if c in df.columns]
    full = pd.concat([df[ids], scores, log], axis=1)
    passed = full["failed_gates"] == ""

    ranked = full[passed].sort_values(["floor_ok", "composite"], ascending=[False, False])
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    excluded = full.loc[~passed, ids + ["failed_gates", "unknown_gates"]]

    gate_counts = {}
    for gates in full["failed_gates"]:
        for g in filter(None, gates.split(";")):
            gate_counts[g] = gate_counts.get(g, 0) + 1
    report.update(
        counties=len(full),
        passed=int(passed.sum()),
        excluded=int((~passed).sum()),
        gate_failures=gate_counts,
        floor_ok=int(ranked["floor_ok"].sum()),
        pillars=[c.removeprefix("pillar_") for c in pillar_cols],
    )
    return ranked.reset_index(drop=True), excluded.reset_index(drop=True), report
