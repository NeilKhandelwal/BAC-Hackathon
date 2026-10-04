"""Phase 3: objective column weights by CRITIC and entropy on gate-passing counties' raw values.

Run from the repo root: .venv/Scripts/python.exe scratch/weighting/critic.py
Writes scratch/weighting/out/critic_summary.json and out/critic_weights.csv.

Each scored column in engine/pillars.yaml that has data is taken raw, given its pillars.yaml transform
(log1p where set), winsorized at the 1st and 99th percentiles of gate-passing counties, min-max scaled
to 0-1, and flipped for lower_better so 1 is always best. CRITIC weight is std_j x sum_k (1 - r_jk).
Entropy weight is 1 - e_j over p_ij = x_ij / sum_i x_ij. Both are computed with nulls set to the
column median, so every column sees the same counties. Weights apply at the column level in a scratch
composite: the weighted mean of a county's non-null scaled columns. That composite has no pillar
floor, so no floor rule is applied; the balanced floor status is reported next to each county.
"""
import json

import numpy as np
import pandas as pd

from common import FOCUS, OUT, er, load, setup_out

CLARK, FRANKLIN, GRANT = "53011", "36033", "53025"


def scaled_columns(df, pillars, passed):
    """Gate-passing counties x scored columns, transformed, winsorized, min-max scaled, direction applied."""
    sub = df[passed].set_index("fips")
    cols, pillar_of = {}, {}
    for pillar, metrics in pillars.items():
        for mt in metrics:
            c = mt["column"]
            if c not in sub.columns:
                continue
            v = pd.to_numeric(sub[c], errors="coerce").astype(float)
            if mt.get("transform") == "log1p":
                v = np.log1p(v)
            lo, hi = v.quantile(0.01), v.quantile(0.99)
            v = v.clip(lo, hi)
            v = (v - lo) / (hi - lo) if hi > lo else v * 0
            if mt.get("direction") == "lower_better":
                v = 1 - v
            cols[c] = v
            pillar_of[c] = pillar
    return pd.DataFrame(cols), pillar_of


def critic(X):
    filled = X.fillna(X.median())
    std = filled.std()
    r = filled.corr().fillna(0)
    conflict = (1 - r).sum()
    w = std * conflict
    return w / w.sum(), r, std, conflict


def entropy(X):
    filled = X.fillna(X.median())
    p = filled / filled.sum()
    n = len(filled)
    with np.errstate(divide="ignore", invalid="ignore"):
        e = -(p * np.log(p)).fillna(0).sum() / np.log(n)
    d = 1 - e
    return d / d.sum()


def composite(X, w):
    present = X.notna()
    num = X.fillna(0).mul(w, axis=1).sum(axis=1)
    den = present.mul(w, axis=1).sum(axis=1)
    return num / den


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    X, pillar_of = scaled_columns(df, pillars, passed)
    w_critic, r, std, conflict = critic(X)
    w_entropy = entropy(X)

    sc = er.score(df, pillars, cond["weights"])
    floor_ok = er.floor_ok(sc.scores, sc.pillar_cols, cond["pillar_floor_percentile"], None,
                           er.floor_exempt(cond, pillars))
    floor_ok.index = df.fips
    names = (df.county_name + ", " + df.state).set_axis(df.fips)

    res = {}
    for label, w in (("critic", w_critic), ("entropy", w_entropy)):
        s = composite(X, w).sort_values(ascending=False)
        rank = s.rank(ascending=False, method="min").astype(int)
        res[label] = {
            "top10": [{"fips": f, "county": names[f], "score": round(float(v), 4), "floor_ok": bool(floor_ok[f])}
                      for f, v in s.head(10).items()],
            "focus": {FOCUS[f]: int(rank[f]) for f in (CLARK, FRANKLIN, GRANT)},
            "ranks": rank,
        }

    weights = pd.DataFrame({"pillar": pd.Series(pillar_of), "critic": w_critic, "entropy": w_entropy,
                            "std": std, "sum_1_minus_r": conflict})
    weights.sort_values("critic", ascending=False).round(4).to_csv(OUT / "critic_weights.csv")
    n_cols = weights.groupby("pillar").size()
    bal = pd.Series(cond["weights"])
    pillar_w = pd.DataFrame({"columns": n_cols, "critic": weights.groupby("pillar").critic.sum(),
                             "entropy": weights.groupby("pillar").entropy.sum(), "balanced": bal}).fillna(0)
    pillar_w["equal_per_column"] = pillar_w["columns"] / pillar_w["columns"].sum()

    # Highly correlated pairs and how CRITIC treats them.
    pairs = []
    cols = list(X.columns)
    for a in range(len(cols)):
        for b in range(a + 1, len(cols)):
            v = r.iat[a, b]
            if abs(v) > 0.8:
                pairs.append({"a": cols[a], "b": cols[b], "r": round(float(v), 3),
                              "critic_a": round(float(w_critic[cols[a]]), 4),
                              "critic_b": round(float(w_critic[cols[b]]), 4),
                              "entropy_a": round(float(w_entropy[cols[a]]), 4),
                              "entropy_b": round(float(w_entropy[cols[b]]), 4)})
    mean_critic = float(w_critic.mean())

    ranks = pd.DataFrame({k: v["ranks"] for k, v in res.items()})
    ranks.insert(0, "county", names.reindex(ranks.index))
    ranks.sort_values("critic").to_csv(OUT / "critic_ranks.csv")
    summary = {
        "counties": int(passed.sum()), "columns": cols, "null_counts": X.isna().sum()[X.isna().sum() > 0].to_dict(),
        "column_weights": weights[["pillar", "critic", "entropy"]].round(4).to_dict(orient="index"),
        "pillar_weights": pillar_w.round(4).to_dict(orient="index"),
        "correlated_pairs_abs_r_gt_0_8": pairs, "mean_critic_column_weight": mean_critic,
        **{f"{k}_top10": v["top10"] for k, v in res.items()}, **{f"{k}_focus": v["focus"] for k, v in res.items()},
    }
    (OUT / "critic_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"{passed.sum()} counties, {len(cols)} columns; nulls: {summary['null_counts']}")
    print("\ncolumn weights (top 12 by CRITIC):")
    print(weights.sort_values("critic", ascending=False).head(12).round(4).to_string())
    print("\nlowest 6 by CRITIC:")
    print(weights.sort_values("critic").head(6).round(4).to_string())
    print("\npillar weights (sum of column weights):")
    print(pillar_w.round(3).to_string())
    print("\n|r| > 0.8 pairs (mean CRITIC column weight %.4f):" % mean_critic)
    for p in pairs:
        print("  ", p)
    for k, v in res.items():
        print(f"\n{k} top 10:", [(t["county"], t["score"], "floor ok" if t["floor_ok"] else "fails floor")
                                for t in v["top10"]])
        print(f"{k} focus ranks:", v["focus"])


if __name__ == "__main__":
    main()
