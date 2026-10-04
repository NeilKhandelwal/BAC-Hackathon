"""Phase 3 measurement: what pct_protected does to the balanced ranking, before anything ships.

Run from the repo root: .venv/Scripts/python.exe scratch/sensitive_land/measure.py
Needs data/raw/tiger/ (county and AIANNH) and data/raw/padus/ (see docs/sensitive_land_log.md).
Writes scratch/sensitive_land/out/measure_summary.json. Reads the committed county table and adds the
new columns in memory only; the frozen table is not changed.

Options measured:
  a. score pct_protected in the land pillar, as engine/pillars.yaml specifies
  b. use it as a gate (docs/schema.md calls it a "sensitive-area gate"), at stated thresholds
  c. context only: the committed ranking, unchanged
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scratch/weighting"))
import engine.rank as er  # noqa: E402
from etl.adapters import pad_us, tribal_lands  # noqa: E402
from smaa import acceptability, composites, order_key  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
FOCUS = {"53025": "Grant, WA", "53011": "Clark, WA", "36033": "Franklin, NY", "25003": "Berkshire, MA"}
GATE_THRESHOLDS = (0.5, 0.25)
SMAA_DRAWS, SEED = 5000, 0


def ranked(df, cond, pillars):
    r, ex, rep = er.rank(df, {**cond, "robustness": {**(cond.get("robustness") or {}), "samples": 0}}, pillars)
    return r, ex, rep


def focus_ranks(r):
    idx = r.set_index("fips")["rank"]
    return {n: (int(idx[f]) if f in idx.index else None) for f, n in FOCUS.items()}


def smaa_focus(df, cond, pillars):
    """Rank-1 and top-10 acceptability with the floor on, as in scratch/weighting/smaa.py."""
    log = er.apply_gates(df, cond)
    passed = (log.failed_gates == "").to_numpy()
    sc = er.score(df, pillars, cond["weights"])
    floor = er.floor_ok(sc.scores, sc.pillar_cols, cond["pillar_floor_percentile"], None,
                        er.floor_exempt(cond, pillars)).to_numpy()[passed]
    vals = sc.scores[sc.pillar_cols].to_numpy()[passed]
    W = np.random.default_rng(SEED).dirichlet(np.ones(len(sc.pillar_cols)), SMAA_DRAWS)
    r1, t10, _ = acceptability(order_key(composites(vals, W), floor))
    fips = df.fips.to_numpy()[passed]
    s1, s10 = pd.Series(r1, index=fips), pd.Series(t10, index=fips)
    names = (df.county_name + ", " + df.state).set_axis(df.fips)
    return {"focus": {n: {"rank1": round(float(s1.get(f, 0)), 4), "top10": round(float(s10.get(f, 0)), 4)}
                      for f, n in FOCUS.items()},
            "top10_by_top10_acceptability": [(names[f], round(float(v), 3)) for f, v in s10.nlargest(10).items()],
            "top5_by_rank1": [(names[f], round(float(v), 3)) for f, v in s1.nlargest(5).items()]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = ROOT / "data/raw"
    df, _ = er.load_features(ROOT / "data/processed/county_features.parquet")
    pillars = er.load_yaml(ROOT / "engine/pillars.yaml")
    cond = er.load_yaml(ROOT / "engine/conditions/balanced.yaml")
    pad = pad_us.build(raw).set_index("fips")
    tribal = tribal_lands.build(raw).set_index("fips").tribal_land_share

    # Land-only share as a denominator sensitivity.
    import geopandas as gpd
    c = gpd.read_file(raw / "tiger/cb_2024_us_county_500k.zip", ignore_geometry=True).set_index("GEOID")
    land_only = (pad.pct_protected * (c.ALAND + c.AWATER).reindex(pad.index) / c.ALAND.reindex(pad.index)).clip(upper=1)

    base = pd.read_csv(ROOT / "results/balanced.csv", dtype={"fips": str})
    out = {"committed_top10": base.head(10)[["county_name", "state"]].agg(", ".join, axis=1).tolist(),
           "committed_focus": {n: int(base.set_index("fips")["rank"].get(f)) if f in set(base.fips) else None
                               for f, n in FOCUS.items()}}

    # (a) scored.
    da = df.assign(pct_protected=df.fips.map(pad.pct_protected))
    ra, _, repa = ranked(da, cond, pillars)
    top = ra.head(10).fips.tolist()
    out["a_scored"] = {
        "top10": [{"county": f"{ra.set_index('fips').at[f, 'county_name']}, {ra.set_index('fips').at[f, 'state']}",
                   "composite": round(float(ra.set_index('fips').at[f, 'composite']), 2),
                   "pct_protected": round(float(pad.at[f, "pct_protected"]), 3),
                   "pct_protected_land_only": round(float(land_only[f]), 3),
                   "pct_protected_gap1to3": round(float(pad.at[f, "pct_protected_gap1to3"]), 3),
                   "tribal_land_share": round(float(tribal[f]), 3)} for f in top],
        "focus": focus_ranks(ra), "passed": repa["passed"], "floor_ok": repa["floor_ok"],
        "gap_first_to_grant": round(float(ra.composite.iloc[0] - ra.set_index("fips").at["53025", "composite"]), 2),
        "smaa": smaa_focus(da, cond, pillars),
    }
    out["focus_shares"] = {n: {"pct_protected": round(float(pad.at[f, "pct_protected"]), 4),
                               "pct_protected_land_only": round(float(land_only[f]), 4),
                               "pct_protected_gap1to3": round(float(pad.at[f, "pct_protected_gap1to3"]), 4),
                               "tribal_land_share": round(float(tribal[f]), 4),
                               "pct_protected_national_percentile": round(float((pad.pct_protected < pad.at[f, "pct_protected"]).mean() * 100), 1)}
                           for f, n in FOCUS.items()}

    # Other presets, committed against scored.
    presets = {}
    for name in ("speed_to_power", "sustainability_first"):
        pc = er.load_yaml(ROOT / f"engine/conditions/{name}.yaml")
        committed = pd.read_csv(ROOT / f"results/{name}.csv", dtype={"fips": str})
        rp, _, _ = ranked(da, pc, pillars)
        presets[name] = {"committed_first": f"{committed.county_name.iloc[0]}, {committed.state.iloc[0]}",
                         "scored_first": f"{rp.county_name.iloc[0]}, {rp.state.iloc[0]}",
                         "committed_focus": {n: int(committed.set_index("fips")["rank"][f]) if f in set(committed.fips)
                                             else None for f, n in FOCUS.items()},
                         "scored_focus": focus_ranks(rp),
                         "scored_top5": rp.head(5)[["county_name", "state"]].agg(", ".join, axis=1).tolist()}
    out["other_presets"] = presets

    # (b) gate: exclude counties whose protected share exceeds a threshold. The engine has no such gate
    # yet, so this filters the committed ranking's gate passers and reranks them unchanged otherwise.
    gates = {}
    committed_passers = set(base.fips)
    for t in GATE_THRESHOLDS:
        keep = base[base.fips.map(pad.pct_protected) <= t]
        gates[str(t)] = {"excluded_gate_passers": int(len(committed_passers) - len(keep)),
                         "excluded_nationally": int((pad.pct_protected > t).sum()),
                         "grant_passes": bool(pad.at["53025", "pct_protected"] <= t),
                         "top10": keep.head(10)[["county_name", "state"]].agg(", ".join, axis=1).tolist()}
    out["b_gate"] = gates

    # (c) context only: committed SMAA numbers for comparison.
    out["c_context_only"] = {"focus": out["committed_focus"], "note": "ranking unchanged"}
    out["c_context_only"]["smaa"] = smaa_focus(df, cond, pillars)
    (OUT / "measure_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
