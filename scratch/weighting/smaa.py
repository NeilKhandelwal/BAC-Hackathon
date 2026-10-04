"""Phase 2: weight-space mapping (SMAA) over the engine's pillar scores.

Run from the repo root: .venv/Scripts/python.exe scratch/weighting/smaa.py
Writes scratch/weighting/out/smaa_summary.json, out/smaa_acceptability.csv, and
docs/img/smaa_acceptability.png.

Pillar scores, gates, and floor membership come from engine/rank.py once. Then 5,000 weight vectors
drawn uniformly from the simplex (Dirichlet with every alpha 1) rank the gate-passing counties the
way the engine does: floor-passing counties first, then the weighted composite, which renormalizes
over a county's non-null pillars. Every drawn weight is positive, so floor membership doesn't change
between draws. The run is done with the floor on (balanced: 10th percentile, permitting exempt) and
off.
"""
import json

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import FOCUS, IMG, OUT, ROOT, er, load, setup_out  # noqa: E402

DRAWS = 5000
SEED = 0
TOP_N = 10
CLARK, FRANKLIN, GRANT = "53011", "36033", "53025"


def composites(vals, W):
    """Counties x draws composite, renormalized over each county's non-null pillars, as the engine does."""
    num = np.nan_to_num(vals) @ W.T
    den = (~np.isnan(vals)).astype(float) @ W.T
    return np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)


def order_key(comp, floor):
    """Sort key matching engine.rank.order: floor-passing first, then composite. Higher is better."""
    return np.where(np.isnan(comp), -np.inf, comp + np.where(floor, 1000.0, 0.0)[:, None])


def acceptability(key, top_n=TOP_N):
    n, d = key.shape
    first = key.argmax(axis=0)
    top = np.argpartition(-key, top_n - 1, axis=0)[:top_n]
    return np.bincount(first, minlength=n) / d, np.bincount(top.ravel(), minlength=n) / d, first


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    sc = er.score(df, pillars, cond["weights"])
    cols = sc.pillar_cols
    floor = cond.get("pillar_floor_percentile", 0)
    exempt = er.floor_exempt(cond, pillars)
    floor_all = er.floor_ok(sc.scores, cols, floor, None, exempt).to_numpy()

    fips = df.fips.to_numpy()[passed]
    names = (df.county_name + ", " + df.state).to_numpy()[passed]
    vals = sc.scores[cols].to_numpy()[passed]
    floor_on = floor_all[passed]
    floor_off = np.ones_like(floor_on)

    # Self-check: balanced weights reproduce the engine's committed top 10.
    w_bal = sc.weights[cols].to_numpy()
    key_bal = order_key(composites(vals, w_bal[None, :]), floor_on)[:, 0]
    mine = fips[np.argsort(-key_bal, kind="stable")[:TOP_N]].tolist()
    committed = pd.read_csv(ROOT / "results/balanced.csv", dtype={"fips": str}).fips.head(TOP_N).tolist()
    assert mine == committed, f"self-check failed:\n{mine}\n{committed}"

    rng = np.random.default_rng(SEED)
    W = rng.dirichlet(np.ones(len(cols)), DRAWS)
    comp = composites(vals, W)
    out = {}
    for label, fl in (("floor_on", floor_on), ("floor_off", floor_off)):
        r1, t10, first = acceptability(order_key(comp, fl))
        central = {}
        for k in np.argsort(-r1)[:5]:
            central[f"{names[k]} ({fips[k]})"] = {
                "rank1": round(float(r1[k]), 3),
                "central_weights": {c.removeprefix("pillar_"): round(float(v), 3)
                                    for c, v in zip(cols, W[first == k].mean(axis=0))}}
        out[label] = {"rank1": pd.Series(r1, index=fips), "top10": pd.Series(t10, index=fips), "central": central}

    # Franklin's floor failure: which pillar, and by how much.
    pct = er.pillar_percentiles(sc.scores, cols).set_index(df.fips)
    counted = [c for c in cols if c.removeprefix("pillar_") not in exempt]
    f_pct = pct.loc[FRANKLIN, counted]
    failing = {c.removeprefix("pillar_"): round(float(v), 1) for c, v in f_pct[f_pct < floor].items()}

    # Franklin against Grant and Clark with the floor off: the energy_carbon weight at which Franklin's
    # composite passes theirs, with the other pillars kept in balanced proportion.
    S = sc.scores.set_index(df.fips)[cols]
    e = "pillar_energy_carbon"
    rest = [c for c in cols if c != e]
    b = sc.weights[rest] / sc.weights[rest].sum()

    def crossing(a, z):
        """w_e where composite(a) = composite(z); composite = w_e * E + (1 - w_e) * R."""
        Ea, Ez = S.at[a, e], S.at[z, e]
        Ra, Rz = (S.loc[a, rest] * b).sum(), (S.loc[z, rest] * b).sum()
        denom = (Ea - Ra) - (Ez - Rz)
        w = (Rz - Ra) / denom if denom else np.nan
        return {"weight": round(float(w), 3), "valid": bool(0 <= w <= 1),
                "franklin_ahead_above": bool(denom > 0), "balanced_energy_carbon": round(float(sc.weights[e]), 3)}

    boundary = {"Franklin vs Grant": crossing(FRANKLIN, GRANT), "Franklin vs Clark": crossing(FRANKLIN, CLARK)}

    # Table and chart.
    tab = pd.DataFrame({"county": names, "rank1_floor_on": out["floor_on"]["rank1"].to_numpy(),
                        "top10_floor_on": out["floor_on"]["top10"].to_numpy(),
                        "rank1_floor_off": out["floor_off"]["rank1"].to_numpy(),
                        "top10_floor_off": out["floor_off"]["top10"].to_numpy(),
                        "floor_ok": floor_on}, index=pd.Index(fips, name="fips"))
    tab = tab.sort_values(["rank1_floor_on", "top10_floor_on"], ascending=False)
    tab.round(4).to_csv(OUT / "smaa_acceptability.csv")

    show = tab[(tab.rank1_floor_on > 0) | (tab.rank1_floor_off > 0)]
    show = show.loc[show[["rank1_floor_on", "rank1_floor_off"]].max(axis=1).sort_values(ascending=False).index[:15]]
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    y = np.arange(len(show))[::-1]
    ax.barh(y + 0.2, show.rank1_floor_on, 0.4, color="#1f618d", label="Floor on (balanced rule)")
    ax.barh(y - 0.2, show.rank1_floor_off, 0.4, color="#c0392b", label="Floor off")
    ax.set_yticks(y, [f"{c}{'' if ok else ' *'}" for c, ok in zip(show.county, show.floor_ok)], fontsize=8)
    ax.set_xlabel("Rank-1 acceptability: share of 5,000 random weightings in which the county ranks #1")
    ax.set_title("Which counties win under some weighting of the eight pillars", fontsize=13, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    fig.text(0.01, 0.005, "Weights drawn uniformly from all possible weightings (Dirichlet, alpha 1). "
             "* fails the pillar floor, so it can win only with the floor off.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    chart = IMG / "smaa_acceptability.png"
    fig.savefig(chart)
    plt.close(fig)

    focus = {FOCUS[f]: {k: round(float(tab.at[f, k]), 4) for k in
                        ["rank1_floor_on", "top10_floor_on", "rank1_floor_off", "top10_floor_off"]}
             | {"floor_ok": bool(tab.at[f, "floor_ok"])} for f in (CLARK, FRANKLIN, GRANT)}
    top = lambda k: [{"fips": f, "county": tab.at[f, "county"], "share": round(float(v), 3)}  # noqa: E731
                     for f, v in tab[k].sort_values(ascending=False).head(10).items() if v > 0]
    summary = {
        "draws": DRAWS, "seed": SEED, "pillars": [c.removeprefix("pillar_") for c in cols],
        "counties": int(len(fips)), "floor_ok_counties": int(floor_on.sum()), "self_check_top10": mine,
        "rank1_floor_on": top("rank1_floor_on"), "top10_floor_on": top("top10_floor_on"),
        "rank1_floor_off": top("rank1_floor_off"), "top10_floor_off": top("top10_floor_off"),
        "central_floor_on": out["floor_on"]["central"], "central_floor_off": out["floor_off"]["central"],
        "focus": focus, "franklin_floor_failing_pillars": failing, "floor_percentile": floor,
        "energy_carbon_boundary_floor_off": boundary, "chart": "docs/img/smaa_acceptability.png",
    }
    (OUT / "smaa_summary.json").write_text(json.dumps(summary, indent=2))

    print("self-check passed:", mine == committed)
    for k in ("rank1_floor_on", "top10_floor_on", "rank1_floor_off", "top10_floor_off"):
        print(k, [(r["county"], r["share"]) for r in summary[k]])
    for k in ("central_floor_on", "central_floor_off"):
        print(k)
        for name, v in summary[k].items():
            print("  ", name, v["rank1"], v["central_weights"])
    print("focus:", json.dumps(focus))
    print("Franklin failing pillars:", failing, "floor", floor)
    print("energy_carbon boundary (floor off):", boundary)


if __name__ == "__main__":
    main()
