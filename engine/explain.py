"""Per-county breakdown. Returns a plain dict so the CLI and the app share it."""
import pandas as pd

from engine.rank import DEFAULT_UNIT, floor_exempt, parse_horizon, pillar_percentiles, rank, score, unit


MORATORIUM_WARNING = "State moratorium in effect. A facility this size can't get state permits today."
# Unscored facts shown beside the scores. Label -> column.
FACTS = {
    "IRA energy community: coal closure tract": "energy_community_coal_closure",
    "IRA energy community: fossil employment area": "energy_community_ffe",
    "State moratorium in effect": "moratorium_state_active",
}

# Readable names for columns whose raw names are easy to confuse. Scored queue measures first, then
# the unscored queue context shown beside them. Columns without an entry show their raw name.
COLUMN_LABELS = {
    "queue_active_mw_clean_excl_storage": "Clean generation in the queue, excluding storage (MW)",
    "queue_operational_mw_online_5y": "Delivered or estimated online 2021-2025 (MW)",
    "queue_active_mw_storage_standalone": "Standalone storage in the queue (MW, not scored)",
    "queue_active_mw_clean": "Legacy: clean including storage in the queue (MW, not scored)",
    "queue_operational_mw_5y": "Legacy: operational, entered the queue 2019 or later (MW, not scored)",
    "queue_operational_online_date_fallback_share":
        "Delivered projects dated by proposed online date (share, not scored)",
    # Land and sensitive-area shares are county screens, not siting checks.
    "pct_protected": "Protected land, PAD-US GAP 1-2 (share of county)",
    "pct_cropland": "Cropland, NLCD pasture and crops (share of county)",
    "pct_developed": "Developed land, NLCD (share of county)",
    "pct_forest_wetland": "Forest and wetland, NLCD (share of county)",
}
# Unscored queue context shown beside the scores, so storage and legacy measures stay visible.
QUEUE_CONTEXT = ["queue_active_mw_storage_standalone", "queue_operational_online_date_fallback_share",
                 "queue_active_mw_clean", "queue_operational_mw_5y"]


def label(column):
    return COLUMN_LABELS.get(column, column)


def _flag(df, i, column):
    """True, False, or None when the column is absent or null."""
    if column not in df.columns or pd.isna(df.at[i, column]):
        return None
    return bool(df.at[i, column])


def _num(v):
    return None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)


def explain(df, conditions, pillars, fips, result=None):
    """Pillar scores, per-column raw value and percentile, gate log, coverage, and raw 2050 deltas.

    Pass result, the (ranked, excluded, report) tuple from rank() on the same
    df and conditions, to skip rerunning the engine.
    """
    u = unit(conditions)
    key = u["key"]
    fips = str(fips).zfill(5) if key == "fips" else str(fips)
    hits = df.index[df[key] == fips]
    if len(hits) == 0:
        raise KeyError(f"{key} {fips} not in the feature table")
    i = hits[0]
    horizon = parse_horizon(conditions.get("horizon", 2026))
    exempt = floor_exempt(conditions, pillars)
    scenario = conditions.get("scenario", "rcp85")
    sc = score(df, pillars, conditions.get("weights") or {}, horizon, scenario)
    ranked, excluded, _ = result if result is not None else rank(df, conditions, pillars)
    hit = ranked.index[ranked[key] == fips]
    row = ranked.loc[hit[0]] if len(hit) else None
    log = row if row is not None else excluded.loc[excluded[key] == fips].iloc[0]
    directions = {m["column"]: m.get("direction", "higher_better") for ms in pillars.values() for m in ms}
    for ms in pillars.values():
        for m in ms:
            if m.get("horizon_2050"):
                directions[m["horizon_2050"].format(scenario=scenario)] = m.get("direction", "higher_better")
    pillar_pct = pillar_percentiles(sc.scores, sc.pillar_cols)

    out = {
        key: fips,
        u["name"]: _num(df.at[i, u["name"]]) if u["name"] in df else None,
        u["group"]: _num(df.at[i, u["group"]]) if u["group"] in df else None,
        "conditions": conditions.get("name"),
        "horizon": horizon,
        "passed_gates": log["failed_gates"] == "",
        "failed_gates": [g for g in log["failed_gates"].split(";") if g],
        "unknown_gates": [g for g in log["unknown_gates"].split(";") if g],
        "rank": None if row is None else int(row["rank"]),
        "of": len(ranked),
        "composite": _num(sc.scores.at[i, "composite"]),
        "floor_ok": None if row is None else bool(row["floor_ok"]),
        "robustness": None if row is None else _num(row["robustness"]),
        "coverage": _num(sc.scores.at[i, "coverage"]),
        "pillar_floor_exempt": exempt,
        "facts": {name: _flag(df, i, col) for name, col in FACTS.items() if col in df.columns},
        "warnings": [MORATORIUM_WARNING] if _flag(df, i, "moratorium_state_active") else [],
        "top_reasons": None if row is None else [r for r in row["top_reasons"].split(";") if r],
        "context": {label(c): _num(df.at[i, c]) for c in QUEUE_CONTEXT if c in df.columns},
        "pillars": {},
        "horizon_2050_raw": {},
    }
    for pillar, cols in sc.columns.items():
        pc = f"pillar_{pillar}"
        out["pillars"][pillar] = {
            "score": _num(sc.scores.at[i, pc]),
            "national_percentile": _num(pillar_pct.at[i, pc]),
            "weight": float(sc.weights[pc]),
            "floor_exempt": pillar in exempt,
            "columns": [{"column": c, "label": label(c), "raw": _num(df.at[i, c]),
                         "percentile": _num(sc.pcts.at[i, c]), "direction": directions.get(c)} for c in cols],
        }
    for ms in pillars.values():
        for m in ms:
            today, future = m["column"], (m.get("horizon_2050") or "").format(scenario=scenario)
            if future and today in df and future in df:
                a, b = _num(df.at[i, today]), _num(df.at[i, future])
                out["horizon_2050_raw"][today] = {"today": a, future: b,
                                                  "delta": None if a is None or b is None else b - a}
    return out


def _fmt(v, spec):
    return "n/a" if v is None else format(v, spec)


def format_text(e, u=DEFAULT_UNIT):
    lines = [f"{e[u['name']]}, {e[u['group']]} ({e[u['key']]}) under {e['conditions']}, horizon {e['horizon']}"]
    if e["passed_gates"]:
        lines.append(f"rank {e['rank']} of {e['of']}, composite {_fmt(e['composite'], '.1f')}, "
                     f"floor_ok {e['floor_ok']}, robustness {_fmt(e['robustness'], '.2f')}, "
                     f"coverage {_fmt(e['coverage'], '.2f')}")
        lines.append(f"top reasons: {', '.join(label(r) for r in e['top_reasons']) or 'no column above the national median'}")
    else:
        lines.append(f"excluded by: {', '.join(e['failed_gates'])}")
    if e["unknown_gates"]:
        lines.append(f"unknown (null, not excluded): {', '.join(e['unknown_gates'])}")
    for w in e["warnings"]:
        lines.append(f"warning: {w}")
    for name, v in e["facts"].items():
        lines.append(f"{name}: {'n/a' if v is None else 'yes' if v else 'no'}")
    if e["pillar_floor_exempt"]:
        lines.append(f"exempt from the floor: {', '.join(e['pillar_floor_exempt'])}")
    for p, d in e["pillars"].items():
        lines.append(f"\n{p}{' (floor exempt)' if d['floor_exempt'] else ''}: score {_fmt(d['score'], '.1f')}, national pctl {_fmt(d['national_percentile'], '.1f')}, "
                     f"weight {d['weight']:.3f}")
        for c in d["columns"]:
            pct = "null" if c["percentile"] is None else f"{c['percentile']:.1f}"
            raw = "null" if c["raw"] is None else f"{c['raw']:.4g}" if isinstance(c["raw"], (int, float)) else c["raw"]
            name = c.get("label", c["column"])
            suffix = f"  {c['column']}" if name != c["column"] else ""
            lines.append(f"  {name:<32} raw {raw:>10}  pctl {pct:>5}  ({c['direction']}){suffix}")
    if e.get("context"):
        lines.append("\nunscored queue context:")
        for name, v in e["context"].items():
            lines.append(f"  {name}: {'n/a' if v is None else format(v, '.4g')}")
    if e["horizon_2050_raw"]:
        lines.append("\n2050 raw change:")
        for col, d in e["horizon_2050_raw"].items():
            fut = next(k for k in d if k not in ("today", "delta"))
            if d["delta"] is not None:
                lines.append(f"  {col:<24} {d['today']:.4g} -> {d[fut]:.4g} ({fut}), change {d['delta']:+.4g}")
    return "\n".join(lines)
