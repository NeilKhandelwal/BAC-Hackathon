"""Revision round 1 for PR #35: sales tax comparisons and Neil's review items.

Run from the repo root after monetize.py, smaa.py, critic.py, revealed.py, and consensus.py:
.venv/Scripts/python.exe scratch/weighting/revisions.py
Writes scratch/weighting/out/revisions_summary.json.
"""
import itertools
import math
import json

import numpy as np
import pandas as pd

import monetize as m
from common import OUT, load, setup_out

FOCUS = {"53011": "Clark, WA", "36033": "Franklin, NY", "53025": "Grant, WA", "25003": "Berkshire, MA"}
THREE = ["53011", "36033", "53025"]
# Grant's own evidence (research/implementation.md, research/risk.md): full 300 MW needs the 2029
# Wanapum-Quincy line, the first phase follows the 2027 Quincy project, about 800 MW of large-load
# requests are queued ahead, and new supply takes 2 to 2.5 years from contract. From October 2026 that
# puts full load around 2029: about 12 months past the 2-year baseline, 8 months if the 2029 line lands
# mid-year on time, and up to the proxy's 18.5 months if the queue or supply slips.
GRANT_EVIDENCE_MONTHS = {"central": 12.0, "low": 8.0, "high": 18.5}


def ranked(costs, col="total_190"):
    r = costs[col].rank(method="min")
    return {
        "top5": costs.sort_values(col).county.head(5).tolist(),
        "ranks": {FOCUS[f]: (int(r[f]) if f in r.index else None) for f in FOCUS},
        "totals_busd": {FOCUS[f]: round(float(costs.at[f, col]) / 1e9, 3) for f in THREE if f in costs.index},
    }


def variance_shares(costs, price):
    comps = {k: costs[k] for k in m.PRIVATE}
    comps["carbon"] = costs[f"carbon_{price}"]
    total = sum(comps.values())
    cov = {k: float(v.cov(total) / total.var()) for k, v in comps.items()}
    var = {k: float(v.var()) for k, v in comps.items()}
    standalone = {k: v / sum(var.values()) for k, v in var.items()}
    # Shapley value with standard deviation as the worth of a coalition. (With variance as the worth,
    # Shapley reproduces the covariance shares exactly, negatives included.)
    keys = list(comps)
    n = len(keys)
    sd = {}
    for r in range(n + 1):
        for S in itertools.combinations(keys, r):
            sd[frozenset(S)] = float(sum((comps[k] for k in S), pd.Series(0.0, index=costs.index)).std()) if S else 0.0
    shap = {}
    for k in keys:
        others = [x for x in keys if x != k]
        val = 0.0
        for r in range(n):
            w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            for S in itertools.combinations(others, r):
                val += w * (sd[frozenset(S) | {k}] - sd[frozenset(S)])
        shap[k] = val
    tot = sum(shap.values())
    shap = {k: v / tot for k, v in shap.items()}
    order = lambda d: [k for k, _ in sorted(d.items(), key=lambda kv: -kv[1])]  # noqa: E731
    return {"covariance": cov, "standalone_variance": standalone, "shapley_sd": shap,
            "order_covariance": order(cov), "order_standalone": order(standalone), "order_shapley_sd": order(shap)}


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    alr, _, _ = m.hazard_rates()
    qm = float(df.queue_median_age_years.median())
    run = lambda ov=None: m.run(df, passed, alr, qm, ov)  # noqa: E731
    p, allc, base = run()
    af = m.annuity(p["rate"], p["years"])
    out = {"tax_status": {FOCUS[f]: {"exempt": bool(base.at[f, "sales_tax_exempt"]),
                                     "rate": float(base.at[f, "sales_tax_rate"]),
                                     "sales_tax_npv_musd": round(float(base.at[f, "sales_tax"]) / 1e6, 1)}
                          for f in FOCUS if f in base.index}}
    out["exempt_share_of_gate_passers"] = float(base.sales_tax_exempt.mean())

    # Tax comparisons at $190/t.
    out["tax"] = {"with_tax_5y": ranked(base), "no_tax": ranked(run({"tax": False})[2]),
                  "with_tax_4y": ranked(run({"tax_refresh_years": 4})[2]),
                  "with_tax_6y": ranked(run({"tax_refresh_years": 6})[2]),
                  "ny_exempt": ranked(run({"ny_exempt": True})[2]),
                  "refresh_taxed_everywhere": ranked(run({"other_refresh_exempt": False})[2])}

    # Variance shares that can't go negative, at each carbon price, with tax in the model.
    out["shares"] = {c: variance_shares(base, c) for c in p["carbon_prices"]}

    # Time to power: imputed counties charged $0, and imputed counties excluded.
    out["ttp_imputed_zero"] = ranked(run({"imputed_queue": "zero"})[2])
    out["ttp_imputed_excluded"] = ranked(base[~base.queue_imputed])
    out["imputed_count"] = int(base.queue_imputed.sum())

    # Grant's row from its own evidence instead of the queue proxy.
    g = {}
    for label, months in GRANT_EVIDENCE_MONTHS.items():
        c2 = base.copy()
        c2.loc["53025", "time_to_power"] = months * p["delay_usd_month"]
        c2["total_190"] = c2[m.PRIVATE].sum(axis=1) + c2["carbon_190"]
        res = ranked(c2)
        gap = float(c2.at["53025", "total_190"] - c2.at["53011", "total_190"])
        res["grant_minus_clark_musd"] = round(gap / 1e6, 1)
        res["grant_minus_franklin_musd"] = round(float(c2.at["53025", "total_190"] - c2.at["36033", "total_190"]) / 1e6, 1)
        res["grant_needs_usd_mwh_below_clark"] = round(gap / (c2.at["53025", "facility_mwh"] * af), 2)
        g[f"{label}_{months}_months"] = res
    out["grant_evidence"] = g
    out["grant_proxy_months"] = float(base.at["53025", "delay_months_ttp"])

    # Cooling: dry everywhere for Clark against Grant.
    dry = run({"cooling": "dry"})[2]
    out["dry_everywhere"] = ranked(dry)
    out["dry_everywhere"]["clark_minus_grant_musd"] = round(
        float(dry.at["53011", "total_190"] - dry.at["53025", "total_190"]) / 1e6, 1)

    # Hazard asset value $3B against $10B.
    out["hazard_3B"] = ranked(run({"asset_usd": 3e9})[2])
    out["hazard_10B"] = ranked(base)

    # One table across methods: top 10 and the four focus counties' ranks.
    cr = pd.read_csv(OUT / "consensus_ranks.csv", dtype={"fips": str}).set_index("fips")
    cr["consensus"] = cr.borda_no_entropy.rank(ascending=False, method="min").astype(int)
    cr["consensus_with_entropy"] = cr.borda_all.rank(ascending=False, method="min").astype(int)
    table = {}
    for mth in ["balanced", "monetized", "smaa", "critic", "entropy", "revealed", "consensus",
                "consensus_with_entropy"]:
        table[mth] = {"top10": cr.sort_values(mth).county.head(10).tolist(),
                      **{FOCUS[f]: int(cr.at[f, mth]) for f in FOCUS}}
    out["method_table"] = table

    (OUT / "revisions_summary.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "shares"}, indent=1, default=str))
    for c, sh in out["shares"].items():
        print(f"\nshares at ${c}/t")
        print(pd.DataFrame({k: sh[k] for k in ("covariance", "standalone_variance", "shapley_sd")}).round(3).to_string())
        print("order cov:", sh["order_covariance"], "\norder standalone:", sh["order_standalone"],
              "\norder shapley:", sh["order_shapley_sd"])


if __name__ == "__main__":
    main()
