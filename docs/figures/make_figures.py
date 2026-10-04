"""Build the deck figures from committed files. No network.

Reads data/processed/county_features.parquet, data/processed/counties.geojson,
results/balanced.csv, the presets in engine/conditions/, and etl/impact.py.
Writes PNGs next to this file.

Usage: python docs/figures/make_figures.py [--featured 53025]

pick_story() also reads docs/figures/freeze_balanced_ranks.csv, the ranks from
results/balanced.csv at tag data-freeze-2026-10-03 (the seven-pillar ranking the
team started from), and global_table() reads results/global_balanced.csv.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.explain import explain  # noqa: E402
from engine.rank import load_features, load_yaml, rank  # noqa: E402
from etl.impact import impact  # noqa: E402

OUT = Path(__file__).resolve().parent
TABLE = ROOT / "data/processed/county_features.parquet"

# Reference palette, light mode (dataviz skill references/palette.md).
SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e4e3df"
EXCLUDED = "#d6d5d0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # first three slots validate all-pairs
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 15, "axes.titlesize": 19, "axes.labelsize": 15,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
})
PILLAR_LABELS = {
    "energy_carbon": "Energy and carbon", "water": "Water", "climate_resilience": "Climate resilience",
    "grid_infrastructure": "Grid and infrastructure", "land": "Land", "community": "Community",
    "permitting": "Permitting", "cost": "Cost of power",
}
SHORT = {"energy_carbon": "Energy", "water": "Water", "climate_resilience": "Climate", "grid_infrastructure": "Grid",
         "land": "Land", "community": "Community", "permitting": "Permitting", "cost": "Cost"}
# Grant County supply and price cases, stated in research/impact.md and research/implementation.md.
# The script multiplies them by etl/impact.py's facility energy, so the products are reproduced here.
BPA_CO2_LB_MWH = 212.46        # eGRID2023 balancing authority BPAT. research/impact.md shows it rounded to 212;
                               # 212.46 reproduces that file's 235,547 t. The exact rate isn't in a committed file.
NEW_LOAD_USD_MWH = (80, 132)   # BPA rate for a new large single load, low and high
FREEZE_TAG = "data-freeze-2026-10-03"
HAZARDS = ["drought", "inland_flood", "coastal_flood", "wildfire", "hurricane", "heat_wave", "tornado", "winter"]


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(OUT / name)


def county_map(ranked, featured):
    """National map: gate-passing counties by composite, excluded counties grey."""
    geo = gpd.read_file(ROOT / "data/processed/counties.geojson").to_crs(5070)
    geo = geo.merge(ranked[["fips", "composite"]], on="fips", how="left")
    fig, ax = plt.subplots(figsize=(14, 8.4))
    geo[geo.composite.isna()].plot(ax=ax, color=EXCLUDED, edgecolor=SURFACE, linewidth=0.15)
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    passed = geo[geo.composite.notna()]
    passed.plot(ax=ax, column="composite", cmap=cmap, edgecolor=SURFACE, linewidth=0.15, legend=True,
                legend_kwds={"label": "Composite score (balanced preset)", "orientation": "horizontal",
                             "shrink": 0.45, "pad": 0.02, "aspect": 40})
    star = geo[geo.fips == featured]
    star.boundary.plot(ax=ax, color=SERIES[1], linewidth=2.2)
    x, y = star.geometry.iloc[0].centroid.coords[0]
    name = ranked.set_index("fips").loc[featured]
    ax.annotate(f"{name.county_name}, {name.state}\nrank {int(name['rank'])}", (x, y), xytext=(x + 2.6e5, y - 3.6e5),
                fontsize=15, color=INK, arrowprops={"arrowstyle": "-", "color": INK_2, "lw": 1.2})
    ax.text(0.01, 0.02, f"Grey: excluded by a hard gate ({len(geo) - len(passed):,} of {len(geo):,} counties)",
            transform=ax.transAxes, color=INK_2, fontsize=14)
    ax.set_axis_off()
    ax.set_title(f"{len(passed):,} of {len(geo):,} counties pass the gates", loc="left", color=INK)
    save(fig, "map_composite.png")


def top10_table(ranked):
    """Top 10 as a table: rank, county, composite, robustness, state moratorium."""
    top = ranked.head(10)
    rows = [[int(r["rank"]), f"{r.county_name}, {r.state}", f"{r.composite:.1f}", f"{r.robustness:.0%}",
             "Yes" if bool(r.moratorium_state_active) else ""] for _, r in top.iterrows()]
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.set_axis_off()
    t = ax.table(cellText=rows, colLabels=["Rank", "County", "Composite", "Robustness", "State moratorium"],
                 loc="center", cellLoc="left", colLoc="left", colWidths=[0.08, 0.3, 0.15, 0.17, 0.27])
    t.auto_set_font_size(False)
    t.set_fontsize(15)
    t.scale(1, 1.75)
    for (row, col), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.8)
        cell.visible_edges = "B"
        if row == 0:
            cell.set_text_props(color=INK_2, weight="bold")
        elif col == 4 and rows[row - 1][4]:
            cell.set_text_props(color=INK, weight="bold")
    ax.set_title("Balanced preset: top 10 of 1,565 gate-passing counties", loc="left", color=INK)
    save(fig, "top10_table.png")


def pillar_bars(ranked, featured, weights, exempt):
    """Featured county's pillar scores, one bar per pillar, weight in the label."""
    row = ranked.set_index("fips").loc[featured]
    pillars = [p for p in PILLAR_LABELS if f"pillar_{p}" in row.index]
    scores = [row[f"pillar_{p}"] for p in pillars]
    total = sum(weights[p] for p in pillars)
    labels = [f"{PILLAR_LABELS[p]} ({weights[p] / total:.0%})" + (" *" if p in exempt else "") for p in pillars]
    fig, ax = plt.subplots(figsize=(11, 5.8))
    y = range(len(pillars))[::-1]
    ax.barh(list(y), scores, color=SERIES[0], height=0.62)
    for yi, s in zip(y, scores):
        ax.text(s + 1.2, yi, f"{s:.0f}", va="center", color=INK, fontsize=15)
    ax.set_yticks(list(y), labels)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Pillar score: mean national percentile of its columns (100 is best)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(f"{row.county_name}, {row.state}: composite {row.composite:.1f}, rank {int(row['rank'])}",
                 loc="left", color=INK)
    if exempt:
        ax.text(0, -0.22, "* scores in the composite but is exempt from the pillar floor", transform=ax.transAxes,
                color=INK_2, fontsize=13)
    save(fig, "featured_pillars.png")


def old_inputs(df):
    """The table as it was before the two corrections: dollar-loss hazard scores and state grid rates."""
    old = df.copy()
    for h in HAZARDS:
        old[f"nri_{h}_score"] = df[f"nri_{h}_risks"]
    old["grid_co2_lb_mwh"] = df["grid_co2_lb_mwh_state"]
    old["grid_renewable_share"] = df["grid_renewable_share_state"]
    return old


def corrections(df, conditions, pillars, counties):
    """Rank under the old inputs (dollar-loss hazard scores, state grid rates) against the corrected inputs."""
    old = old_inputs(df)
    runs = {}
    for label, frame in (("Old inputs", old), ("Corrected", df)):
        r, x, _ = rank(frame, conditions, pillars)
        runs[label] = (r.set_index("fips")["rank"], x.set_index("fips")["failed_gates"])
    floor_y = 26  # the "excluded" band starts here, below the ranked range shown
    excluded_rows = {"Old inputs": 0, "Corrected": 0}
    lane_rows = {"Old inputs": 0, "Corrected": 0}
    fig, ax = plt.subplots(figsize=(11, 6.6))
    for (fips, name), color in zip(counties.items(), SERIES):
        ys, notes = [], []
        for label in ("Old inputs", "Corrected"):
            ranks, failed = runs[label]
            if fips in ranks.index:
                rk = int(ranks[fips])
                if rk <= 20:
                    ys.append(rk)
                else:  # ranks past 20 sit in a lane, one row each, labeled with the real rank
                    ys.append(21.8 + 1.3 * lane_rows[label])
                    lane_rows[label] += 1
                notes.append(f"#{rk:,}")
            else:
                ys.append(floor_y + 1.6 * excluded_rows[label])  # one row per excluded county, no overlap
                excluded_rows[label] += 1
                gate = failed[fips].split(";")[0].replace("hazard_percentile_max.nri_", "").replace("_score", "")
                notes.append(f"excluded ({gate.replace('_', ' ')} gate)")
        ax.plot([0, 1], ys, color=color, linewidth=2.5, marker="o", markersize=10)
        ax.text(-0.04, ys[0], f"{name}  {notes[0]}", ha="right", va="center", color=INK, fontsize=14)
        ax.text(1.04, ys[1], f"{notes[1]}  {name}", ha="left", va="center", color=INK, fontsize=14)
    ax.axhline(21.2, color=GRID, linewidth=1, linestyle=(0, (4, 4)))
    ax.axhline(floor_y - 1.2, color=GRID, linewidth=1, linestyle=(0, (4, 4)))
    ax.text(-0.85, 22.4, "below #20", ha="left", va="center", color=INK_2, fontsize=11)
    ax.set_ylim(floor_y + 1.6 * max(excluded_rows.values()) + 0.5, 0)
    ax.set_xlim(-0.9, 1.9)
    ax.set_xticks([0, 1], ["Old inputs", "Corrected inputs"])
    ax.set_yticks([1, 5, 10, 15, 20], ["#1", "#5", "#10", "#15", "#20"])
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("FEMA's dollar-loss scores had excluded real hubs", loc="left", color=INK)
    ax.text(0, -0.12, "Old: FEMA dollar-loss risk scores and state grid rates. Corrected: FEMA loss-rate percentiles "
            "and eGRID subregion rates.\nBalanced preset; everything else held at today's engine and table.",
            transform=ax.transAxes, color=INK_2, fontsize=12)
    save(fig, "corrections.png")


def grant_ranges(table, fips="53025"):
    """Grant's CO2 and energy cost under the supply and price cases in research/impact.md."""
    dry = impact(fips, cooling="dry", table=table)
    price = float(table.set_index("fips").loc[fips, "industrial_price_cents_kwh"])
    return {"facility_mwh": round(dry["facility_mwh"]),
            "co2_tonnes": {"bpa": round(dry["facility_mwh"] * BPA_CO2_LB_MWH / 2204.62),
                           "nwpp_table": round(dry["co2_tonnes"])},
            "energy_cost_musd": {"state_average": round(dry["facility_mwh"] * price * 10 / 1e6),
                                 "new_load_low": round(dry["facility_mwh"] * NEW_LOAD_USD_MWH[0] / 1e6),
                                 "new_load_high": round(dry["facility_mwh"] * NEW_LOAD_USD_MWH[1] / 1e6)}}


def energy_cost_musd(table, fips):
    dry = impact(fips, cooling="dry", table=table)
    return dry["facility_mwh"] * float(table.set_index("fips").loc[fips, "industrial_price_cents_kwh"]) * 10 / 1e6


def impact_compare(counties, featured="53025", baseline="51107"):
    """Three panels with their own axes: CO2 (dry), on-site water (evaporative), energy cost (dry).
    The featured county's CO2 and cost are drawn as ranges, not points."""
    table = pd.read_parquet(TABLE)
    fips = [*counties, baseline]
    names = [impact(f, table=table)["county"] for f in fips]
    rng = grant_ranges(table, featured)
    co2 = [impact(f, cooling="dry", table=table)["co2_tonnes"] / 1e3 for f in fips]
    water = [impact(f, cooling="evaporative", table=table)["water_million_gal"] for f in fips]
    cost = [energy_cost_musd(table, f) for f in fips]
    fig, axes = plt.subplots(1, 3, figsize=(19, 6.4))
    panels = ((axes[0], co2, "CO2, dry cooling", "thousand metric tons per year"),
              (axes[1], water, "On-site water, evaporative cooling", "million gallons per year"),
              (axes[2], cost, "Energy cost, dry cooling", "million dollars per year"))
    for k, (ax, values, title, unit) in enumerate(panels):
        y = list(range(len(fips)))[::-1]
        top = max(values + ([rng["co2_tonnes"]["nwpp_table"] / 1e3] if k == 0 else
                            [rng["energy_cost_musd"]["new_load_high"]] if k == 2 else []))
        for yi, f, v in zip(y, fips, values):
            if f == featured and k in (0, 2):
                lo, hi = ((rng["co2_tonnes"]["bpa"] / 1e3, rng["co2_tonnes"]["nwpp_table"] / 1e3) if k == 0 else
                          (rng["energy_cost_musd"]["new_load_low"], rng["energy_cost_musd"]["new_load_high"]))
                ax.barh(yi, hi - lo, left=lo, color=BLUE_RAMP[1], height=0.62)
                ax.plot([lo, hi], [yi, yi], "o", color=SERIES[0], markersize=9)
                ax.text(hi + top * 0.02, yi, f"{lo:,.0f} to {hi:,.0f}", va="center", color=INK, fontsize=14)
                if k == 2:  # the state-average price is a floor a new load won't get
                    floor = rng["energy_cost_musd"]["state_average"]
                    ax.plot([floor], [yi], "|", color=INK_2, markersize=22, markeredgewidth=2.5)
                    ax.text(floor - top * 0.02, yi, f"state avg {floor:,.0f}", ha="right", va="center",
                            color=INK_2, fontsize=11)
            else:
                ax.barh(yi, v, color=INK_3 if f == baseline else SERIES[0], height=0.62)
                ax.text(v + top * 0.02, yi, f"{v:,.0f}", va="center", color=INK, fontsize=14)
        ax.axvline(values[-1], color=INK_3, linewidth=1.2, linestyle=(0, (4, 4)))
        ax.set_yticks(y, names if k == 0 else [""] * len(names))
        ax.set_xlim(0, top * 1.35)
        ax.set_xlabel(unit)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(title, loc="left", color=INK)
        if k == 1:
            dry = impact(featured, cooling="dry", table=table)["water_million_gal"]
            ax.text(0, -0.2, f"{names[0]}'s plan uses dry cooling: {dry:,.1f} million gallons a year.",
                    transform=ax.transAxes, color=INK_2, fontsize=12)
    fig.suptitle("300 MW campus, load factor 0.8, against Loudoun County, VA (grey, dashed). Grant shown as a range: "
                 "CO2 from BPA's rate to the Northwest average; cost at BPA's new-load rate.",
                 x=0.01, ha="left", color=INK_2, fontsize=13, y=1.01)
    fig.tight_layout()
    save(fig, "impact.png")


def pick_story(df, conditions, pillars, counties):
    """How the pick changed: the seven-pillar ranking at the freeze tag, the same engine after the
    Massachusetts policy correction, and the eight-pillar engine with cost as its own pillar."""
    path = OUT / "freeze_balanced_ranks.csv"
    if not path.exists():
        sys.exit(f"missing {path}: the ranks from results/balanced.csv at tag {FREEZE_TAG}. Restore it with "
                 f"git show {FREEZE_TAG}:results/balanced.csv, keeping fips, county_name, state, rank, composite.")
    frozen = pd.read_csv(path, dtype={"fips": str}).set_index("fips")["rank"]
    seven = copy.deepcopy(pillars)
    seven["grid_infrastructure"] = pillars["grid_infrastructure"] + pillars["cost"]
    del seven["cost"]
    c7 = copy.deepcopy(conditions)
    w = {k: v for k, v in conditions["weights"].items() if k != "cost"}
    c7["weights"] = {k: v / sum(w.values()) for k, v in w.items()}
    corrected = rank(df, c7, seven)[0].set_index("fips")["rank"]
    now = rank(df, conditions, pillars)[0].set_index("fips")["rank"]
    stages = [("Seven pillars\n(freeze tag)", frozen), ("Seven pillars, MA\npolicy corrected", corrected),
              ("Cost as its\nown pillar", now)]
    fig, ax = plt.subplots(figsize=(13, 6.6))
    out = {}
    cap = 25  # ranks past this sit in a band at the bottom
    for i, ((fips, name), color) in enumerate(zip(counties.items(), SERIES)):
        ranks = [int(r[fips]) for _, r in stages]
        out[name] = ranks
        ys = [min(rk, cap + 2) for rk in ranks]
        ax.plot(range(3), ys, color=color, linewidth=2.5, marker="o", markersize=10)
        ax.text(-0.06, ys[0], f"{name}  #{ranks[0]}", ha="right", va="center", color=INK, fontsize=14)
        ax.text(2.06, ys[2], f"#{ranks[2]:,}  {name}", ha="left", va="center", color=INK, fontsize=14)
        below = i == 2  # the third line labels under its point so neighbors don't collide
        ax.text(1, ys[1] + (0.7 if below else -0.7), f"#{ranks[1]}", ha="center", va="top" if below else "bottom",
                color=INK_2, fontsize=12)
    ax.axhline(cap + 0.5, color=GRID, linewidth=1, linestyle=(0, (4, 4)))
    ax.text(2.0, cap + 1.2, "below #25", ha="center", color=INK_2, fontsize=11)
    ax.set_ylim(cap + 3.5, 0)
    ax.set_xlim(-1.1, 3.0)
    ax.set_xticks(range(3), [s for s, _ in stages])
    ax.set_yticks([1, 5, 10, 15, 20, 25], ["#1", "#5", "#10", "#15", "#20", "#25"])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("How the pick changed: balanced preset rank at each step", loc="left", color=INK)
    save(fig, "pick_story.png")
    return out


def horizon_2050(featured, baseline="51107"):
    """Cooling degree days and days above 95F, today and 2050 (RCP 8.5), two panels with their own axes."""
    d = pd.read_parquet(TABLE).set_index("fips")
    fips = [featured, baseline]
    names = [f"{d.loc[f, 'county_name']}, {d.loc[f, 'state']}" for f in fips]
    panels = (("Cooling degree days", "cdd_hist", "cdd_2050_rcp85", "{:,.0f}"),
              ("Days above 95°F", "days_above_95f_hist", "days_above_95f_2050_rcp85", "{:,.1f}"))
    today_c, later_c = BLUE_RAMP[2], BLUE_RAMP[5]  # one hue, light for today, dark for 2050
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    out = {}
    for ax, (title, now_col, later_col, fmt) in zip(axes, panels):
        now = [float(d.loc[f, now_col]) for f in fips]
        later = [float(d.loc[f, later_col]) for f in fips]
        out[title] = {n: {"today": round(a, 1), "2050": round(b, 1)} for n, a, b in zip(names, now, later)}
        x = range(len(fips))
        ax.bar([i - 0.19 for i in x], now, width=0.36, color=today_c, label="Today")
        ax.bar([i + 0.19 for i in x], later, width=0.36, color=later_c, label="2050, RCP 8.5")
        top = max(later)
        for i, (a, b) in enumerate(zip(now, later)):
            ax.text(i - 0.19, a + top * 0.015, fmt.format(a), ha="center", va="bottom", color=INK, fontsize=14)
            ax.text(i + 0.19, b + top * 0.015, fmt.format(b), ha="center", va="bottom", color=INK, fontsize=14)
        ax.set_xticks(list(x), names)
        ax.set_ylim(0, top * 1.18)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.set_title(title, loc="left", color=INK)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("Mid-century (CMRA, LOCA-downscaled CMIP5, 2036 to 2065) against the historical baseline",
                 x=0.01, ha="left", color=INK_2, fontsize=13, y=1.01)
    fig.tight_layout()
    save(fig, "horizon_2050.png")
    return out


def global_table(us_row="USA"):
    """Global country run: the top 10 plus the United States, from results/global_balanced.csv."""
    g = pd.read_csv(ROOT / "results/global_balanced.csv")
    report = json.loads((ROOT / "results/global_balanced_report.json").read_text())
    show = pd.concat([g.head(10), g[g.iso3 == us_row]])
    rows = [[int(r["rank"]), r.country, f"{r.composite:.1f}", f"{r.robustness:.0%}", "" if r.floor_ok else "fails"]
            for _, r in show.iterrows()]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_axis_off()
    t = ax.table(cellText=rows, colLabels=["Rank", "Country", "Composite", "Robustness", "Floor"], loc="center",
                 cellLoc="left", colLoc="left", colWidths=[0.1, 0.36, 0.17, 0.19, 0.14])
    t.auto_set_font_size(False)
    t.set_fontsize(15)
    t.scale(1, 1.7)
    for (row, col), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.8)
        cell.visible_edges = "B"
        if row == 0:
            cell.set_text_props(color=INK_2, weight="bold")
        elif row == len(rows):  # the United States row, set apart
            cell.set_text_props(color=INK, weight="bold")
    ax.set_title(f"Same engine, {report['counties']} countries: {report['passed']} pass the gates, "
                 f"{report['floor_ok']} pass the floor", loc="left", color=INK)
    save(fig, "global_table.png")
    us = g[g.iso3 == us_row].iloc[0]
    return {"countries": report["counties"], "passed": report["passed"], "floor_ok": report["floor_ok"],
            "pillars": report["pillars"], "top3": list(g.country.head(3)),
            "us": {"rank": int(us["rank"]), "of": len(g), "composite": round(float(us.composite), 1),
                   "floor_ok": bool(us.floor_ok), "pillar_climate_resilience": round(float(us.pillar_climate_resilience), 1)}}


def framework(conditions, report):
    """Decision pipeline: gates, percentiles, pillars, composite, floor, robustness."""
    w = report["weights_used"]
    steps = [
        ("Hard gates", f"{report['counties']:,} counties\n{report['passed']:,} pass\nnull never\nexcludes"),
        ("Percentiles", "each column\nranked nationally\n0 to 100, 100 best"),
        ("Pillars", "mean of columns\n" + "\n".join(f"{SHORT[p]} {v:.0%}" for p, v in w.items())),
        ("Composite", "weighted sum\nof pillar scores"),
        ("Floor rule", f"below the {conditions['pillar_floor_percentile']}th pctl\non any pillar:\nranks after\n"
                       f"every county\nthat isn't\n({report['floor_ok']:,} pass)"),
        ("Robustness", f"{conditions['robustness']['samples']:,} weight\ndraws: share\nin the top "
                       f"{conditions['robustness']['top_n']}"),
    ]
    fig, ax = plt.subplots(figsize=(17, 5.8))
    ax.set_axis_off()
    ax.set_xlim(0, len(steps))
    ax.set_ylim(0, 1)
    for i, (title, body) in enumerate(steps):
        ax.add_patch(plt.Rectangle((i + 0.06, 0.06), 0.82, 0.86, facecolor=SURFACE, edgecolor=SERIES[0], linewidth=2))
        ax.text(i + 0.47, 0.83, title, ha="center", va="center", fontsize=17, weight="bold", color=INK)
        ax.text(i + 0.47, 0.44, body, ha="center", va="center", fontsize=13, color=INK_2, linespacing=1.35)
        if i < len(steps) - 1:
            ax.annotate("", (i + 1.06, 0.5), (i + 0.88, 0.5), arrowprops={"arrowstyle": "-|>", "color": INK_2, "lw": 1.6})
    ax.set_title(f"Conditions file in, ranked shortlist out ({conditions['name']} preset)", loc="left", color=INK)
    save(fig, "framework.png")


def rank_or_gate(ranked, excluded, fips):
    if fips in set(ranked["fips"]):
        return int(ranked.set_index("fips").loc[fips, "rank"])
    return "excluded: " + excluded.set_index("fips").loc[fips, "failed_gates"]


def weight_sensitivity(df, conditions, pillars, featured, top_n=10):
    """Equal weights, and robustness from uniformly random weightings (Dirichlet alpha 1 per pillar)."""
    eq = copy.deepcopy(conditions)
    eq["weights"] = {k: 1 / len(conditions["weights"]) for k in conditions["weights"]}
    base = rank(df, conditions, pillars)[0]
    er = rank(df, eq, pillars)[0]
    uni = copy.deepcopy(eq)
    uni["robustness"] = {"samples": 5000, "concentration": 1, "top_n": top_n, "seed": 0}
    ur = rank(df, uni, pillars)[0].sort_values("robustness", ascending=False)
    k = len(conditions["weights"])
    return {"equal_weights_featured_rank": int(er.set_index("fips").loc[featured, "rank"]),
            "equal_weights_top10_overlap": len(set(er.fips.head(10)) & set(base.fips.head(10))),
            "uniform_weightings_top10_share": {f"{n}, {s}": round(float(x), 3) for n, s, x in
                                               zip(ur.county_name.head(5), ur.state.head(5), ur.robustness.head(5))},
            "default_weight_sd": {p: round((w * (1 - w) / (conditions["robustness"]["concentration"] * k + 1)) ** 0.5, 3)
                                  for p, w in conditions["weights"].items()}}


def facts(df, conditions, pillars, ranked, excluded, report, featured, story, extra):
    """Every number the deck cites, written to facts.json so speaker notes can point at one committed file."""
    d = df.set_index("fips")
    name = lambda f: f"{d.loc[f, 'county_name']}, {d.loc[f, 'state']}"  # noqa: E731
    out = {"balanced": {k: report[k] for k in ("counties", "passed", "floor_ok", "moratorium_state_active_ranked")},
           "top10": [{"rank": int(r["rank"]), "fips": r.fips, "county": f"{r.county_name}, {r.state}",
                      "composite": round(r.composite, 1), "robustness": round(r.robustness, 3),
                      "state_moratorium": bool(r.moratorium_state_active)} for _, r in ranked.head(10).iterrows()]}
    out["gap_first_to_second"] = round(ranked.composite.iloc[0] - ranked.composite.iloc[1], 1)
    e = explain(df, conditions, pillars, featured, result=(ranked, excluded, report))
    out["featured"] = {"fips": featured, "county": name(featured), "rank": e["rank"], "composite": round(e["composite"], 1),
                       "robustness": e["robustness"], "coverage": round(e["coverage"], 3), "warnings": e["warnings"],
                       "facts": e["facts"], "top_reasons": e["top_reasons"],
                       "pillars": {p: round(v["score"], 1) for p, v in e["pillars"].items()},
                       "horizon_2050_raw": e["horizon_2050_raw"]}
    old_r, old_x, old_rep = rank(old_inputs(df), conditions, pillars)
    out["corrections"] = {"old_inputs": {"passed": old_rep["passed"], "floor_ok": old_rep["floor_ok"],
                                         "top10": [f"{n}, {s}" for n, s in zip(old_r.county_name.head(10), old_r.state.head(10))]},
                          "counties": {name(f): {"old": rank_or_gate(old_r, old_x, f), "corrected": rank_or_gate(ranked, excluded, f)}
                                       for f in dict.fromkeys((featured, "25003", "50003", "19153", "48113", "04013"))},
                          "vermont_grid": {"state_co2_lb_mwh": round(float(d.loc["50003", "grid_co2_lb_mwh_state"]), 1),
                                           "state_renewable_share": round(float(d.loc["50003", "grid_renewable_share_state"]), 3),
                                           "subregion": d.loc["50003", "grid_subregion"],
                                           "subregion_co2_lb_mwh": round(float(d.loc["50003", "grid_co2_lb_mwh"]), 1),
                                           "subregion_renewable_share": round(float(d.loc["50003", "grid_renewable_share"]), 3)}}
    no_dc = copy.deepcopy(pillars)
    no_dc["grid_infrastructure"] = [m for m in pillars["grid_infrastructure"] if m["column"] != "dc_existing_count"]
    nd_r, nd_x, _ = rank(df, conditions, no_dc)
    out["validation_hubs"] = {name(f): {"rank": rank_or_gate(ranked, excluded, f),
                                        "rank_without_dc_existing_count": rank_or_gate(nd_r, nd_x, f),
                                        "dc_existing_count": int(d.loc[f, "dc_existing_count"])}
                              for f in ("53025", "42079")}
    out["limitations"] = {
        "homer_city_indiana_pa_fiber_share": round(float(d.loc["42063", "fiber_share_locations"]), 4),
        "fiber_gate": conditions["gates"]["min_fiber_share_locations"],
        "indiana_pa_coal_retired_mw": float(d.loc["42063", "coal_retired_mw"]),
        "counties_with_zero_retired_coal": int((df.coal_retired_mw == 0).sum()),
        "counties_at_population_peak": int((df.pop_change_pct_since_peak == 0).sum()),
        "knox_il_rank": rank_or_gate(ranked, excluded, "17095"),
        "knox_il_pop_change_pct_since_peak": round(float(d.loc["17095", "pop_change_pct_since_peak"]), 1),
        "knox_il_unemployment_rate_pct_2023": float(d.loc["17095", "unemployment_rate_pct_2023"]),
        "knox_il_pillar_community": round(float(ranked.set_index("fips").loc["17095", "pillar_community"]), 1),
        "nwpp_co2_lb_mwh": round(float(d.loc["53025", "grid_co2_lb_mwh"]), 1),
        "coverage_top10": [round(float(c), 3) for c in ranked.coverage.head(10)],
        "scored_columns_present": int(sum(1 for ms in pillars.values() for m in ms if m["column"] in df.columns)),
        "scored_columns_mapped": int(sum(len(ms) for ms in pillars.values())),
        "loudoun_va": rank_or_gate(ranked, excluded, "51107"),
        "featured_plant_capacity_mw_100km": round(float(d.loc[featured, "plant_capacity_mw_100km"])),
    }
    out["presets"] = {}
    for preset in ("balanced", "speed_to_power", "sustainability_first"):
        c = load_yaml(ROOT / f"engine/conditions/{preset}.yaml")
        r, _, rep = rank(df, c, pillars)
        out["presets"][preset] = {"passed": rep["passed"], "floor_ok": rep["floor_ok"], "floor": c["pillar_floor_percentile"],
                                  "top3": [f"{n}, {s}" for n, s in zip(r.county_name.head(3), r.state.head(3))]}
    table = pd.read_parquet(TABLE)
    out["impact"] = {}
    for f in dict.fromkeys((featured, "53075", "47181", "25003", "51107")):
        dry, evap = impact(f, cooling="dry", table=table), impact(f, cooling="evaporative", table=table)
        out["impact"][dry["county"]] = {"co2_tonnes_dry": round(dry["co2_tonnes"]), "water_million_gal_evap": round(evap["water_million_gal"], 1),
                                        "water_million_gal_dry": round(dry["water_million_gal"], 1)}
    out["pick_story"] = {"stages": ["seven pillars at the freeze tag", "seven pillars, Massachusetts policy corrected",
                                    "eight pillars with cost"], "ranks": story}
    out["weights"] = {"balanced": conditions["weights"], **weight_sensitivity(df, conditions, pillars, featured)}
    out["grant_ranges"] = grant_ranges(table, featured)
    out["energy_cost_musd_state_average"] = {impact(f, table=table)["county"]: round(energy_cost_musd(table, f))
                                             for f in (featured, "53075", "47181", "25003", "51107")}
    out.update(extra)
    (OUT / "facts.json").write_text(json.dumps(out, indent=1, default=str))
    print(OUT / "facts.json")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--featured", default="53025", help="5-digit fips of the featured county")
    args = p.parse_args()
    conditions = load_yaml(ROOT / "engine/conditions/balanced.yaml")
    pillars = load_yaml(ROOT / "engine/pillars.yaml")
    df, _ = load_features(TABLE)
    ranked, excluded, report = rank(df, conditions, pillars)
    committed = pd.read_csv(ROOT / "results/balanced.csv", dtype={"fips": str})
    if committed["fips"].head(10).tolist() != ranked["fips"].head(10).tolist():
        sys.exit("results/balanced.csv is stale against the table; regenerate it before the figures")
    county_map(ranked, args.featured)
    top10_table(ranked)
    pillar_bars(ranked, args.featured, conditions["weights"], conditions.get("pillar_floor_exempt") or [])
    names = (df["county_name"] + ", " + df["state"]).set_axis(df["fips"])
    shown = list(dict.fromkeys([args.featured, "19153", "48113"]))[:3]  # counties the dollar-loss scores gated out
    corrections(df, conditions, pillars, {f: names[f] for f in shown})
    story = pick_story(df, conditions, pillars, {f: names[f] for f in list(dict.fromkeys([args.featured, "25003", "53075"]))[:3]})
    impact_compare([args.featured, "53075", "47181", "25003"], featured=args.featured)
    framework(conditions, report)
    extra = {"horizon_2050_figure": horizon_2050(args.featured), "global": global_table()}
    facts(df, conditions, pillars, ranked, excluded, report, args.featured, story, extra)


if __name__ == "__main__":
    main()
