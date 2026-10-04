"""Pre-Phase 2: parameter uncertainty over the monetized model. Is the top-3 tie at $190/t real?

Run from the repo root: .venv/Scripts/python.exe scratch/weighting/montecarlo.py
Needs data/raw/nri/nri_counties.csv, like monetize.py.
Writes scratch/weighting/out/montecarlo_summary.json and docs/img/mc_winners.png.

Each draw varies: a price multiplier per state and a carbon-rate multiplier per eGRID subregion,
both U(0.8, 1.2); the monthly delay cost U($10M, $50M), applied to time to power and moratorium;
active-moratorium months U(8, 20); and the carbon price U($100, $300)/t. Everything else stays at
the monetize.py defaults. Counties that share a state and subregion get the same multipliers, so
the draws rank state-and-subregion clusters; cluster shares are reported next to county shares.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import monetize as m  # noqa: E402
from common import IMG, OUT, load, setup_out  # noqa: E402
from etl import impact  # noqa: E402

N = 1000
SEED = 42
RANGES = {"price_mult": (0.8, 1.2), "carbon_rate_mult": (0.8, 1.2), "delay_usd_month": (10e6, 50e6),
          "moratorium_months_active": (8, 20), "carbon_usd_t": (100, 300)}
CLARK, FRANKLIN, GRANT = "53011", "36033", "53025"


def components(df, passed):
    """Base components from monetize.compute, plus the parts each draw scales."""
    alr, _, _ = m.hazard_rates()
    queue_median = float(df.queue_median_age_years.median())
    p, allc, costs = m.run(df, passed, alr, queue_median)
    sub = df[passed].set_index("fips")
    flag = lambda c: sub[c].fillna(False).astype(bool).to_numpy()  # noqa: E731
    active = flag("moratorium_state_active") | flag("moratorium_active")
    fixed_months = (flag("moratorium_pending") * p["moratorium_months_pending"] * p["p_pending"]
                    + flag("dc_pushback_any") * p["pushback_months"] * p["p_pushback"])
    c = costs.loc[sub.index]
    return p, c, {"state": sub.state.to_numpy(), "subregion": sub.grid_subregion.to_numpy(),
                  "active": active, "fixed_months": fixed_months}


def totals(c, extra, af, price_mult, carbon_mult, delay, months, carbon_usd):
    """Total NPV per county for one draw. price_mult and carbon_mult are per-county arrays."""
    energy = c.facility_mwh.to_numpy() * c.price_usd_mwh.to_numpy() * price_mult * af
    carbon = c.co2_t.to_numpy() * carbon_mult * carbon_usd * af
    ttp = c.delay_months_ttp.to_numpy() * delay
    mor = (extra["active"] * months + extra["fixed_months"]) * delay
    return energy + carbon + ttp + mor + c.water.to_numpy() + c.hazard.to_numpy()


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    p, c, extra = components(df, passed)
    af = m.annuity(p["rate"], p["years"])
    fips = c.index.to_numpy()
    n = len(fips)

    # Self-check: base parameters reproduce monetize.py's total at $190/t.
    base = totals(c, extra, af, 1.0, 1.0, p["delay_usd_month"], p["moratorium_months_active"], 190)
    err = float(np.abs(base - c.total_190.to_numpy()).max())
    assert err < 1.0, f"self-check failed: max difference ${err:,.2f}"

    rng = np.random.default_rng(SEED)
    states, s_idx = np.unique(extra["state"], return_inverse=True)
    subs, r_idx = np.unique(extra["subregion"], return_inverse=True)
    price_m = rng.uniform(*RANGES["price_mult"], (N, len(states)))
    carbon_m = rng.uniform(*RANGES["carbon_rate_mult"], (N, len(subs)))
    delay = rng.uniform(*RANGES["delay_usd_month"], N)
    months = rng.uniform(*RANGES["moratorium_months_active"], N)
    cprice = rng.uniform(*RANGES["carbon_usd_t"], N)
    bpa_usd = rng.uniform(*m.BPA_USD_MWH, N)

    T = np.empty((N, n))
    for d in range(N):
        T[d] = totals(c, extra, af, price_m[d, s_idx], carbon_m[d, r_idx], delay[d], months[d], cprice[d])

    first = T.argmin(axis=1)
    top3 = np.argpartition(T, 3, axis=1)[:, :3]
    p1 = pd.Series(np.bincount(first, minlength=n) / N, index=fips)
    p3 = pd.Series(np.bincount(top3.ravel(), minlength=n) / N, index=fips)
    cluster = pd.Series([f"{s} / {r}" for s, r in zip(extra["state"], extra["subregion"])], index=fips)
    cluster_p1 = pd.Series(cluster.to_numpy()[first]).value_counts(normalize=True)
    imputed_p1 = float(c.queue_imputed.to_numpy()[first].mean())

    i = {f: int(np.where(fips == f)[0][0]) for f in (CLARK, FRANKLIN, GRANT)}
    clark_beats_franklin = T[:, i[CLARK]] < T[:, i[FRANKLIN]]
    clark_beats_grant = T[:, i[CLARK]] < T[:, i[GRANT]]
    pcf = float(clark_beats_franklin.mean())
    se = float(np.sqrt(pcf * (1 - pcf) / N))

    # Win rates by tercile of each driver.
    drivers = {"delay_usd_month": delay, "moratorium_months_active": months, "carbon_usd_t": cprice}
    is_ny = np.array([s == "NY" for s in extra["state"]])[first]
    is_wa = np.array([s == "WA" for s in extra["state"]])[first]
    terciles = {}
    for name, v in drivers.items():
        cuts = np.quantile(v, [1 / 3, 2 / 3])
        rows = []
        for k, (lo, hi) in enumerate([(-np.inf, cuts[0]), (cuts[0], cuts[1]), (cuts[1], np.inf)]):
            sel = (v > lo) & (v <= hi)
            rows.append({"tercile": ["low", "mid", "high"][k], "range": [float(v[sel].min()), float(v[sel].max())],
                         "p_clark_beats_franklin": round(float(clark_beats_franklin[sel].mean()), 3),
                         "p_ny_first": round(float(is_ny[sel].mean()), 3),
                         "p_wa_first": round(float(is_wa[sel].mean()), 3)})
        terciles[name] = rows

    # Grant with BPA-like supply, on the same draws, kept out of the main ranking.
    g = c.loc[GRANT]
    g_bpa = (T[:, i[GRANT]] - g.facility_mwh * g.price_usd_mwh * price_m[:, s_idx[i[GRANT]]] * af
             - g.co2_t * carbon_m[:, r_idx[i[GRANT]]] * cprice * af
             + g.facility_mwh * bpa_usd * af
             + impact.co2_tonnes(g.facility_mwh, impact.BPA_CO2_LB_MWH) * cprice * af)
    others = np.delete(T, i[GRANT], axis=1)
    bpa_rank = (others < g_bpa[:, None]).sum(axis=1) + 1
    grant_bpa = {"median_rank": float(np.median(bpa_rank)), "p_first": float((bpa_rank == 1).mean()),
                 "p_top3": float((bpa_rank <= 3).mean()), "p10_rank": float(np.quantile(bpa_rank, 0.1)),
                 "p90_rank": float(np.quantile(bpa_rank, 0.9)),
                 "p_beats_clark": float((g_bpa < T[:, i[CLARK]]).mean()),
                 "p_beats_franklin": float((g_bpa < T[:, i[FRANKLIN]]).mean())}

    # Chart: which state wins, by carbon price and delay cost.
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    win_state = np.where(np.isin(extra["state"][first], ["WA", "NY"]), extra["state"][first], "other")
    style = {"WA": ("#1f618d", "Washington county is #1"), "NY": ("#c0392b", "New York county is #1"),
             "other": ("#b8b8b8", "Another state's county is #1")}
    for s in ("other", "WA", "NY"):
        sel = win_state == s
        ax.scatter(cprice[sel], delay[sel] / 1e6, s=14, alpha=0.8, color=style[s][0],
                   label=f"{style[s][1]} ({sel.mean():.0%} of draws)")
    ax.set_xlabel(r"Carbon price, \$ per tonne CO2")
    ax.set_ylabel(r"Delay cost, \$M per month (time to power and moratorium)")
    ax.set_title("Which state's county ranks #1 across 1,000 parameter draws", fontsize=13, loc="left")
    ax.legend(fontsize=9, frameon=True, framealpha=0.95, edgecolor="none", loc="upper left")
    ax.grid(alpha=0.3)
    fig.text(0.01, 0.005, "Each dot is one draw. Also varied: price ±20% per state, carbon rate ±20% per eGRID "
             "subregion, NY moratorium 8 to 20 months. 300 MW IT, 25 years at 7%.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    chart = IMG / "mc_winners.png"
    fig.savefig(chart)
    plt.close(fig)

    names = c.county
    top = lambda s, k=10: [{"fips": f, "county": names[f], "share": round(float(v), 3)}  # noqa: E731
                           for f, v in s.sort_values(ascending=False).head(k).items() if v > 0]
    summary = {
        "draws": N, "seed": SEED, "ranges": RANGES, "self_check_max_abs_diff_usd": err,
        "p_first_top": top(p1), "p_top3_top": top(p3), "cluster_p_first": cluster_p1.round(3).to_dict(),
        "focus": {names[f]: {"p_first": float(p1[f]), "p_top3": float(p3[f])} for f in (CLARK, FRANKLIN, GRANT)},
        "p_clark_beats_franklin": pcf, "p_clark_beats_franklin_se": se,
        "p_clark_beats_grant": float(clark_beats_grant.mean()),
        "imputed_queue_share_of_first": imputed_p1, "terciles": terciles, "grant_bpa": grant_bpa,
        "chart": "docs/img/mc_winners.png",
    }
    (OUT / "montecarlo_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"self-check max diff ${err:.4f}")
    print("P(#1):", [(r["county"], r["share"]) for r in top(p1)])
    print("P(top 3):", [(r["county"], r["share"]) for r in top(p3)])
    print("cluster P(#1):", cluster_p1.round(3).to_dict())
    print(f"P(Clark beats Franklin) = {pcf:.3f} ± {1.96 * se:.3f} (95%); P(Clark beats Grant) = "
          f"{clark_beats_grant.mean():.3f}; imputed-queue share of #1 draws = {imputed_p1:.3f}")
    for k, rows in terciles.items():
        print(k, [(r["tercile"], [round(x / 1e6, 1) if k == "delay_usd_month" else round(x, 1) for x in r["range"]],
                   r["p_clark_beats_franklin"], r["p_ny_first"], r["p_wa_first"]) for r in rows])
    print("Grant with BPA supply:", grant_bpa)


if __name__ == "__main__":
    main()
