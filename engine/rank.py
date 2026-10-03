"""Naive v0 ranking: gates, percentile pillar scores, weighted composite, floor rule.

Pure functions, no network. Semantics follow docs/conditions.md with the null
rule decided for v0: a pillar mean ignores null columns, and a pillar with no
available columns is dropped and the remaining weights are renormalized.
"""
import json
from pathlib import Path
from typing import NamedTuple

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

    # The first gate whose threshold comes from the facility: nearby plant capacity must
    # be at least `multiple` times the facility's MW.
    mult = gates.get("min_nearby_capacity_multiple")
    if mult is not None:
        mw = (conditions.get("facility") or {}).get("mw")
        if mw is None:
            raise ValueError("gates.min_nearby_capacity_multiple needs facility.mw")
        v = pd.to_numeric(values("plant_capacity_mw_100km"), errors="coerce")
        record("min_nearby_capacity_multiple", "plant_capacity_mw_100km", v < mult * mw)

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


class Scores(NamedTuple):
    scores: pd.DataFrame      # pillar_* columns, composite, coverage
    pillar_cols: list
    warnings: list
    swapped: list             # 2050 columns that replaced today's columns
    pcts: pd.DataFrame        # per-column percentile, one column per scored data column
    columns: dict             # pillar -> list of scored data columns
    weights: pd.Series        # renormalized, indexed by pillar_* column


def score(df, pillars, weights, horizon=2026, scenario="rcp85"):
    """Pillar scores and the weighted composite for every county."""
    resolved, warnings, swapped = resolve_columns(df, pillars, horizon, scenario)
    out = pd.DataFrame(index=df.index)
    pcts, columns = {}, {}
    for pillar, cols in resolved.items():
        if not cols:
            warnings.append(f"{pillar}: no available columns, pillar dropped")
            continue
        for c, m in cols:
            pcts[c] = percentile(df[c], m.get("direction", "higher_better"), m.get("transform"))
        columns[pillar] = [c for c, _ in cols]
        out[f"pillar_{pillar}"] = pd.DataFrame({c: pcts[c] for c in columns[pillar]}).mean(axis=1, skipna=True)

    pillar_cols = [c for c in out.columns if c.startswith("pillar_")]
    w = pillar_weights(weights, pillar_cols)
    dropped = [p for p in weights if f"pillar_{p}" not in pillar_cols and weights[p]]
    if dropped or not np.isclose(sum(float(v or 0) for v in weights.values()), 1.0):
        warnings.append(f"weights renormalized over {len(pillar_cols)} pillars (dropped: {', '.join(dropped) or 'none'})")
    out["composite"] = composite(out[pillar_cols], w)
    pcts = pd.DataFrame(pcts, index=df.index)
    out["coverage"] = pcts.notna().mean(axis=1) if len(pcts.columns) else 0.0
    return Scores(out, pillar_cols, warnings, swapped, pcts, columns, w)


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


def order(scores, floor_mask, passed):
    """Rank among gate-passed counties: floor-passing first, then composite. Null outside the gate."""
    keyed = pd.DataFrame({"floor": floor_mask, "c": scores["composite"]})[passed]
    idx = keyed.sort_values(["floor", "c"], ascending=[False, False]).index
    return pd.Series(np.arange(1, len(idx) + 1), index=idx).reindex(scores.index)


def top_reasons(sc, n=3):
    """The n columns adding most to each county's composite, as a semicolon list.

    A column's contribution is its pillar weight times its percentile above
    the median (50), divided by the number of non-null columns in that pillar
    for the county. Measuring from the median keeps a column that is tied for
    most counties, or alone in its pillar, from topping every county's list.
    """
    parts = []
    for pillar, cols in sc.columns.items():
        p = sc.pcts[cols] - 50
        parts.append(p.div(p.notna().sum(axis=1), axis=0) * sc.weights[f"pillar_{pillar}"])
    contrib = pd.concat(parts, axis=1)
    return contrib.apply(lambda r: ";".join(r.dropna().nlargest(n).index), axis=1)


def robustness(pillar_scores, w, floor_mask, conditions):
    """Share of Dirichlet weight draws in which each county lands in the top N.

    Draws use alpha = concentration * weights * number of pillars, so the
    mean draw equals the stated weights. Pillar scores and floor membership
    don't depend on weights, so only the composite is recomputed per draw.
    Zero-weight pillars stay at zero.
    """
    cfg = conditions.get("robustness") or {}
    samples, top_n = int(cfg.get("samples", 2000)), int(cfg.get("top_n", 10))
    if samples <= 0 or len(pillar_scores) == 0:
        return pd.Series(np.nan, index=pillar_scores.index)
    rng = np.random.default_rng(cfg.get("seed", 0))
    pos = w > 0
    draws = np.zeros((samples, len(w)))
    draws[:, pos.values] = rng.dirichlet(cfg.get("concentration", 20) * w[pos].values * pos.sum(), samples)

    vals = pillar_scores[w.index].to_numpy()
    num = np.nan_to_num(vals) @ draws.T                          # counties x samples
    den = (~np.isnan(vals)).astype(float) @ draws.T
    comp = np.divide(num, den, out=np.full_like(num, -np.inf), where=den > 0)
    comp = np.where(np.isnan(comp), -np.inf, comp) + floor_mask.to_numpy()[:, None] * 1000.0  # floor group first
    k = min(top_n, len(comp))
    top = np.argpartition(-comp, k - 1, axis=0)[:k]               # k x samples
    hits = np.bincount(top.ravel(), minlength=len(comp))
    return pd.Series(hits / samples, index=pillar_scores.index)


def rank(df, conditions, pillars):
    """Run the engine. Returns (ranked, excluded, report)."""
    report = {"warnings": []}
    horizon = conditions.get("horizon", 2026)
    scenario = conditions.get("scenario", "rcp85")
    weights = conditions.get("weights") or {}
    floor = conditions.get("pillar_floor_percentile", 0)

    log = apply_gates(df, conditions)
    passed = log["failed_gates"] == ""
    sc = score(df, pillars, weights, horizon, scenario)
    report["warnings"] += sc.warnings
    scores = sc.scores
    scores["floor_ok"] = floor_ok(scores, sc.pillar_cols, floor)

    # Horizon comparison. horizon_delta is a difference of national
    # percentiles, so it shows relative change only; rank_delta_2050 is the
    # rank movement a user can read. Both null when no 2050 column exists.
    other = score(df, pillars, weights, 2026 if horizon == 2050 else 2050, scenario)
    s2026, s2050 = (other, sc) if horizon == 2050 else (sc, other)
    if s2050.swapped:
        scores["horizon_delta"] = s2050.scores["composite"] - s2026.scores["composite"]
        r2026, r2050 = (order(s.scores, floor_ok(s.scores, s.pillar_cols, floor), passed) for s in (s2026, s2050))
        scores["rank_delta_2050"] = r2050 - r2026
    else:
        scores["horizon_delta"] = scores["rank_delta_2050"] = np.nan

    scores["top_reasons"] = top_reasons(sc)
    p = passed.to_numpy()
    scores["robustness"] = robustness(scores.loc[p, sc.pillar_cols], sc.weights,
                                      scores.loc[p, "floor_ok"], conditions).reindex(scores.index)

    ids = [c for c in ("fips", "county_name", "state") if c in df.columns]
    full = pd.concat([df[ids], scores, log], axis=1)
    full["rank"] = order(scores, scores["floor_ok"], passed)
    ranked = full[passed].sort_values("rank")
    ranked = ranked[["rank"] + [c for c in ranked.columns if c != "rank"]]
    ranked["rank"] = ranked["rank"].astype(int)
    excluded = full.loc[~passed, ids + ["failed_gates", "unknown_gates"]]

    gate_counts = {}
    for gates in full["failed_gates"]:
        for g in filter(None, gates.split(";")):
            gate_counts[g] = gate_counts.get(g, 0) + 1
    # A percentile cap on a zero-heavy hazard can exclude every exposed county; show the exposed count.
    exposed = {f"hazard_percentile_max.{c}": int((pd.to_numeric(df[c], errors="coerce") > 0).sum())
               for c, v in ((conditions.get("gates") or {}).get("hazard_percentile_max") or {}).items()
               if v is not None and c in df.columns}
    report.update(
        counties=len(full),
        passed=int(passed.sum()),
        excluded=int((~passed).sum()),
        gate_failures=gate_counts,
        hazard_gate_nonzero_counties=exposed,
        floor_ok=int(ranked["floor_ok"].sum()),
        pillars=[c.removeprefix("pillar_") for c in sc.pillar_cols],
        weights_used={c.removeprefix("pillar_"): round(float(v), 4) for c, v in sc.weights.items()},
    )
    return ranked.reset_index(drop=True), excluded.reset_index(drop=True), report
