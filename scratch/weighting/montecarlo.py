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


def components(df, passed, overrides=None):
    """Base components from monetize.compute, plus the parts each draw scales."""
    alr, _, _ = m.hazard_rates()
    queue_median = float(df.queue_median_age_years.median())
    p, allc, costs = m.run(df, passed, alr, queue_median, overrides)
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
    return energy + carbon + ttp + mor + c.water.to_numpy() + c.hazard.to_numpy() + c.sales_tax.to_numpy()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--overrides", default="{}", help="JSON of monetize.DEFAULTS overrides, e.g. '{\"tax\": false}'")
    ap.add_argument("--tag", default="", help="suffix for the summary file; a tagged run writes no charts")
    args = ap.parse_args()
    overrides, tag = json.loads(args.overrides), args.tag
    setup_out()
    df, cond, pillars, passed = load("balanced")
    p, c, extra = components(df, passed, overrides)
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

    # Crossover: the carbon price at which Franklin's total equals Clark's, at base parameters, as a
    # function of delay cost D and NY moratorium months M. Both totals are linear in carbon price.
    cl, fr = c.loc[CLARK], c.loc[FRANKLIN]
    fixed = lambda r: r.energy + r.water + r.hazard + r.sales_tax  # noqa: E731
    d_co2 = af * (cl.co2_t - fr.co2_t)  # dollars per $/t of carbon price that Clark pays over Franklin
    i_f = i[FRANKLIN]

    def crossover(D, M):
        franklin = fixed(fr) + fr.delay_months_ttp * D + (extra["active"][i_f] * M + extra["fixed_months"][i_f]) * D
        clark = fixed(cl) + cl.delay_months_ttp * D + (extra["active"][i[CLARK]] * M
                                                       + extra["fixed_months"][i[CLARK]]) * D
        return (franklin - clark) / d_co2

    cross = {"base_25M_12mo": crossover(25e6, 12), "10M_12mo": crossover(10e6, 12),
             "50M_12mo": crossover(50e6, 12), "25M_8mo": crossover(25e6, 8), "25M_20mo": crossover(25e6, 20)}
    check = totals(c, extra, af, 1.0, 1.0, 25e6, 12, cross["base_25M_12mo"])
    assert abs(check[i[CLARK]] - check[i_f]) < 1.0, "crossover check failed"

    # Which driver moves the Clark - Franklin gap? Linear regression on all seven drivers per draw.
    s_of = {s: k for k, s in enumerate(states)}
    r_of = {r: k for k, r in enumerate(subs)}
    X = pd.DataFrame({
        "price_mult_WA": price_m[:, s_of["WA"]], "price_mult_NY": price_m[:, s_of["NY"]],
        "carbon_mult_NWPP": carbon_m[:, r_of["NWPP"]], "carbon_mult_NYUP": carbon_m[:, r_of["NYUP"]],
        "delay_usd_month": delay, "moratorium_months": months, "carbon_usd_t": cprice})
    gap = T[:, i[CLARK]] - T[:, i_f]
    A = np.column_stack([np.ones(N), X.to_numpy()])
    beta, *_ = np.linalg.lstsq(A, gap, rcond=None)
    r2 = 1 - ((gap - A @ beta) ** 2).sum() / ((gap - gap.mean()) ** 2).sum()
    # Independent drivers, so each one's share of the gap's variance is beta^2 var(x) / var(gap).
    drv_share = {k: float(b ** 2 * X[k].var() / gap.var()) for k, b in zip(X.columns, beta[1:])}

    # Do minor-state winners win on a lucky price draw? Mean drawn price multiplier of the winning state.
    win_mult = price_m[np.arange(N), s_idx[first]]
    win_cluster = cluster.to_numpy()[first]
    lucky = pd.Series(win_mult).groupby(win_cluster).agg(["mean", "size"]).sort_values("size", ascending=False)
    within = {"WA / NWPP won by Clark": float((fips[first][win_cluster == "WA / NWPP"] == CLARK).mean()),
              "NY / NYUP won by Franklin": float((fips[first][win_cluster == "NY / NYUP"] == FRANKLIN).mean())}

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

    # BPA fairness scenario: Clark and Grant both pay the drawn BPA new-load rate (one tariff, one draw)
    # and emit at BPA's rate with no multiplier. Franklin and every other county keep the state average.
    T_bpa = T.copy()
    for f in (CLARK, GRANT):
        k = i[f]
        r = c.iloc[k]
        energy = r.facility_mwh * r.price_usd_mwh * price_m[:, s_idx[k]] * af
        carbon = r.co2_t * carbon_m[:, r_idx[k]] * cprice * af
        rest = (r.delay_months_ttp * delay + (extra["active"][k] * months + extra["fixed_months"][k]) * delay
                + r.water + r.hazard + r.sales_tax)
        assert np.allclose(energy + carbon + rest, T[:, k]), "BPA self-check failed"
        T_bpa[:, k] = (rest + r.facility_mwh * bpa_usd * af
                       + impact.co2_tonnes(r.facility_mwh, impact.BPA_CO2_LB_MWH) * cprice * af)
    first_b = T_bpa.argmin(axis=1)
    top3_b = np.argpartition(T_bpa, 3, axis=1)[:, :3]
    p1_b = pd.Series(np.bincount(first_b, minlength=n) / N, index=fips)
    p3_b = pd.Series(np.bincount(top3_b.ravel(), minlength=n) / N, index=fips)
    cf_b = T_bpa[:, i[CLARK]] < T_bpa[:, i[FRANKLIN]]
    bpa = {
        "p_first_top": [{"fips": f, "county": c.county[f], "share": round(float(v), 3)}
                        for f, v in p1_b.sort_values(ascending=False).head(10).items() if v > 0],
        "p_top3_top": [{"fips": f, "county": c.county[f], "share": round(float(v), 3)}
                       for f, v in p3_b.sort_values(ascending=False).head(10).items() if v > 0],
        "focus": {c.county[f]: {"p_first": float(p1_b[f]), "p_top3": float(p3_b[f])} for f in (CLARK, FRANKLIN, GRANT)},
        "cluster_p_first": pd.Series(cluster.to_numpy()[first_b]).value_counts(normalize=True).round(3).to_dict(),
        "p_clark_beats_franklin": float(cf_b.mean()),
        "p_clark_beats_grant": float((T_bpa[:, i[CLARK]] < T_bpa[:, i[GRANT]]).mean()),
        "draws_changing_winner": float((first != first_b).mean()),
        "p_clark_beats_franklin_by_bpa_rate_tercile": {},
    }
    cuts = np.quantile(bpa_usd, [1 / 3, 2 / 3])
    for k, (lo, hi) in enumerate([(-np.inf, cuts[0]), (cuts[0], cuts[1]), (cuts[1], np.inf)]):
        sel = (bpa_usd > lo) & (bpa_usd <= hi)
        bpa["p_clark_beats_franklin_by_bpa_rate_tercile"][["low", "mid", "high"][k]] = {
            "range": [round(float(bpa_usd[sel].min()), 1), round(float(bpa_usd[sel].max()), 1)],
            "p": round(float(cf_b[sel].mean()), 3)}

    # BPA rate below which Clark beats Franklin at base prices, by carbon price, for the chart.
    i_c = i[CLARK]
    clark_bpa_co2 = impact.co2_tonnes(cl.facility_mwh, impact.BPA_CO2_LB_MWH)

    def clark_breakeven_rate(cp, D=25e6, M=12):
        franklin = (fixed(fr) + fr.delay_months_ttp * D + (extra["active"][i_f] * M + extra["fixed_months"][i_f]) * D
                    + fr.co2_t * cp * af)
        clark_rest = (cl.water + cl.hazard + cl.sales_tax + cl.delay_months_ttp * D
                      + (extra["active"][i_c] * M + extra["fixed_months"][i_c]) * D + clark_bpa_co2 * cp * af)
        return (franklin - clark_rest) / (cl.facility_mwh * af)

    bpa["clark_breakeven_bpa_rate_usd_mwh"] = {f"{cp}_usd_t": round(float(clark_breakeven_rate(cp)), 1)
                                               for cp in (100, 190, 300)}
    bpa["clark_breakeven_bpa_rate_usd_mwh_10M_delay"] = round(float(clark_breakeven_rate(190, D=10e6)), 1)
    bpa["clark_breakeven_bpa_rate_usd_mwh_50M_delay"] = round(float(clark_breakeven_rate(190, D=50e6)), 1)

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    ws = np.where(np.isin(extra["state"][first_b], ["WA", "NY"]), extra["state"][first_b], "other")
    style_b = {"WA": ("#1f618d", "Washington county is #1"), "NY": ("#c0392b", "New York county is #1"),
               "other": ("#b8b8b8", "Another state's county is #1")}
    for s in ("other", "WA", "NY"):
        sel = ws == s
        ax.scatter(cprice[sel], bpa_usd[sel], s=14, alpha=0.8, color=style_b[s][0],
                   label=f"{style_b[s][1]} ({sel.mean():.0%} of draws)")
    cps = np.linspace(100, 300, 50)
    for D, ls in ((25e6, "-"), (10e6, ":"), (50e6, "--")):
        ax.plot(cps, [clark_breakeven_rate(x, D=D) for x in cps], ls, color="black", lw=1.2,
                label=f"Clark = Franklin at base prices, delay \\${D / 1e6:.0f}M per month")
    ax.set_xlabel(r"Carbon price, \$ per tonne CO2")
    ax.set_ylabel(r"BPA new-load rate paid by Clark and Grant, \$ per MWh")
    ax.set_title("With BPA supply for Clark and Grant, the rate decides #1", fontsize=13, loc="left")
    ax.legend(fontsize=8, frameon=True, framealpha=0.95, edgecolor="none", loc="upper left")
    ax.grid(alpha=0.3)
    fig.text(0.01, 0.005, "Each dot is one of the same 1,000 draws. Clark and Grant: BPA rate U(\\$80, \\$132)/MWh "
             "and 212 lb CO2/MWh. Franklin and all other counties: state average price ±20%.\n"
             "No new-load rate is sourced for New York. Other Washington counties keep the state average. "
             "Below a line, Clark costs less than Franklin.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    if not tag:
        fig.savefig(IMG / "mc_winners_bpa.png")
    plt.close(fig)

    # Chart: which state wins, by carbon price and delay cost.
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    win_state = np.where(np.isin(extra["state"][first], ["WA", "NY"]), extra["state"][first], "other")
    style = {"WA": ("#1f618d", "Washington county is #1"), "NY": ("#c0392b", "New York county is #1"),
             "other": ("#b8b8b8", "Another state's county is #1")}
    for s in ("other", "WA", "NY"):
        sel = win_state == s
        ax.scatter(cprice[sel], delay[sel] / 1e6, s=14, alpha=0.8, color=style[s][0],
                   label=f"{style[s][1]} ({sel.mean():.0%} of draws)")
    dd = np.linspace(10e6, 50e6, 50)
    for M, ls in ((12, "-"), (8, ":"), (20, "--")):
        ax.plot([crossover(D, M) for D in dd], dd / 1e6, ls, color="black", lw=1.2,
                label=f"Franklin = Clark at base prices, NY moratorium {M} months")
    ax.set_xlim(95, 305)
    ax.set_xlabel(r"Carbon price, \$ per tonne CO2")
    ax.set_ylabel(r"Delay cost, \$M per month (time to power and moratorium)")
    ax.set_title("Which state's county ranks #1 across 1,000 parameter draws", fontsize=13, loc="left")
    ax.legend(fontsize=8, frameon=True, framealpha=0.95, edgecolor="none", loc="upper left")
    ax.grid(alpha=0.3)
    fig.text(0.01, 0.005, "Each dot is one draw. Also varied: price ±20% per state, carbon rate ±20% per eGRID "
             "subregion, NY moratorium 8 to 20 months. 300 MW IT, 25 years at 7%.\n"
             "Right of a line, Franklin NY costs less than Clark WA at base prices. Price draws move the "
             "winner as much as carbon price does.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    chart = IMG / "mc_winners.png"
    if not tag:
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
        "crossover_carbon_usd_t": cross, "gap_regression_r2": float(r2),
        "gap_regression_beta": dict(zip(["intercept", *X.columns], map(float, beta))),
        "gap_variance_share_by_driver": drv_share,
        "winner_state_price_mult": {k: {"mean": round(float(v["mean"]), 3), "wins": int(v["size"])}
                                    for k, v in lucky.iterrows()},
        "within_cluster": within, "bpa_scenario": bpa,
        "chart": "docs/img/mc_winners.png",
    }
    summary["overrides"] = overrides
    (OUT / f"montecarlo_summary{'_' + tag if tag else ''}.json").write_text(json.dumps(summary, indent=2))

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
    print("crossover carbon price, $/t:", {k: round(v, 1) for k, v in cross.items()})
    print(f"gap regression R2 {r2:.3f}; variance share by driver:", {k: round(v, 3) for k, v in drv_share.items()})
    print("winner state price multiplier by cluster:\n", lucky.head(12).round(3).to_string())
    print("within cluster:", within)
    print("BPA scenario:", json.dumps(bpa, indent=1))


if __name__ == "__main__":
    main()
