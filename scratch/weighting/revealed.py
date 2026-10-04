"""Phase 4: revealed preference. Which scored columns predict where data centers already are?

Run from the repo root: .venv/Scripts/python.exe scratch/weighting/revealed.py
Needs scratch/weighting/out/monetized_costs.csv (run monetize.py first).
Writes scratch/weighting/out/revealed_summary.json and out/revealed_ranks.csv.

Outcome: the county has at least one existing data center in FracTracker (dc_existing_count > 0).
Features: every scored column in engine/pillars.yaml that has data, except dc_existing_count, with
its pillars.yaml transform. Model: L2 logistic regression with median imputation and standardization
fit inside stratified 5-fold cross validation, trained on all 3,109 counties. FracTracker's existing
facilities reflect past siting, much of it near metros for latency, not AI campus siting.
"""
import json

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import FOCUS, OUT, ROOT, load, setup_out

SEED = 0
OUTCOME = "dc_existing_count"
CLARK, FRANKLIN, GRANT = "53011", "36033", "53025"


def features(df, pillars):
    X, pillar_of, direction = {}, {}, {}
    for pillar, metrics in pillars.items():
        for mt in metrics:
            c = mt["column"]
            if c == OUTCOME or c not in df.columns:
                continue
            v = pd.to_numeric(df[c], errors="coerce").astype(float)
            X[c] = np.log1p(v) if mt.get("transform") == "log1p" else v
            pillar_of[c] = pillar
            direction[c] = 1 if mt.get("direction", "higher_better") == "higher_better" else -1
    return pd.DataFrame(X).set_axis(df.fips), pillar_of, direction


def model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=1.0, max_iter=5000))


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    X, pillar_of, direction = features(df, pillars)
    y = (df[OUTCOME].fillna(0).to_numpy() > 0).astype(int)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)

    oof = cross_val_predict(model(), X, y, cv=cv, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, oof)
    oof_pop = cross_val_predict(model(), X[["population"]], y, cv=cv, method="predict_proba")[:, 1]
    auc_pop = roc_auc_score(y, oof_pop)
    print(f"positives {y.sum()} of {len(y)} ({y.mean():.1%}); out-of-fold AUC {auc:.3f}; "
          f"population-only AUC {auc_pop:.3f}; lift {auc - auc_pop:+.3f}")
    summary = {"counties": int(len(y)), "positives": int(y.sum()), "auc": float(auc),
               "auc_population_only": float(auc_pop), "auc_lift": float(auc - auc_pop)}
    if auc < 0.65:
        summary["stopped"] = "AUC below 0.65"
        (OUT / "revealed_summary.json").write_text(json.dumps(summary, indent=2))
        print("AUC below 0.65: phase stops here.")
        return

    fit = model().fit(X, y)
    coef = pd.Series(fit[-1].coef_[0], index=X.columns)
    filled = pd.DataFrame(fit[0].transform(X), columns=X.columns, index=X.index)
    uni = filled.apply(lambda col: np.corrcoef(col, y)[0, 1])
    # A sign conflict: industry's preference runs against the pillar direction, and the univariate
    # correlation agrees with the coefficient's sign, so collinearity didn't flip it.
    conflict = (np.sign(coef) != pd.Series(direction)) & (np.sign(uni) == np.sign(coef))
    cols = pd.DataFrame({"pillar": pd.Series(pillar_of), "coef": coef, "univariate_r": uni,
                         "pillar_direction": pd.Series(direction), "sign_conflict": conflict})
    cols["abs_coef"] = cols.coef.abs()
    cols = cols.sort_values("abs_coef", ascending=False)

    by_pillar = cols.groupby("pillar").abs_coef.sum()
    pillar_w = (by_pillar / by_pillar.sum())
    conflict_share = (cols[cols.sign_conflict].groupby("pillar").abs_coef.sum() / by_pillar).reindex(
        pillar_w.index).fillna(0)
    crit = json.loads((OUT / "critic_summary.json").read_text())["pillar_weights"]
    comp = pd.DataFrame({"revealed": pillar_w, "share_from_sign_conflicts": conflict_share,
                         "balanced": pd.Series(cond["weights"]),
                         "critic": pd.Series({k: v["critic"] for k, v in crit.items()})}).fillna(0)

    # Industry picks among gate passers with no current data center.
    prob = pd.Series(fit.predict_proba(X)[:, 1], index=X.index)
    names = (df.county_name + ", " + df.state).set_axis(df.fips)
    gp = df.fips[passed]
    rp_rank = prob[gp].rank(ascending=False, method="min").astype(int)
    mon = pd.read_csv(OUT / "monetized_costs.csv", dtype={"fips": str}).set_index("fips")
    mon_rank = mon.total_190.rank(method="min").astype(int)
    bal = pd.read_csv(ROOT / "results/balanced.csv", dtype={"fips": str}).set_index("fips")["rank"]
    ranks = pd.DataFrame({"county": names[gp].to_numpy(), "p_industry": prob[gp].to_numpy(),
                          "has_dc": (df[OUTCOME].fillna(0)[passed] > 0).to_numpy()}, index=gp.to_numpy())
    ranks["rank_revealed"] = rp_rank
    ranks["rank_monetized_190"] = mon_rank.reindex(ranks.index)
    ranks["rank_balanced"] = bal.reindex(ranks.index)
    ranks.sort_values("rank_revealed").round(4).to_csv(OUT / "revealed_ranks.csv")
    picks = ranks[~ranks.has_dc].sort_values("p_industry", ascending=False).head(10)

    # Five biggest disagreements: within the combined top 20 of revealed preference and monetized $190,
    # the largest rank differences.
    pool = ranks[(ranks.rank_revealed <= 20) | (ranks.rank_monetized_190 <= 20)].copy()
    pool["diff"] = (pool.rank_revealed - pool.rank_monetized_190).abs()
    disagree = pool.sort_values("diff", ascending=False).head(5)

    focus = {FOCUS[f]: {"p_industry": round(float(prob[f]), 3), "rank_revealed": int(rp_rank[f]),
                        "has_dc": bool(df.set_index("fips").at[f, OUTCOME] > 0)} for f in (CLARK, FRANKLIN, GRANT)}
    summary.update({
        "columns": cols.round(4).to_dict(orient="index"), "pillar_weights": comp.round(4).to_dict(orient="index"),
        "sign_conflicts": cols[cols.sign_conflict].index.tolist(),
        "industry_picks_no_dc": [{"fips": f, **r[["county", "p_industry", "rank_monetized_190", "rank_balanced"]]
                                  .to_dict()} for f, r in picks.iterrows()],
        "top10_revealed_all": ranks.sort_values("rank_revealed").head(10)[["county", "p_industry", "has_dc"]]
        .reset_index().to_dict(orient="records"),
        "disagreements": disagree[["county", "rank_revealed", "rank_monetized_190", "rank_balanced", "diff"]]
        .reset_index().to_dict(orient="records"),
        "focus": focus,
    })
    (OUT / "revealed_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    print("\ncoefficients (standardized), largest first:")
    print(cols[["pillar", "coef", "univariate_r", "pillar_direction", "sign_conflict"]].round(3).to_string())
    print("\npillar weights:")
    print(comp.round(3).to_string())
    print("\nindustry picks (gate passers without a data center):")
    print(picks[["county", "p_industry", "rank_monetized_190", "rank_balanced"]].round(3).to_string())
    print("\nfive biggest disagreements (revealed vs monetized $190, combined top 20):")
    print(disagree[["county", "rank_revealed", "rank_monetized_190", "rank_balanced", "has_dc"]].to_string())
    print("\nfocus:", focus)


if __name__ == "__main__":
    main()
