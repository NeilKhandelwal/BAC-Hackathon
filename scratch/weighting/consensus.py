"""Phase 5: consensus across weighting methods, the two-stage shortlist, and the weight comparison chart.

Run from the repo root after the other phase scripts:
.venv/Scripts/python.exe scratch/weighting/consensus.py
Writes scratch/weighting/out/consensus_summary.json, out/consensus_ranks.csv, and
docs/img/weights_by_method.png.

Methods and how each ranks the 1,565 gate-passing counties:
- balanced: the engine's committed ranking (results/balanced.csv).
- monetized: 25-year private cost plus carbon at $190/t, state-average prices.
- smaa: rank-1 acceptability with the floor on, ties broken by top-10 acceptability.
- critic, entropy: the column-level composites from critic.py.
- revealed: predicted probability of hosting a data center, from revealed.py.
Borda: within each method's top 20, rank 1 earns 20 points and rank 20 earns 1.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import FOCUS, IMG, OUT, ROOT, er, load, setup_out  # noqa: E402

TOP = 20
SHORTLIST_MIN_TOP10 = 0.01  # shortlisted if at least 1% of SMAA weightings (floor off) put it in the top 10
CLARK, FRANKLIN, GRANT = "53011", "36033", "53025"
PILLARS = ["energy_carbon", "water", "climate_resilience", "grid_infrastructure", "land", "community", "permitting",
           "cost"]


def borda(ranks, methods, top=TOP):
    pts = sum(np.where(ranks[m] <= top, top + 1 - ranks[m], 0) for m in methods)
    return pd.Series(pts, index=ranks.index)


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    gp = df.fips[passed].to_numpy()
    names = (df.county_name + ", " + df.state).set_axis(df.fips)

    bal = pd.read_csv(ROOT / "results/balanced.csv", dtype={"fips": str}).set_index("fips")["rank"]
    mon = pd.read_csv(OUT / "monetized_costs.csv", dtype={"fips": str}).set_index("fips")
    smaa = pd.read_csv(OUT / "smaa_acceptability.csv", dtype={"fips": str}).set_index("fips")
    crit = pd.read_csv(OUT / "critic_ranks.csv", dtype={"fips": str}, index_col=0)
    crit.index = crit.index.astype(str).str.zfill(5)
    rev = pd.read_csv(OUT / "revealed_ranks.csv", dtype={"fips": str}, index_col=0)
    rev.index = rev.index.astype(str).str.zfill(5)

    smaa_key = smaa.rank1_floor_on * 1e6 + smaa.top10_floor_on  # rank-1 first, top-10 breaks ties
    ranks = pd.DataFrame(index=pd.Index(gp, name="fips"))
    ranks["county"] = names.reindex(gp).to_numpy()
    ranks["balanced"] = bal.reindex(gp)
    ranks["monetized"] = mon.total_190.reindex(gp).rank(method="min")
    ranks["smaa"] = smaa_key.reindex(gp).rank(ascending=False, method="min")
    ranks["critic"] = crit.critic.reindex(gp)
    ranks["entropy"] = crit.entropy.reindex(gp)
    ranks["revealed"] = rev.rank_revealed.reindex(gp)
    methods = ["balanced", "monetized", "smaa", "critic", "entropy", "revealed"]
    assert ranks[methods].notna().all().all(), "a method is missing gate-passing counties"
    ranks[methods] = ranks[methods].astype(int)
    ranks["borda_all"] = borda(ranks, methods)
    ranks["borda_no_entropy"] = borda(ranks, [m for m in methods if m != "entropy"])
    ranks.sort_values("borda_all", ascending=False).to_csv(OUT / "consensus_ranks.csv")
    cons_all = ranks.sort_values(["borda_all", "monetized"], ascending=[False, True]).head(10)
    cons_ne = ranks.sort_values(["borda_no_entropy", "monetized"], ascending=[False, True]).head(10)

    # The engine run with the monetized model's data-implied weights at $190/t (negative shares set to 0).
    msum = json.loads((OUT / "monetize_summary.json").read_text())
    implied = {k: max(v, 0.0) for k, v in msum["data_implied_pillar_weights"]["190"].items()}
    implied = {p: implied.get(p, 0.0) for p in PILLARS}
    total = sum(implied.values())
    implied = {p: v / total for p, v in implied.items()}
    ranked, _, _ = er.rank(df, {**cond, "weights": implied, "robustness": {"samples": 0}}, pillars)
    engine_implied_top10 = ranked.fips.head(10).tolist()
    npv_top10 = mon.total_190.sort_values().index[:10].tolist()
    overlap = len(set(engine_implied_top10) & set(npv_top10))

    # Two-stage framework. Stage 1 shortlists counties that some weighting puts in the engine's top 10
    # (SMAA, floor off, so the floor's judgment doesn't decide the shortlist). Stage 2 ranks the
    # shortlist by monetized cost.
    short = smaa.index[smaa.top10_floor_off >= SHORTLIST_MIN_TOP10]
    short = [f for f in short if f in mon.index]
    stage2 = mon.loc[short].sort_values("total_190")
    stage2_tab = pd.DataFrame({
        "county": stage2.county, "npv_190_busd": (stage2.total_190 / 1e9).round(3),
        "co2_kt": (stage2.co2_t / 1e3).round(0), "smaa_top10_floor_off": smaa.top10_floor_off.reindex(stage2.index),
        "floor_ok": smaa.floor_ok.reindex(stage2.index), "balanced_rank": bal.reindex(stage2.index)})
    stage2_private = mon.loc[short].sort_values("private").head(5)

    # Weight comparison across methods.
    crit_sum = json.loads((OUT / "critic_summary.json").read_text())["pillar_weights"]
    rev_sum = json.loads((OUT / "revealed_summary.json").read_text())["pillar_weights"]
    W = pd.DataFrame({
        "Balanced (judgment)": pd.Series(cond["weights"]),
        "Monetized, $190/t (variance shares)": pd.Series(implied),
        "CRITIC (pillar sums)": pd.Series({k: v["critic"] for k, v in crit_sum.items()}),
        "Entropy (pillar sums)": pd.Series({k: v["entropy"] for k, v in crit_sum.items()}),
        "Revealed preference": pd.Series({k: v["revealed"] for k, v in rev_sum.items()}),
    }).reindex(PILLARS).fillna(0)
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=200)
    colors = ["#555555", "#1f618d", "#27ae60", "#b8b8b8", "#c0392b"]
    x = np.arange(len(PILLARS))
    width = 0.16
    for k, (col, color) in enumerate(zip(W.columns, colors)):
        ax.bar(x + (k - 2) * width, W[col], width, label=col, color=color)
    ax.set_xticks(x, [p.replace("_", " ") for p in PILLARS], rotation=15, fontsize=9)
    ax.set_ylabel("Weight (each method sums to 1)")
    ax.set_title("Pillar weights by method", fontsize=13, loc="left")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.text(0.01, 0.005, "Monetized: share of cross-county variance in 25-year cost at $190/t; land and community "
             "aren't monetized; negative shares set to 0. CRITIC and entropy: column weights summed by pillar, "
             "so pillars with more columns get more.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(IMG / "weights_by_method.png")
    plt.close(fig)

    focus = {FOCUS[f]: ranks.loc[f, methods + ["borda_all", "borda_no_entropy"]].astype(int).to_dict()
             for f in (CLARK, FRANKLIN, GRANT)}
    table = lambda t: t[["county", *methods, "borda_all", "borda_no_entropy"]].reset_index().to_dict(  # noqa: E731
        orient="records")
    summary = {
        "methods": methods, "top": TOP, "consensus_top10_all": table(cons_all),
        "consensus_top10_no_entropy": table(cons_ne), "focus": focus,
        "method_top10": {m: ranks.sort_values(m).county.head(10).tolist() for m in methods},
        "engine_with_implied_weights": {"weights": implied, "top10": [names[f] for f in engine_implied_top10],
                                        "npv_top10": [names[f] for f in npv_top10], "overlap_with_npv_top10": overlap},
        "shortlist": {"rule": f"SMAA top-10 acceptability, floor off, >= {SHORTLIST_MIN_TOP10:.0%}",
                      "size": len(short), "stage2_top10_by_190": stage2_tab.head(10).reset_index().to_dict(
                          orient="records"),
                      "stage2_top5_private": stage2_private.county.tolist(),
                      "focus_in_shortlist": {FOCUS[f]: f in short for f in (CLARK, FRANKLIN, GRANT)},
                      "focus_stage2_rank": {FOCUS[f]: (int(stage2.index.get_loc(f)) + 1 if f in stage2.index else None)
                                            for f in (CLARK, FRANKLIN, GRANT)}},
        "weights_table": W.round(3).to_dict(), "chart": "docs/img/weights_by_method.png",
    }
    (OUT / "consensus_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    pd.set_option("display.width", 220)
    print("consensus top 10, all six methods:")
    print(cons_all[["county", *methods, "borda_all"]].to_string())
    print("\nconsensus top 10, without entropy:")
    print(cons_ne[["county", *methods, "borda_no_entropy"]].to_string())
    print("\nfocus:", json.dumps(focus))
    print("\nengine with implied weights", {k: round(v, 3) for k, v in implied.items()})
    print("  top 10:", [names[f] for f in engine_implied_top10])
    print("  NPV top 10:", [names[f] for f in npv_top10], "overlap", overlap)
    print(f"\nshortlist ({summary['shortlist']['rule']}): {len(short)} counties; focus in it:",
          summary["shortlist"]["focus_in_shortlist"], "stage-2 ranks:", summary["shortlist"]["focus_stage2_rank"])
    print(stage2_tab.head(10).to_string())
    print("stage 2, private cost only, top 5:", stage2_private.county.tolist())
    print("\nweights:\n", W.round(3).to_string())


if __name__ == "__main__":
    main()
