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
    "min_electricity_generation_twh": ("electricity_generation_twh", lambda v, t: v < t),
}
FLAG_GATES = {
    "exclude_moratorium_active": "moratorium_active",
    "exclude_moratorium_state_active": "moratorium_state_active",
    "exclude_air_nonattainment": "air_nonattainment_count",
}
# Gates handled by their own code in apply_gates, with the column each reads.
SPECIAL_GATES = {
    "states_include": "state",
    "states_exclude": "state",
    "min_nearby_capacity_multiple": "plant_capacity_mw_100km",
    "max_water_stress_if_evaporative": "water_stress_bws",
    "hazard_percentile_max": None,
}
HORIZONS = (2026, 2050)
# Row identity: key, display name, and the group column the states_* gates act on.
DEFAULT_UNIT = {"key": "fips", "name": "county_name", "group": "state"}
# Unscored columns carried into ranked output so a user sees them next to the score.
FLAG_COLUMNS = ("moratorium_state_active",)


def parse_horizon(value):
    """Return 2026 or 2050 from an int or numeric string; raise on anything else."""
    try:
        h = int(str(value).strip())
    except ValueError:
        h = None
    if h not in HORIZONS:
        raise ValueError(f"horizon must be 2026 or 2050, got {value!r}")
    return h


def floor_exempt(conditions, pillars):
    """The pillar_floor_exempt list, checked against the pillar names in pillars.yaml."""
    exempt = conditions.get("pillar_floor_exempt") or []
    if not isinstance(exempt, (list, tuple)):
        raise ValueError(f"pillar_floor_exempt must be a list of pillar names, got {exempt!r}")
    unknown = [p for p in exempt if p not in pillars]
    if unknown:
        raise ValueError(f"pillar_floor_exempt names unknown pillars: {', '.join(map(str, unknown))}")
    return list(exempt)


def check_gates(df, conditions):
    """Warnings for gate settings that would silently do nothing or mark every county unknown."""
    gates = conditions.get("gates") or {}
    warnings = []
    known = set(SIMPLE_GATES) | set(FLAG_GATES) | set(SPECIAL_GATES)
    for key in gates:
        if key not in known:
            warnings.append(f"gates.{key} is not a known gate and was ignored")
    cooling = (conditions.get("facility") or {}).get("cooling", "dry")
    active = {name: col for name, (col, _) in SIMPLE_GATES.items() if gates.get(name) is not None}
    active.update({name: col for name, col in FLAG_GATES.items() if gates.get(name)})
    if gates.get("min_nearby_capacity_multiple") is not None:
        active["min_nearby_capacity_multiple"] = "plant_capacity_mw_100km"
    if gates.get("max_water_stress_if_evaporative") is not None and cooling in ("evaporative", "hybrid"):
        active["max_water_stress_if_evaporative"] = "water_stress_bws"
    for column, pmax in (gates.get("hazard_percentile_max") or {}).items():
        if pmax is not None:
            active[f"hazard_percentile_max.{column}"] = column
    for name, column in active.items():
        if column not in df.columns:
            warnings.append(f"gate {name}: column {column} is not in the table, so every county is unknown")
    return warnings


def load_yaml(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


def unit(conditions):
    """The conditions file's unit block over the county defaults."""
    return {**DEFAULT_UNIT, **((conditions or {}).get("unit") or {})}


def load_features(path, key="fips"):
    """Read the feature table and drop columns the manifest lists as missing. Zero-pads only a fips key."""
    path = Path(path)
    df = pd.read_parquet(path)
    df[key] = df[key].astype(str)
    if key == "fips":
        df[key] = df[key].str.zfill(5)
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
    group = unit(conditions)["group"]
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
    for name, v in (("states_include", include), ("states_exclude", exclude)):
        if not isinstance(v, (list, tuple)):
            raise ValueError(f"gates.{name} must be a list of state abbreviations, got {v!r}")
    if include:
        record("states_include", group, ~values(group).isin(include))
    if exclude:
        record("states_exclude", group, values(group).isin(exclude))

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
    horizon = parse_horizon(horizon)
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
    # Coverage counts every column in pillars.yaml, so absent columns lower it.
    n_total = sum(len(ms) for ms in pillars.values())
    out["coverage"] = pcts.notna().sum(axis=1) / n_total if n_total else 0.0
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


def pillar_percentiles(scores, pillar_cols):
    """National percentile of each pillar score."""
    return scores[pillar_cols].rank(pct=True, method="average") * 100


def floor_ok(scores, pillar_cols, floor, w=None, exempt=()):
    """True where every non-null pillar with positive weight is at or above the floor.

    The floor compares the national percentile of the pillar score. A pillar
    the user weights at zero, or lists in exempt, doesn't count.
    """
    cols = [c for c in pillar_cols if (w is None or w.get(c, 0) > 0) and c.removeprefix("pillar_") not in exempt]
    if not floor or not cols:
        return pd.Series(True, index=scores.index)
    return ~(pillar_percentiles(scores, cols) < floor).any(axis=1)


def order(scores, floor_mask, passed):
    """Rank among gate-passed counties: floor-passing first, then composite. Null outside the gate."""
    keyed = pd.DataFrame({"floor": floor_mask, "c": scores["composite"]})[passed]
    idx = keyed.sort_values(["floor", "c"], ascending=[False, False]).index
    return pd.Series(np.arange(1, len(idx) + 1), index=idx).reindex(scores.index)


def top_reasons(sc, rows, n=3):
    """The n columns adding most to the composite of each county in rows, as a semicolon list.

    Only columns above the median count, so the list can be shorter than n.

    A column's contribution is its pillar weight times its percentile above
    the median (50), divided by the number of non-null columns in that pillar
    for the county. Measuring from the median keeps a column that is tied for
    most counties, or alone in its pillar, from topping every county's list.
    """
    parts = []
    for pillar, cols in sc.columns.items():
        p = sc.pcts.loc[rows, cols] - 50
        parts.append(p.div(p.notna().sum(axis=1), axis=0) * sc.weights[f"pillar_{pillar}"])
    contrib = pd.concat(parts, axis=1)
    a = contrib.to_numpy()
    a = np.where(a > 0, a, -np.inf)  # above-median only; NaN compares False
    k = min(n, a.shape[1])
    idx = np.argsort(-a, axis=1, kind="stable")[:, :k]
    keep = np.take_along_axis(a, idx, axis=1) > -np.inf
    names = contrib.columns.to_numpy()
    return pd.Series([";".join(names[i][m]) for i, m in zip(idx, keep)], index=contrib.index, dtype=object)


def robustness(pillar_scores, w, floor_mask, conditions):
    """Share of Dirichlet weight draws in which each county lands in the top N.

    Draws use alpha = concentration * weights * number of pillars, so the
    mean draw equals the stated weights. Pillar scores and floor membership
    don't depend on weights, so only the composite is recomputed per draw.
    Zero-weight pillars stay at zero. Only floor-passing counties with a
    composite can be hits. When that field has top_n counties or fewer,
    every one of them would score 1.0, so robustness is null with a warning.
    Returns (robustness, warnings).
    """
    cfg = conditions.get("robustness") or {}
    samples, top_n = int(cfg.get("samples", 2000)), int(cfg.get("top_n", 10))
    null = pd.Series(np.nan, index=pillar_scores.index)
    if samples <= 0 or len(pillar_scores) == 0:
        return null, []
    eligible = floor_mask.to_numpy(dtype=bool) & pillar_scores[w.index[w > 0]].notna().any(axis=1).to_numpy()
    if eligible.sum() <= top_n:
        return null, [f"robustness not computed: {int(eligible.sum())} counties pass the gates and the floor, "
                      f"not more than top_n ({top_n})"]
    rng = np.random.default_rng(cfg.get("seed", 0))
    pos = w > 0
    draws = np.zeros((samples, len(w)))
    draws[:, pos.values] = rng.dirichlet(cfg.get("concentration", 20) * w[pos].values * pos.sum(), samples)

    vals = pillar_scores[w.index].to_numpy()
    num = np.nan_to_num(vals) @ draws.T                          # counties x samples
    den = (~np.isnan(vals)).astype(float) @ draws.T
    comp = np.divide(num, den, out=np.full_like(num, -np.inf), where=den > 0)
    comp[~eligible] = -np.inf  # floor-failing and null-composite counties never count as hits
    comp = np.where(np.isnan(comp), -np.inf, comp)
    top = np.argpartition(-comp, top_n - 1, axis=0)[:top_n]       # top_n x samples
    hit = np.take_along_axis(comp, top, axis=0) > -np.inf
    hits = np.bincount(top[hit], minlength=len(comp))
    return pd.Series(hits / samples, index=pillar_scores.index), []


def rank(df, conditions, pillars):
    """Run the engine. Returns (ranked, excluded, report)."""
    report = {"warnings": []}
    horizon = parse_horizon(conditions.get("horizon", 2026))
    scenario = conditions.get("scenario", "rcp85")
    weights = conditions.get("weights") or {}
    floor = conditions.get("pillar_floor_percentile", 0)
    exempt = floor_exempt(conditions, pillars)

    report["warnings"] += check_gates(df, conditions)
    log = apply_gates(df, conditions)
    passed = log["failed_gates"] == ""
    sc = score(df, pillars, weights, horizon, scenario)
    report["warnings"] += sc.warnings
    scores = sc.scores
    scores["floor_ok"] = floor_ok(scores, sc.pillar_cols, floor, sc.weights, exempt)  # robustness reuses this mask

    # Horizon comparison. horizon_delta is a difference of national
    # percentiles, so it shows relative change only; rank_delta_2050 is the
    # rank movement a user can read. Both null when no 2050 column exists.
    other = score(df, pillars, weights, 2026 if horizon == 2050 else 2050, scenario)
    s2026, s2050 = (other, sc) if horizon == 2050 else (sc, other)
    if s2050.swapped:
        scores["horizon_delta"] = s2050.scores["composite"] - s2026.scores["composite"]
        r2026, r2050 = (order(s.scores, floor_ok(s.scores, s.pillar_cols, floor, s.weights, exempt), passed)
                        for s in (s2026, s2050))
        scores["rank_delta_2050"] = r2050 - r2026
    else:
        scores["horizon_delta"] = scores["rank_delta_2050"] = np.nan

    p = passed.to_numpy()
    scores["top_reasons"] = top_reasons(sc, scores.index[p]).reindex(scores.index)
    robust, warns = robustness(scores.loc[p, sc.pillar_cols], sc.weights, scores.loc[p, "floor_ok"], conditions)
    scores["robustness"] = robust.reindex(scores.index)
    report["warnings"] += warns

    ids = [c for c in unit(conditions).values() if c in df.columns]
    flags = [c for c in FLAG_COLUMNS if c in df.columns]
    full = pd.concat([df[ids + flags], scores, log], axis=1)
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
        moratorium_state_active_ranked=(int(ranked["moratorium_state_active"].fillna(False).astype(bool).sum())
                                        if "moratorium_state_active" in ranked else None),
        pillars=[c.removeprefix("pillar_") for c in sc.pillar_cols],
        pillar_floor_exempt=exempt,
        weights_used={c.removeprefix("pillar_"): round(float(v), 4) for c, v in sc.weights.items()},
    )
    return ranked.reset_index(drop=True), excluded.reset_index(drop=True), report
