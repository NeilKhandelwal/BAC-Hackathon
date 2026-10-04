"""Measure what NLCD land cover columns do to the balanced ranking, before anything ships.

Run from the repo root: .venv/Scripts/python.exe scratch/sensitive_land/measure_landcover.py
Needs data/raw/nhgis/ (IPUMS NHGIS land cover summary), data/raw/tiger/, and data/raw/padus/.
Writes scratch/sensitive_land/out/landcover_summary.json. Columns are added in memory only.

Scenarios:
  cropland        pct_cropland (NLCD 81-82) scored in the land pillar, as engine/pillars.yaml specifies
  cultivated      the same slot scored on cultivated crops only (NLCD 82)
  all_nlcd        every NLCD column pillars.yaml maps: pct_cropland and pct_developed (land),
                  pct_forest_wetland (permitting). Appending the adapter to the table would ship this.
  full_land       all_nlcd plus pct_protected: the land pillar as originally designed
"""
import copy
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine.rank as er  # noqa: E402
from etl.adapters import nlcd_landcover, pad_us  # noqa: E402
from measure import FOCUS, smaa_focus  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
FOCUS = {**FOCUS, "53075": "Whitman, WA"}


def run(df, cond, pillars):
    r, _, rep = er.rank(df, {**cond, "robustness": {**(cond.get("robustness") or {}), "samples": 0}}, pillars)
    idx = r.set_index("fips")
    return {"top10": [f"{c}, {s} ({v:.2f})" for c, s, v in zip(r.county_name.head(10), r.state.head(10),
                                                                 r.composite.head(10))],
            "ranks": {n: (int(idx.at[f, "rank"]) if f in idx.index else None) for f, n in FOCUS.items()},
            "grant_land_pillar": round(float(idx.at["53025", "pillar_land"]), 1),
            "grant_permitting_pillar": round(float(idx.at["53025", "pillar_permitting"]), 1),
            "gap_first_to_grant": round(float(r.composite.iloc[0] - idx.at["53025", "composite"]), 2),
            "passed": rep["passed"], "floor_ok": rep["floor_ok"]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = ROOT / "data/raw"
    df, _ = er.load_features(ROOT / "data/processed/county_features.parquet")
    pillars = er.load_yaml(ROOT / "engine/pillars.yaml")
    cond = er.load_yaml(ROOT / "engine/conditions/balanced.yaml")
    nl = nlcd_landcover.build(raw).set_index("fips")
    pad = pad_us.build(raw).set_index("fips")

    def add(cols, source):
        return df.assign(**{c: df.fips.map(source[c]) for c in cols})

    cultivated_pillars = copy.deepcopy(pillars)
    for m in cultivated_pillars["land"]:
        if m["column"] == "pct_cropland":
            m["column"] = "pct_cultivated_crops"

    d_crop = add(["pct_cropland"], nl)
    d_cult = add(["pct_cultivated_crops"], nl)
    d_all = add(["pct_cropland", "pct_developed", "pct_forest_wetland"], nl)
    d_full = d_all.assign(pct_protected=d_all.fips.map(pad.pct_protected))
    out = {
        "shares": {n: {c: round(float(nl.at[f, c]), 3) for c in nl.columns} for f, n in FOCUS.items()},
        "committed": run(df, cond, pillars),
        "cropland": run(d_crop, cond, pillars),
        "cultivated": run(d_cult, cond, cultivated_pillars),
        "all_nlcd": run(d_all, cond, pillars),
        "full_land": run(d_full, cond, pillars),
    }
    out["smaa_grant"] = {k: smaa_focus(d, cond, p)["focus"]["Grant, WA"] for k, d, p in
                         [("committed", df, pillars), ("cropland", d_crop, pillars),
                          ("all_nlcd", d_all, pillars), ("full_land", d_full, pillars)]}
    (OUT / "landcover_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
