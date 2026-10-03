"""Per-county breakdown. Returns a plain dict so the CLI and the app share it."""
import pandas as pd

from engine.rank import parse_horizon, pillar_percentiles, rank, score


def _num(v):
    return None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)


def explain(df, conditions, pillars, fips, result=None):
    """Pillar scores, per-column raw value and percentile, gate log, coverage, and raw 2050 deltas.

    Pass result, the (ranked, excluded, report) tuple from rank() on the same
    df and conditions, to skip rerunning the engine.
    """
    fips = str(fips).zfill(5)
    hits = df.index[df["fips"] == fips]
    if len(hits) == 0:
        raise KeyError(f"fips {fips} not in the feature table")
    i = hits[0]
    horizon = parse_horizon(conditions.get("horizon", 2026))
    scenario = conditions.get("scenario", "rcp85")
    sc = score(df, pillars, conditions.get("weights") or {}, horizon, scenario)
    ranked, excluded, _ = result if result is not None else rank(df, conditions, pillars)
    hit = ranked.index[ranked["fips"] == fips]
    row = ranked.loc[hit[0]] if len(hit) else None
    log = row if row is not None else excluded.loc[excluded["fips"] == fips].iloc[0]
    directions = {m["column"]: m.get("direction", "higher_better") for ms in pillars.values() for m in ms}
    for ms in pillars.values():
        for m in ms:
            if m.get("horizon_2050"):
                directions[m["horizon_2050"].format(scenario=scenario)] = m.get("direction", "higher_better")
    pillar_pct = pillar_percentiles(sc.scores, sc.pillar_cols)

    out = {
        "fips": fips,
        "county_name": _num(df.at[i, "county_name"]) if "county_name" in df else None,
        "state": _num(df.at[i, "state"]) if "state" in df else None,
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
        "top_reasons": None if row is None else [r for r in row["top_reasons"].split(";") if r],
        "pillars": {},
        "horizon_2050_raw": {},
    }
    for pillar, cols in sc.columns.items():
        pc = f"pillar_{pillar}"
        out["pillars"][pillar] = {
            "score": _num(sc.scores.at[i, pc]),
            "national_percentile": _num(pillar_pct.at[i, pc]),
            "weight": float(sc.weights[pc]),
            "columns": [{"column": c, "raw": _num(df.at[i, c]), "percentile": _num(sc.pcts.at[i, c]),
                         "direction": directions.get(c)} for c in cols],
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


def format_text(e):
    lines = [f"{e['county_name']}, {e['state']} ({e['fips']}) under {e['conditions']}, horizon {e['horizon']}"]
    if e["passed_gates"]:
        lines.append(f"rank {e['rank']} of {e['of']}, composite {_fmt(e['composite'], '.1f')}, "
                     f"floor_ok {e['floor_ok']}, robustness {_fmt(e['robustness'], '.2f')}, "
                     f"coverage {_fmt(e['coverage'], '.2f')}")
        lines.append(f"top reasons: {', '.join(e['top_reasons']) or 'no column above the national median'}")
    else:
        lines.append(f"excluded by: {', '.join(e['failed_gates'])}")
    if e["unknown_gates"]:
        lines.append(f"unknown (null, not excluded): {', '.join(e['unknown_gates'])}")
    for p, d in e["pillars"].items():
        lines.append(f"\n{p}: score {_fmt(d['score'], '.1f')}, national pctl {_fmt(d['national_percentile'], '.1f')}, "
                     f"weight {d['weight']:.3f}")
        for c in d["columns"]:
            pct = "null" if c["percentile"] is None else f"{c['percentile']:.1f}"
            raw = "null" if c["raw"] is None else f"{c['raw']:.4g}" if isinstance(c["raw"], (int, float)) else c["raw"]
            lines.append(f"  {c['column']:<32} raw {raw:>10}  pctl {pct:>5}  ({c['direction']})")
    if e["horizon_2050_raw"]:
        lines.append("\n2050 raw change:")
        for col, d in e["horizon_2050_raw"].items():
            fut = next(k for k in d if k not in ("today", "delta"))
            if d["delta"] is not None:
                lines.append(f"  {col:<24} {d['today']:.4g} -> {d[fut]:.4g} ({fut}), change {d['delta']:+.4g}")
    return "\n".join(lines)
