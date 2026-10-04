"""Phase 1: monetized total cost of siting a 300 MW IT campus in each gate-passing county.

Run from the repo root: .venv/Scripts/python.exe scratch/weighting/monetize.py
Needs data/raw/nri/nri_counties.csv; docs/weighting_log.md has the fetch command.
Writes scratch/weighting/out/monetized_costs.csv, out/monetize_summary.json, and
docs/img/cost_vs_co2.png.

Every cost is a 25-year NPV in dollars. Energy, carbon, water, and hazard are annual flows
discounted with an annuity factor. Time to power and moratorium delay are one-time costs at
year 0. Fiber, land, and community are not monetized; they stay gates or unscored.
"""
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import FOCUS, IMG, OUT, ROOT, load, names, setup_out  # noqa: E402
from etl import impact  # noqa: E402

# Every parameter in one place. docs/weighting_log.md and docs/weighting.md list the basis.
DEFAULTS = {
    "mw": 300,                          # IT load
    "load_factor": impact.LOAD_FACTOR,  # 0.8, as in etl/impact.py
    "years": 25,
    "rate": 0.07,                       # discount rate
    "carbon_prices": [0, 51, 190, 300],  # $/t CO2; 190 is EPA's 2023 social cost of carbon
    "water_usd_per_kgal": 7.0,          # assumption, not sourced
    "asset_usd": 10e9,                  # campus capex exposed to hazard loss
    "delay_usd_month": 25e6,
    "ttp_delay_usd_month": None,        # time-to-power delay cost; None uses delay_usd_month. 0 turns the proxy off
    "queue_baseline_years": 2.0,        # queue age that costs nothing
    "imputed_queue": "median",          # how counties without a queue age are charged: median or zero
    "moratorium_months_active": 12,     # state or county moratorium in force, probability 1
    "moratorium_months_pending": 12,
    "p_pending": 0.5,
    "pushback_months": 6,
    "p_pushback": 0.3,
    "tax": True,                        # sales and use tax on equipment; False drops the component
    "tax_equipment_usd": 4e9,           # taxable IT and electrical equipment per purchase cycle
    "tax_refresh_years": 5,             # equipment is bought at year 0 and again every this many years
    # WA exemption (RCW 82.08.986) is limited to rural counties as RCW 82.14.370 defines them:
    # fewer than 100 people per square mile, or under 225 square miles of land.
    "wa_rural_max_density_per_sqkm": 100 / 2.589988,
    "wa_rural_max_area_sqkm": 225 * 2.589988,
    "wa_refresh_exempt": False,         # ESSB 6231: replacement servers not eligible from July 1, 2026
    "other_refresh_exempt": True,       # unverified states with an exemption flag: refreshes exempt too
    # NY Tax Law 1115(a)(37) covers equipment for Internet website services sold to customers. An AI
    # training campus with no hosted services for sale probably doesn't qualify, and repeal is proposed.
    "ny_exempt": False,
    "cooling": "allowed",               # allowed: evaporative where water stress <= evap_max_stress, else dry
    "evap_max_stress": 2.0,             # the balanced preset's evaporative water stress gate
}
PRIVATE = ["energy", "water", "hazard", "time_to_power", "moratorium", "sales_tax"]
COMPONENTS = ["energy", "carbon", "water", "hazard", "time_to_power", "moratorium", "sales_tax"]
PILLAR_OF = {"sales_tax": "permitting",  # the engine scores the exemption inside state_policy_risk
             "energy": "cost", "carbon": "energy_carbon", "water": "water", "hazard": "climate_resilience",
             "time_to_power": "grid_infrastructure", "moratorium": "permitting"}
GRANT, CLARK, FRANKLIN = "53025", "53011", "36033"
BPA_USD_MWH = (80, 132)  # BPA rate range for a new large load, research/impact.md


def annuity(rate, years):
    return (1 - (1 + rate) ** -years) / rate


def hazard_rates():
    """Sum of NRI building expected-annual-loss rates over the 17 hazards that have one, by fips.

    NaN means the hazard doesn't apply there (coastal flooding inland), so it counts as 0, as in
    etl/adapters/nri.py. Drought has only an agriculture rate, so it isn't in the sum.
    """
    nri = pd.read_csv(ROOT / "data/raw/nri/nri_counties.csv", dtype={"STCOFIPS": str}, low_memory=False)
    nri = nri.set_index("STCOFIPS")
    cols = [c for c in nri.columns if c.endswith("_ALRB")]
    alr = nri[cols].fillna(0).sum(axis=1)
    check = (nri.EAL_VALB / nri.BUILDVALUE).reindex(alr.index)
    rel = ((alr - check).abs() / check)
    return alr, cols, {"median_rel_diff": float(rel.median()), "p95_rel_diff": float(rel.quantile(0.95)),
                       "max_rel_diff": float(rel.max()), "max_rel_diff_fips": rel.idxmax()}


def sales_tax_inputs(df, p):
    """Combined sales tax rate and exemption flags (initial purchase, refreshes) per county.

    Rates: scratch/weighting/sales_tax_rates.csv (Tax Foundation midyear 2026 state combined rates)
    with county overrides in scratch/weighting/sales_tax_counties.csv (WA DOR Q4 2026 unincorporated
    rates, NY Publication 718 for Franklin). Exemption: the state table's state_sales_tax_exemption flag
    (unknown counts as taxed) exempts initial and refresh purchases. Washington is replaced by the
    statute: RCW 82.08.986 exempts only rural counties (RCW 82.14.370 prongs a and c tested; prong b
    can't be tested from this table), and since July 1, 2026 replacement server equipment is not
    eligible (ESSB 6231), so a rural WA county's refreshes are taxed. New York is set by ny_exempt.
    Other states' conditions (investment, jobs, refresh treatment) aren't modeled.
    """
    here = Path(__file__).resolve().parent
    rates = pd.read_csv(here / "sales_tax_rates.csv").set_index("state").combined_rate
    rate = df.state.map(rates).astype(float)
    over = pd.read_csv(here / "sales_tax_counties.csv", dtype={"fips": str}).set_index("fips")
    r_over = df.fips.map(over.combined_rate)
    rate = r_over.where(r_over.notna(), rate)
    flag = df.state_sales_tax_exemption.fillna(False).astype(bool)
    initial, refresh = flag.copy(), flag & p["other_refresh_exempt"]
    wa = df.state == "WA"
    rural = (df.pop_density_per_sqkm < p["wa_rural_max_density_per_sqkm"]) | (
        df.land_area_sqkm < p["wa_rural_max_area_sqkm"])
    initial = initial.where(~wa, rural)
    refresh = refresh.where(~wa, rural & p["wa_refresh_exempt"])
    ny = df.state == "NY"
    initial = initial.where(~ny, bool(p["ny_exempt"]))
    refresh = refresh.where(~ny, bool(p["ny_exempt"]))
    return rate.fillna(0).to_numpy(float), initial.to_numpy(bool), refresh.to_numpy(bool)


def compute(df, p, alr, queue_median):
    """One row per county with every cost component as an NPV in dollars."""
    af = annuity(p["rate"], p["years"])
    cdd = df.cdd_hist.to_numpy(float)
    bws = df.water_stress_bws.to_numpy(float)
    evap = bws <= p["evap_max_stress"] if p["cooling"] == "allowed" else np.zeros(len(df), bool)
    kind = np.where(evap, "evaporative", "dry")
    pue = np.where(evap, impact._linear(impact.PUE["evaporative"], cdd), impact._linear(impact.PUE["dry"], cdd))
    wue = np.where(evap, impact._linear(impact.WUE_L_PER_KWH["evaporative"], cdd),
                   impact._linear(impact.WUE_L_PER_KWH["dry"], cdd))
    it_mwh = p["mw"] * impact.HOURS_PER_YEAR * p["load_factor"]
    facility_mwh = it_mwh * pue
    co2 = impact.co2_tonnes(facility_mwh, df.grid_co2_lb_mwh.to_numpy(float))
    water_gal = it_mwh * 1000 * wue / impact.LITRES_PER_GALLON
    price = df.industrial_price_cents_kwh.to_numpy(float) * 10  # cents/kWh -> $/MWh
    rate = alr.reindex(df.fips).to_numpy(float)

    q = df.queue_median_age_years
    imputed = q.isna().to_numpy()
    # imputed_queue: "median" charges counties without a queue age the national median; "zero" charges them
    # nothing (as if they energize within the baseline).
    fill = p["queue_baseline_years"] if p.get("imputed_queue") == "zero" else queue_median
    q_used = q.fillna(fill).to_numpy(float)
    ttp_months = np.clip(q_used - p["queue_baseline_years"], 0, None) * 12

    flag = lambda c: df[c].fillna(False).astype(bool).to_numpy()  # noqa: E731
    active = flag("moratorium_state_active") | flag("moratorium_active")
    mor_months = (active * p["moratorium_months_active"]
                  + flag("moratorium_pending") * p["moratorium_months_pending"] * p["p_pending"]
                  + flag("dc_pushback_any") * p["pushback_months"] * p["p_pushback"])

    out = pd.DataFrame({
        "fips": df.fips.to_numpy(), "county": (df.county_name + ", " + df.state).to_numpy(),
        "cooling": kind, "pue": pue, "facility_mwh": facility_mwh, "co2_t": co2,
        "water_mgal": water_gal / 1e6, "price_usd_mwh": price, "water_stress": bws, "hazard_alr": rate,
        "queue_age_used": q_used, "queue_imputed": imputed, "delay_months_ttp": ttp_months,
        "delay_months_moratorium": mor_months,
        "energy": facility_mwh * price * af,
        "water": water_gal / 1000 * p["water_usd_per_kgal"] * (1 + bws) * af,
        "hazard": rate * p["asset_usd"] * af,
        "time_to_power": ttp_months * (p["delay_usd_month"] if p["ttp_delay_usd_month"] is None
                                       else p["ttp_delay_usd_month"]),
        "moratorium": mor_months * p["delay_usd_month"],
    })
    if p["tax"]:
        tax_rate, ex_initial, ex_refresh = sales_tax_inputs(df, p)
    else:
        tax_rate, ex_initial, ex_refresh = np.zeros(len(df)), np.ones(len(df), bool), np.ones(len(df), bool)
    # Equipment is bought at year 0 and again every tax_refresh_years within the horizon.
    pv_refresh = sum((1 + p["rate"]) ** -t for t in range(p["tax_refresh_years"], p["years"], p["tax_refresh_years"]))
    out["sales_tax_rate"] = tax_rate
    out["sales_tax_exempt"] = ex_initial
    out["sales_tax_refresh_exempt"] = ex_refresh
    out["sales_tax"] = tax_rate * p["tax_equipment_usd"] * (np.where(ex_initial, 0.0, 1.0)
                                                            + np.where(ex_refresh, 0.0, pv_refresh))
    out["private"] = out[PRIVATE].sum(axis=1)
    for c in p["carbon_prices"]:
        out[f"carbon_{c}"] = co2 * c * af
        out[f"total_{c}"] = out["private"] + out[f"carbon_{c}"]
    return out.set_index("fips")


def shares(costs, price):
    """Share of the cross-county variance in total cost from each component: cov(c, total) / var(total).

    Shares sum to 1. A negative share means the component tends to be lower where the total is higher.
    """
    comps = {k: costs[k] for k in PRIVATE}
    comps["carbon"] = costs[f"carbon_{price}"]
    total = sum(comps.values())
    var = total.var()
    return {k: float(comps[k].cov(total) / var) for k in COMPONENTS}


def pareto(costs):
    """Counties no other county beats on both annual CO2 and private cost."""
    s = costs.sort_values(["co2_t", "private"])
    best, keep = np.inf, []
    for f, row in s.iterrows():
        if row["private"] < best:
            keep.append(f)
            best = row["private"]
    return keep


def grant_variants(costs, p):
    """Grant at the regional eGRID rate and state price, and with BPA-like supply at $80 and $132/MWh."""
    af = annuity(p["rate"], p["years"])
    g = costs.loc[GRANT]
    bpa_co2 = impact.co2_tonnes(g.facility_mwh, impact.BPA_CO2_LB_MWH)
    out = {"regional": {"co2_t": float(g.co2_t), "private": float(g.private)}}
    for usd in BPA_USD_MWH:
        out[f"bpa_{usd}"] = {"co2_t": float(bpa_co2),
                             "private": float(g.private - g.energy + g.facility_mwh * usd * af)}
    return out


def bpa_variants(costs, fips, p):
    """A county at its regional rate and state price, and with BPA-like supply at $80 and $132/MWh."""
    af = annuity(p["rate"], p["years"])
    r = costs.loc[fips]
    co2 = impact.co2_tonnes(r.facility_mwh, impact.BPA_CO2_LB_MWH)
    out = {"regional": {"co2_t": float(r.co2_t), "private": float(r.private)}}
    for usd in BPA_USD_MWH:
        out[f"bpa_{usd}"] = {"co2_t": float(co2), "private": float(r.private - r.energy + r.facility_mwh * usd * af)}
    return out


def winning_conditions(costs, p, carbon_prices=(0, 51, 100, 190, 300)):
    """What each contender needs to win, at base delay cost and NY moratorium months.

    Clark and Grant can take BPA-like supply; Franklin stays at the NY average because there is no
    sourced new-load rate for it.
    """
    af = annuity(p["rate"], p["years"])
    cl, fr, gr = costs.loc[CLARK], costs.loc[FRANKLIN], costs.loc[GRANT]
    bpa_co2 = {k: impact.co2_tonnes(costs.loc[k].facility_mwh, impact.BPA_CO2_LB_MWH) for k in (CLARK, GRANT)}

    def rest(r):  # everything except energy and carbon
        return r.private - r.energy

    # BPA rate below which Clark (BPA supply) costs less than Franklin (NY average), by carbon price.
    clark_vs_franklin = {c: float((fr.private + fr.co2_t * c * af - rest(cl) - bpa_co2[CLARK] * c * af)
                                  / (cl.facility_mwh * af)) for c in carbon_prices}
    # Grant against Clark at $190/t: on the same supply, what Grant would have to save.
    gap_avg = float(gr.total_190 - cl.total_190)
    gap_bpa = {usd: float((rest(gr) + gr.facility_mwh * usd * af + bpa_co2[GRANT] * 190 * af)
                          - (rest(cl) + cl.facility_mwh * usd * af + bpa_co2[CLARK] * 190 * af))
               for usd in BPA_USD_MWH}
    return {
        "clark_bpa_co2_t": float(bpa_co2[CLARK]), "grant_bpa_co2_t": float(bpa_co2[GRANT]),
        "franklin_co2_t": float(fr.co2_t),
        "clark_bpa_beats_franklin_below_usd_mwh": clark_vs_franklin,
        "grant_minus_clark_190_state_avg_usd": gap_avg,
        "grant_needs_months_less_delay_state_avg": gap_avg / p["delay_usd_month"],
        "grant_needs_usd_mwh_discount_state_avg": gap_avg / (gr.facility_mwh * af),
        "grant_minus_clark_190_bpa_usd": gap_bpa,
        "grant_needs_months_less_delay_bpa": {k: v / p["delay_usd_month"] for k, v in gap_bpa.items()},
        "grant_time_to_power_months": float(gr.delay_months_ttp), "clark_time_to_power_months": float(cl.delay_months_ttp),
        "franklin_new_load_rate": "none sourced; NY state average used",
    }


def breakevens(costs, frontier, variants, p):
    """Carbon price at which each cleaner frontier county's private + carbon cost drops below Grant's."""
    af = annuity(p["rate"], p["years"])
    rows = []
    for f in frontier:
        if f == GRANT:
            continue
        r = costs.loc[f]
        row = {"fips": f, "county": r.county, "co2_kt": r.co2_t / 1e3, "private_musd_yr": r.private / af / 1e6}
        for name, g in variants.items():
            if r.co2_t >= g["co2_t"]:
                row[name] = None  # not cleaner than this Grant variant
            else:
                be = (r.private - g["private"]) / (af * (g["co2_t"] - r.co2_t))
                row[name] = round(max(be, 0.0), 1)  # 0 means it's already cheaper before any carbon price
        rows.append(row)
    return pd.DataFrame(rows)


def plot(costs, frontier, variants, loudoun, p, clark_variants=None):
    af = annuity(p["rate"], p["years"])
    y = costs.private / af / 1e6
    x = costs.co2_t / 1e3
    fig, ax = plt.subplots(figsize=(11, 7), dpi=200)
    ax.scatter(x, y, s=8, color="#b8b8b8", label=f"{len(costs):,} gate-passing counties", zorder=1)
    fr = costs.loc[frontier].sort_values("co2_t")
    ax.plot(fr.co2_t / 1e3, fr.private / af / 1e6, "-o", color="#c0392b", ms=4, lw=1.5,
            label="Pareto frontier (no county is both cheaper and cleaner)", zorder=3)
    # Frontier points within 40 kt of each other share one label so the names don't overlap.
    # Counties the story names get their own label.
    own = [f for f in fr.index if f in ("53011", "36033")]
    groups, cur = [], []
    for f, r in fr.drop(own).iterrows():
        if cur and r.co2_t - fr.loc[cur[-1], "co2_t"] > 40e3:
            groups.append(cur)
            cur = []
        cur.append(f)
    groups.append(cur)
    for g in filter(None, groups):
        pts = fr.loc[g]
        x0, y0 = pts.co2_t.mean() / 1e3, pts.private.min() / af / 1e6
        if len(g) > 3:
            text = textwrap.fill(f"{len(g)} frontier counties: " + ", ".join(pts.county), 48)
            ax.annotate(text, (x0, y0), xytext=(0.06, 0.06), textcoords="axes fraction", fontsize=7,
                        color="#7b241c", arrowprops=dict(arrowstyle="-", color="#7b241c", lw=0.6), zorder=4)
        else:
            ax.annotate("\n".join(pts.county), (pts.co2_t.iloc[-1] / 1e3, y0), xytext=(6, 4),
                        textcoords="offset points", fontsize=7, color="#7b241c", zorder=4)
    for f in own:
        r = fr.loc[f]
        ax.annotate(r.county, (r.co2_t / 1e3, r.private / af / 1e6), xytext=(6, -12), textcoords="offset points",
                    fontsize=8, fontweight="bold", color="#7b241c", zorder=4)
    g = variants["regional"]
    ax.scatter(g["co2_t"] / 1e3, g["private"] / af / 1e6, marker="*", s=220, color="#1f618d", zorder=5,
               label="Grant, WA at the Northwest grid average and state price")
    bx = variants["bpa_80"]["co2_t"] / 1e3
    lo, hi = variants["bpa_80"]["private"] / af / 1e6, variants["bpa_132"]["private"] / af / 1e6
    ax.plot([bx, bx], [lo, hi], color="#1f618d", lw=3, zorder=5)
    ax.scatter([bx, bx], [lo, hi], marker="_", s=200, color="#1f618d", zorder=5,
               label=r"Grant with BPA-like supply: 212 lb/MWh, \$80 to \$132/MWh")
    if clark_variants is not None:
        cx = clark_variants["bpa_80"]["co2_t"] / 1e3
        clo, chi = clark_variants["bpa_80"]["private"] / af / 1e6, clark_variants["bpa_132"]["private"] / af / 1e6
        ax.plot([cx, cx], [clo, chi], color="#7d3c98", lw=3, zorder=5)
        ax.scatter([cx, cx], [clo, chi], marker="_", s=200, color="#7d3c98", zorder=5,
                   label=r"Clark with BPA-like supply: 212 lb/MWh, \$80 to \$132/MWh")
    if loudoun is not None:
        ax.scatter(loudoun.co2_t / 1e3, loudoun.private / af / 1e6, marker="D", s=50, facecolors="none",
                   edgecolors="black", zorder=5, label="Loudoun, VA (fails the queue-age gate; reference)")
    ax.set_xlabel("CO2, thousand metric tons per year (eGRID subregion average rate)")
    ax.set_ylabel("Private cost, $M per year (25-year annualized: energy, water, hazard, delays)")
    ax.set_title("Cost and carbon of a 300 MW IT campus by county", fontsize=13, loc="left")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    fig.text(0.01, 0.005, r"Load factor 0.8, 7% over 25 years, \$25M per month of delay, \$10B asset value, "
             r"\$7 per 1,000 gal water. Cooling: evaporative where Aqueduct water stress <= 2, else dry." "\n"
             "New York counties carry a 12-month state moratorium cost. Energy uses state average industrial prices. "
             "No new-load rate is sourced for New York, so Franklin has no BPA-style range.",
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    path = IMG / "cost_vs_co2.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def run(df, passed, alr, queue_median, overrides=None):
    p = {**DEFAULTS, **(overrides or {})}
    allc = compute(df, p, alr, queue_median)
    return p, allc, allc[passed]


def summarize_variant(costs, label):
    t = costs.sort_values("total_190")
    rank190 = t.total_190.rank(method="min")
    known = costs[~costs.queue_imputed]
    return {"variant": label, "top_private": costs.private.idxmin(), "top_190": t.index[0],
            "top5_190": "; ".join(t.county.head(5)),
            "gap_1_to_2_pct": round(100 * (t.total_190.iloc[1] / t.total_190.iloc[0] - 1), 2),
            **{f"rank190_{FOCUS[f].split(',')[0]}": (int(rank190[f]) if f in rank190 else None)
               for f in ["53025", "36033", "25003"]},
            **{f"share190_{k}": round(v, 3) for k, v in shares(costs, 190).items()},
            "share190_ttp_known_queue_only": round(shares(known, 190)["time_to_power"], 3)}


def main():
    setup_out()
    df, cond, pillars, passed = load("balanced")
    alr, alr_cols, alr_err = hazard_rates()
    queue_median = float(df.queue_median_age_years.median())  # national median over counties with data
    p, allc, costs = run(df, passed, alr, queue_median)
    af = annuity(p["rate"], p["years"])
    nm = names(df)

    known = costs[~costs.queue_imputed]
    share = {c: shares(costs, c) for c in p["carbon_prices"]}
    share_known = {c: shares(known, c) for c in p["carbon_prices"]}
    frontier = pareto(costs)
    variants = grant_variants(costs, p)
    be = breakevens(costs, frontier, variants, p)

    sens = [summarize_variant(costs, "base")]
    for label, ov in [("dry everywhere", {"cooling": "dry"}), ("water $3/kgal", {"water_usd_per_kgal": 3}),
                      ("water $15/kgal", {"water_usd_per_kgal": 15}), ("delay $10M/mo", {"delay_usd_month": 10e6}),
                      ("delay $50M/mo", {"delay_usd_month": 50e6}),
                      ("moratorium 8 mo", {"moratorium_months_active": 8}),
                      ("moratorium 20 mo", {"moratorium_months_active": 20}),
                      ("time to power off", {"ttp_delay_usd_month": 0}),
                      ("queue baseline 1.5 y", {"queue_baseline_years": 1.5}),
                      ("queue baseline 2.5 y", {"queue_baseline_years": 2.5})]:
        sens.append(summarize_variant(run(df, passed, alr, queue_median, ov)[2], label))
    sens = pd.DataFrame(sens)

    loudoun = allc.loc["51107"] if "51107" in allc.index else None
    clark_variants = bpa_variants(costs, CLARK, p)
    conditions = winning_conditions(costs, p)
    img = plot(costs, frontier, variants, loudoun, p, clark_variants)

    keep = ["county", "cooling", "pue", "sales_tax_rate", "sales_tax_exempt", "sales_tax_refresh_exempt", "co2_t", "water_mgal", "price_usd_mwh", "hazard_alr", "queue_age_used",
            "queue_imputed", "delay_months_moratorium"] + COMPONENTS[:1] + PRIVATE[1:] + ["private"] + \
        [f"carbon_{c}" for c in p["carbon_prices"]] + [f"total_{c}" for c in p["carbon_prices"]]
    keep = [k for k in keep if k in costs.columns]
    costs.sort_values("total_190")[keep].round(2).to_csv(OUT / "monetized_costs.csv")

    def top(col, n=10):
        t = costs.sort_values(col).head(n)
        return [{"fips": f, "county": r.county, "npv_busd": round(r[col] / 1e9, 3), "co2_kt": round(r.co2_t / 1e3)}
                for f, r in t.iterrows()]

    weights = {c: {PILLAR_OF[k]: round(v, 3) for k, v in share[c].items()} for c in p["carbon_prices"]}
    summary = {
        "params": p, "annuity_factor": af, "counties": int(len(costs)),
        "queue_imputed": int(costs.queue_imputed.sum()), "queue_national_median_years": queue_median,
        "hazard_columns": alr_cols, "hazard_sum_vs_eal_ratio": alr_err,
        "cooling_counts": costs.cooling.value_counts().to_dict(),
        "top10_private": top("private"), **{f"top10_total_{c}": top(f"total_{c}") for c in p["carbon_prices"]},
        "variance_shares": share, "variance_shares_known_queue_only": share_known,
        "data_implied_pillar_weights": weights, "frontier": frontier, "grant_variants": variants,
        "breakevens": be.to_dict(orient="records"), "sensitivities": sens.to_dict(orient="records"),
        "focus": {nm[f]: {"rank_private": int(costs.private.rank(method="min")[f]),
                          "rank_190": int(costs.total_190.rank(method="min")[f]),
                          **{k: round(costs.loc[f, k] / 1e6, 1) for k in COMPONENTS[:1] + PRIVATE[1:]},
                          "carbon_190_musd": round(costs.loc[f, "carbon_190"] / 1e6, 1),
                          "co2_kt": round(costs.loc[f, "co2_t"] / 1e3)}
                  for f in FOCUS if f in costs.index},
        "clark_bpa_variants": clark_variants, "winning_conditions": conditions,
        "chart": str(img.relative_to(ROOT)),
    }
    (OUT / "monetize_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    # Report
    print(f"counties {len(costs)}, annuity factor {af:.3f}, queue imputed {summary['queue_imputed']} "
          f"(median {queue_median:.2f} y), cooling {summary['cooling_counts']}, hazard sum vs EAL/BUILDVALUE {alr_err}")
    t190 = costs.sort_values("total_190")
    g = costs.loc[GRANT]
    print(f"$190 head-to-head, $B: {t190.county.iloc[0]} {t190.total_190.iloc[0] / 1e9:.3f}, "
          f"{t190.county.iloc[1]} {t190.total_190.iloc[1] / 1e9:.3f}, Grant {g.total_190 / 1e9:.3f}, "
          f"Grant without time to power {(g.total_190 - g.time_to_power) / 1e9:.3f}")
    print("imputed queue share: top 50 at $190", round(t190.head(50).queue_imputed.mean(), 2),
          "overall", round(costs.queue_imputed.mean(), 2))
    for c in p["carbon_prices"]:
        print(f"top10 private+carbon ${c}:", [f"{r['county']} {r['npv_busd']}" for r in top(f'total_{c}')])
    print("top10 private:", [f"{r['county']} {r['npv_busd']}" for r in top("private")])
    print("\nvariance shares (all counties):")
    print(pd.DataFrame(share).T.round(3).to_string())
    print("variance shares (known queue age only, n=%d):" % len(known))
    print(pd.DataFrame(share_known).T.round(3).to_string())
    print("\nmean NPV by component, $B:", (costs[COMPONENTS[:1] + PRIVATE[1:] + ["carbon_190"]].mean() / 1e9).round(3).to_dict())
    print("std NPV by component, $B:", (costs[COMPONENTS[:1] + PRIVATE[1:] + ["carbon_190"]].std() / 1e9).round(3).to_dict())
    print("\nfocus:", json.dumps(summary["focus"], indent=0))
    print("\nfrontier:", [nm[f] for f in frontier])
    print("grant variants ($M/yr private, kt):", {k: (round(v['private'] / af / 1e6), round(v['co2_t'] / 1e3))
                                                   for k, v in variants.items()})
    print(be.to_string(index=False))
    print("\nsensitivities:")
    print(sens.to_string(index=False))
    print("clark bpa variants ($M/yr, kt):", {k: (round(v["private"] / af / 1e6), round(v["co2_t"] / 1e3))
                                            for k, v in clark_variants.items()})
    print("winning conditions:", json.dumps(conditions, indent=1))
    print("chart:", img)


if __name__ == "__main__":
    main()
