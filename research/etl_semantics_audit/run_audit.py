"""Semantic audit of the queue and FracTracker definitions. Read-only for production artifacts.

Usage (from the repo root): python research/etl_semantics_audit/run_audit.py

Inputs: data/raw/ (main's cached downloads), data/processed/county_features.parquet (the frozen
committed table), and, optionally, an earlier FracTracker fetch in
data/raw/fractracker_local_20261003/ for the cross-fetch check (skipped when absent).

The queue correction (clean generation excluding storage, delivered capacity by online date) is
now production. The ranking experiments compare pillar mappings on the same committed table:
legacy (the pre-correction columns), each correction alone, and corrected (production). Two
harness checks run first: the corrected mapping must reproduce results/ byte for byte, and the
legacy mapping must reproduce results/ at LEGACY_COMMIT byte for byte when git history is there.

Writes the compact research/etl_semantics_audit/audit_summary.json (committed) and full CSV
tables under research/etl_semantics_audit/outputs/ (gitignored). Rankings live in a temporary
directory. Production columns, engine/pillars.yaml, conditions, and results/ are not touched.
"""
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import yaml
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from etl.adapters.fractracker import _facility_fips  # noqa: E402
from etl.adapters.lbnl_queue_alt import CLEAN_GEN, STORAGE, clean_generation_mw, placed_queue  # noqa: E402
from etl.fips import EXCLUDED_STATE_FIPS, build_lookup, load_tiger, to_fips  # noqa: E402
from etl.schema import CLEAN_SOURCES  # noqa: E402

RAW = ROOT / "data/raw"
LOCAL_FT = RAW / "fractracker_local_20261003"
TABLE = ROOT / "data/processed/county_features.parquet"
MANIFEST = ROOT / "data/processed/county_features.manifest.json"
OUT = Path(__file__).parent / "outputs"
SUMMARY = Path(__file__).parent / "audit_summary.json"
LEGACY_COMMIT = "c4c41b7"  # main before the queue correction
LEGACY = {"queue_active_mw_clean_excl_storage": "queue_active_mw_clean",
          "queue_operational_mw_online_5y": "queue_operational_mw_5y"}
PRESETS = ["balanced", "speed_to_power", "sustainability_first"]
WATCH = {"53025": "Grant County, WA", "51107": "Loudoun County, VA"}
AS_OF = pd.Timestamp("2026-10-03")
WINDOW = (pd.Timestamp("2021-01-01"), pd.Timestamp("2025-12-31"))
ALL_STORAGE = STORAGE | {"Other Storage"}


def write(df, name):
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / name, index=False)
    return df


# --------------------------------------------------------------------------- queue

def main_clean_mask(q):
    """Main's rule (etl/adapters/lbnl_queue.py): every '+' component of type_clean is in CLEAN_SOURCES."""
    return q.type_clean.map(lambda t: set(str(t).lower().split("+")) <= CLEAN_SOURCES)


def main_operational_mask(q):
    """Main's rule: operational and q_year >= 2019, or q_year missing and on_date >= 2021-01-01."""
    online = pd.to_datetime(q.on_date, errors="coerce") >= "2021-01-01"
    return (q.q_status == "operational") & ((q.q_year >= 2019) | (q.q_year.isna() & online))


def online_date(q):
    on, prop = pd.to_datetime(q.on_date, errors="coerce"), pd.to_datetime(q.prop_date, errors="coerce")
    return on.fillna(prop), on.isna() & prop.notna()


def queue_audit(table):
    q, _ = placed_queue(RAW)
    res = {}
    a = q[q.q_status == "active"].copy()
    a["main_clean_mw"] = a.mw_1.where(main_clean_mask(a), 0).fillna(0)
    a["excl_storage_mw"] = clean_generation_mw(a)
    a["diff_mw"] = a.main_clean_mw - a.excl_storage_mw
    tech = (a.groupby("type_clean").agg(projects=("diff_mw", "size"), main_clean_mw=("main_clean_mw", "sum"),
                                         excl_storage_mw=("excl_storage_mw", "sum"), diff_mw=("diff_mw", "sum"))
            .query("diff_mw != 0").sort_values("diff_mw", ascending=False).reset_index())
    write(tech.round(1), "queue_clean_by_technology.csv")

    standalone = a[a.type_clean.isin(ALL_STORAGE | {"Battery+Other Storage"})]
    hyb_storage_first = a[a.type_clean.str.contains(r"\+", na=False) & a.type_1.isin(ALL_STORAGE)
                          & main_clean_mask(a)]
    hyb_dropped = a[~main_clean_mask(a) & (a.excl_storage_mw > 0)]
    hyb = a[a.type_clean.str.contains(r"\+", na=False)]
    res["clean"] = {
        "active_projects": len(a),
        "main_clean_gw": a.main_clean_mw.sum() / 1e3, "excl_storage_gw": a.excl_storage_mw.sum() / 1e3,
        "standalone_storage_counted_as_clean_gw": standalone.main_clean_mw.sum() / 1e3,
        "standalone_storage_projects": len(standalone),
        "standalone_storage_counties": standalone.fips.nunique(),
        "hybrids_active": len(hyb),
        "hybrids_type1_is_storage": len(hyb_storage_first),
        "hybrids_type1_is_storage_gw_counted_clean_by_main": hyb_storage_first.mw_1.sum() / 1e3,
        "hybrids_type1_is_storage_with_mw_for_generation_component": int(
            sum(hyb_storage_first[f"mw_{i}"].where(hyb_storage_first[f"type_{i}"].isin(CLEAN_GEN)).notna().sum()
                for i in (2, 3))),
        "hybrids_with_nonclean_component_dropped_by_main": len(hyb_dropped),
        "hybrids_with_nonclean_component_clean_gw_dropped": hyb_dropped.excl_storage_mw.sum() / 1e3,
        "solar_battery_type1_solar_mw2_filled": int(((a.type_clean == "Solar+Battery") & (a.type_1 == "Solar")
                                                      & a.mw_2.notna()).sum()),
        "solar_battery_type1_solar": int(((a.type_clean == "Solar+Battery") & (a.type_1 == "Solar")).sum()),
    }
    t = table.set_index("fips")
    d = (t.queue_active_mw_clean - t.queue_active_mw_clean_excl_storage)
    res["clean"]["counties_differing"] = int((d.abs() > 1e-6).sum())
    res["clean"]["counties_higher_in_main"] = int((d > 1e-6).sum())
    res["clean"]["counties_lower_in_main"] = int((d < -1e-6).sum())
    res["clean"]["counties_with_clean_mw_only_from_storage"] = int(
        ((t.queue_active_mw_clean > 0) & (t.queue_active_mw_clean_excl_storage == 0)).sum())
    top = (pd.DataFrame({"fips": d.index, "county": t.county_name + ", " + t.state,
                         "queue_active_mw_clean": t.queue_active_mw_clean,
                         "queue_active_mw_clean_excl_storage": t.queue_active_mw_clean_excl_storage,
                         "queue_active_mw_storage_standalone": t.queue_active_mw_storage_standalone,
                         "difference_mw": d}).loc[d.abs().sort_values(ascending=False).index].head(25))
    write(top.round(1), "queue_clean_top25_county_differences.csv")

    op = q[q.q_status == "operational"].copy()
    op["online"], op["fallback"] = online_date(op)
    op["in_main"] = main_operational_mask(op)
    op["in_online5y"] = op.online.between(*WINDOW)
    op["reason"] = np.select(
        [op.in_main & op.in_online5y, op.in_main & op.online.isna(), op.in_main & (op.online < WINDOW[0]),
         op.in_main, op.in_online5y & (op.q_year < 2019)],
        ["both", "main only: no online or proposed date", "main only: online before 2021",
         "main only: other", "online-date only: entered queue before 2019"], default="neither")
    rec = (op[op.reason != "neither"].groupby("reason").agg(projects=("mw_1", "size"), mw=("mw_1", "sum"))
           .reset_index())
    write(rec.round(1), "queue_operational_reconciliation.csv")
    entry = (op[op.in_online5y].groupby("q_year").agg(projects=("mw_1", "size"), mw=("mw_1", "sum")).reset_index())
    write(entry.round(1), "queue_online_5y_by_entry_year.csv")
    w = op[op.in_online5y]
    res["operational"] = {
        "main_gw": op[op.in_main].mw_1.sum() / 1e3, "online5y_gw": w.mw_1.sum() / 1e3,
        "main_projects": int(op.in_main.sum()), "online5y_projects": len(w),
        "online5y_projects_dated_by_prop_date": int(w.fallback.sum()),
        "online5y_gw_dated_by_prop_date": w[w.fallback].mw_1.sum() / 1e3,
        "operational_projects_with_no_on_date": int(pd.to_datetime(op.on_date, errors="coerce").isna().sum()),
        "operational_projects_with_no_on_or_prop_date": int(op.online.isna().sum()),
        "online5y_entered_queue_before_2019_gw": w[w.q_year < 2019].mw_1.sum() / 1e3,
        "online5y_median_years_in_queue": float((w.online - pd.to_datetime(w.q_date, errors="coerce")).dt.days.median() / 365.25),
    }
    d2 = t.queue_operational_mw_5y - t.queue_operational_mw_online_5y
    res["operational"].update(counties_differing=int((d2.abs() > 1e-6).sum()),
                              counties_zero_in_main_positive_online=int(((t.queue_operational_mw_5y == 0)
                                                                         & (t.queue_operational_mw_online_5y > 0)).sum()),
                              counties_positive_in_main_zero_online=int(((t.queue_operational_mw_5y > 0)
                                                                         & (t.queue_operational_mw_online_5y == 0)).sum()))
    top2 = (pd.DataFrame({"fips": d2.index, "county": t.county_name + ", " + t.state,
                          "queue_operational_mw_5y": t.queue_operational_mw_5y,
                          "queue_operational_mw_online_5y": t.queue_operational_mw_online_5y,
                          "fallback_share": t.queue_operational_online_date_fallback_share, "difference_mw": d2})
            .loc[d2.abs().sort_values(ascending=False).index].head(25))
    write(top2.round(2), "queue_operational_top25_county_differences.csv")
    reg = (op.assign(no_on=pd.to_datetime(op.on_date, errors="coerce").isna(), no_any=op.online.isna())
           .groupby(op.region.fillna("unknown"))
           .agg(operational_projects=("mw_1", "size"), share_missing_on_date=("no_on", "mean"),
                share_missing_on_and_prop_date=("no_any", "mean"), online5y_projects=("in_online5y", "sum"),
                online5y_dated_by_prop_date=("fallback", lambda s: int((s & op.loc[s.index, "in_online5y"]).sum())))
           .reset_index().sort_values("share_missing_on_date", ascending=False))
    write(reg.round(3), "queue_online_date_by_region.csv")
    return res


# --------------------------------------------------------------------------- rankings

def mapping(swap):
    """engine/pillars.yaml with the scored columns in swap (corrected -> legacy) put back."""
    pillars = copy.deepcopy(yaml.safe_load((ROOT / "engine/pillars.yaml").read_text()))
    for metrics in pillars.values():
        for m in metrics:
            m["column"] = swap.get(m["column"], m["column"])
    return pillars


def run_rankings(tmp):
    variants = {
        "legacy": LEGACY,
        "clean_excl_storage_only": {"queue_operational_mw_online_5y": "queue_operational_mw_5y"},
        "operational_online_date_only": {"queue_active_mw_clean_excl_storage": "queue_active_mw_clean"},
        "corrected": {},
    }
    dirs = {}
    for name, swap in variants.items():
        pfile = Path(tmp) / f"pillars_{name}.yaml"
        pfile.write_text(yaml.safe_dump(mapping(swap), sort_keys=False))
        outdir = Path(tmp) / name
        outdir.mkdir()
        for p in PRESETS:
            subprocess.run([sys.executable, "-m", "engine", "rank", "--conditions", f"engine/conditions/{p}.yaml",
                            "--features", str(TABLE), "--pillars", str(pfile), "--out", str(outdir / f"{p}.csv")],
                           cwd=ROOT, check=True, capture_output=True)
        dirs[name] = outdir
    checks = {}
    for p in PRESETS:
        for suffix in (".csv", "_excluded.csv", "_report.json"):
            f = f"{p}{suffix}"
            assert (dirs["corrected"] / f).read_bytes() == (ROOT / "results" / f).read_bytes(), \
                f"corrected mapping does not reproduce results/{f}"
            old = subprocess.run(["git", "show", f"{LEGACY_COMMIT}:results/{f}"], cwd=ROOT, capture_output=True)
            if old.returncode == 0:
                assert (dirs["legacy"] / f).read_bytes() == old.stdout, f"legacy mapping does not reproduce {f}"
                checks[f] = "legacy reproduces " + LEGACY_COMMIT
    return dirs, {"corrected_reproduces_results": True,
                  "legacy_reproduces_pre_correction_results": len(checks) == 9}


def summarize(dirs):
    rows, moves, watch = [], [], []
    for p in PRESETS:
        base = pd.read_csv(dirs["legacy"] / f"{p}.csv", dtype={"fips": str})
        brep = json.loads((dirs["legacy"] / f"{p}_report.json").read_text())
        for v, d in dirs.items():
            r = pd.read_csv(d / f"{p}.csv", dtype={"fips": str})
            rep = json.loads((d / f"{p}_report.json").read_text())
            ex = pd.read_csv(d / f"{p}_excluded.csv", dtype={"fips": str})
            m = base.merge(r, on="fips", suffixes=("_b", "_v"))
            top10_b, top10_v = base.head(10).fips.tolist(), r.head(10).fips.tolist()
            top25_b, top25_v = set(base.head(25).fips), set(r.head(25).fips)
            rows.append({
                "preset": p, "variant": v, "passed": rep["passed"], "floor_ok": rep["floor_ok"],
                "gate_failures_equal_legacy": rep["gate_failures"] == brep["gate_failures"],
                "winner": f"{r.iloc[0].county_name}, {r.iloc[0].state}", "winner_composite": r.iloc[0].composite,
                "top10_same_set": set(top10_b) == set(top10_v), "top10_same_order": top10_b == top10_v,
                "top10": "; ".join(f"{x.county_name}, {x.state}" for x in r.head(10).itertuples()),
                "entered_top25": "; ".join(sorted(f"{x.county_name}, {x.state}" for x in r[r.fips.isin(top25_v - top25_b)].itertuples())),
                "left_top25": "; ".join(sorted(f"{x.county_name}, {x.state}" for x in base[base.fips.isin(top25_b - top25_v)].itertuples())),
                "spearman_rank": float(m["rank_b"].corr(m["rank_v"], method="spearman")),
                "mean_abs_composite_change": float((m.composite_v - m.composite_b).abs().mean()),
                "max_abs_composite_change": float((m.composite_v - m.composite_b).abs().max()),
                "mean_abs_energy_carbon_change": float((m.pillar_energy_carbon_v - m.pillar_energy_carbon_b).abs().mean()),
                "max_abs_energy_carbon_change": float((m.pillar_energy_carbon_v - m.pillar_energy_carbon_b).abs().max()),
                "mean_abs_grid_infrastructure_change": float((m.pillar_grid_infrastructure_v - m.pillar_grid_infrastructure_b).abs().mean()),
                "mean_abs_robustness_change": float((m.robustness_v - m.robustness_b).abs().mean()),
            })
            for f, label in WATCH.items():
                hit = r[r.fips == f]
                if len(hit):
                    x = hit.iloc[0]
                    watch.append({"preset": p, "variant": v, "county": label, "status": "ranked", "rank": int(x["rank"]),
                                  "composite": x.composite, "pillar_energy_carbon": x.pillar_energy_carbon,
                                  "pillar_grid_infrastructure": x.pillar_grid_infrastructure,
                                  "robustness": x.robustness})
                else:
                    e = ex[ex.fips == f]
                    watch.append({"preset": p, "variant": v, "county": label, "status": "excluded by gates",
                                  "failed_gates": e.failed_gates.iloc[0] if len(e) else ""})
            if v != "legacy":
                big = m.assign(rank_change=m.rank_b - m.rank_v).loc[lambda x: (x.rank_b <= 50) | (x.rank_v <= 50)]
                for x in big.sort_values("rank_v").itertuples():
                    if x.rank_change:
                        moves.append({"preset": p, "variant": v, "fips": x.fips, "county": f"{x.county_name_b}, {x.state_b}",
                                      "rank_legacy": x.rank_b, "rank_variant": x.rank_v,
                                      "composite_legacy": x.composite_b, "composite_variant": x.composite_v})
    write(pd.DataFrame(rows), "ranking_experiment_summary.csv")
    write(pd.DataFrame(watch), "ranking_experiment_watch_counties.csv")
    write(pd.DataFrame(moves), "ranking_experiment_top50_moves.csv")
    return rows, watch


# --------------------------------------------------------------------------- FracTracker

def parse_mw(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).replace(",", "").strip()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return np.nan
    return (nums[0] + nums[1]) / 2 if len(nums) >= 2 and "-" in s else nums[0]


def local_dedupe(f):
    """Prior local rule: drop delete_dup rows, then same normalized name + state + status within 1 km."""
    f = f[f.delete_dup.isna()].copy()
    f["_key"] = f.facility_name.fillna("").str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    drop = set()
    for _, g in f[f._key != ""].groupby(["_key", "state", "status"]):
        g = g.sort_values("facility_id")
        rows = list(g.itertuples())
        for i, a in enumerate(rows):
            if a.Index in drop:
                continue
            for b in rows[i + 1:]:
                p = np.pi / 180
                h = (np.sin((b.lat - a.lat) * p / 2) ** 2
                     + np.cos(a.lat * p) * np.cos(b.lat * p) * np.sin((b.long - a.long) * p / 2) ** 2)
                if 12742 * np.arcsin(np.sqrt(h)) <= 1.0:
                    drop.add(b.Index)
    return f.drop(index=list(drop)).drop(columns="_key"), drop


def facility_assignments(ft, tiger, counties):
    """Per-facility FIPS under main's rule (name first, then point) and the prior local rule (point first)."""
    lookup = build_lookup(tiger)
    by_name = pd.Series([to_fips(c, s, lookup) for c, s in zip(ft.county, ft.state)], index=ft.index)
    pts = gpd.GeoDataFrame(index=ft.index, geometry=gpd.points_from_xy(ft.long, ft.lat), crs=4326).to_crs(counties.crs)
    hit = gpd.sjoin(pts, counties[["GEOID", "geometry"]], predicate="within")
    by_point = hit[~hit.index.duplicated()].GEOID.reindex(ft.index)
    valid = set(tiger.GEOID)
    main = _facility_fips(ft, RAW, tiger)
    local = by_point.where(by_point.isin(valid)).fillna(by_name.where(by_name.isin(valid)))
    return main, local, by_name, by_point


def check_reproduces(ft, table):
    """The main-rule reimplementation must match the committed table's facility columns exactly."""
    t = table.set_index("fips")
    existing, proposed = {"Operating", "Expanding"}, {"Proposed", "Approved/Permitted/Under construction", "Pre-proposal"}
    f = ft[ft.fips_main.notna()]
    got = {"dc_existing_count": f[f.status.isin(existing)].groupby("fips_main").size(),
           "dc_proposed_count": f[f.status.isin(proposed)].groupby("fips_main").size(),
           "dc_pushback_count": f[f.pushback].groupby("fips_main").size()}
    for col, s in got.items():
        s = s.reindex(t.index, fill_value=0)
        assert (s.values == t[col].astype(int).values).all(), f"main-rule reimplementation differs on {col}"


def fractracker_audit():
    tiger = load_tiger(RAW)
    counties = gpd.read_file(RAW / "tiger/cb_2024_us_county_500k.zip")
    counties = counties[~counties.STATEFP.isin(EXCLUDED_STATE_FIPS)]
    res = {}

    # Moratoria: both definitions on both fetches (main's fetch only when the earlier one is absent).
    have_local = (LOCAL_FT / "ft_moratoria_2.csv").exists()
    main_m = pd.read_csv(RAW / "fractracker/ft_moratoria.csv", dtype=str)
    local_m = (pd.read_csv(LOCAL_FT / "ft_moratoria_2.csv", dtype=str) if have_local
               else main_m[main_m.level_ == "county"].copy())
    main_county = main_m[main_m.level_ == "county"]

    def flags_local(d):
        s, c = d.status.str.lower(), d.category.str.lower()
        return set(d[(s == "active") & c.isin(["moratorium", "ban"])].GEOID.str.zfill(5))

    def flags_main(d):
        ended = pd.to_datetime(d.end_date, errors="coerce") < AS_OF
        d = d[d.category.isin(["moratorium", "ban"]) & ~ended]
        return set(d[d.status == "active"].GEOID)

    res["moratorium_matrix"] = {"local_rule_local_fetch": len(flags_local(local_m)) if have_local else None,
                                "local_rule_main_fetch": len(flags_local(main_county)),
                                "main_rule_local_fetch": len(flags_main(local_m)) if have_local else None,
                                "main_rule_main_fetch": len(flags_main(main_county))}
    key = ["GEOID", "entry_id"]
    cmp_cols = ["status", "category", "effective_date", "end_date"]
    j = local_m[key + cmp_cols].merge(main_county[key + cmp_cols], on=key, how="outer", suffixes=("_l", "_m"),
                                      indicator=True)
    res["moratorium_county_rows_changed_between_fetches"] = None if not have_local else int(
        ((j._merge != "both") | j.apply(lambda r: any(str(r[c + "_l"]) != str(r[c + "_m"]) for c in cmp_cols), axis=1)).sum())
    diff_geoids = flags_local(main_county) ^ flags_main(main_county)
    names = tiger.set_index("GEOID")
    rows = []
    for g in sorted(diff_geoids):
        for r in main_m[(main_m.GEOID == g) | (main_m.GEOID.str[:5] == g)].itertuples():
            ended = pd.to_datetime(r.end_date, errors="coerce")
            countywide = r.level_ == "county"
            blocking = r.category in ("moratorium", "ban")
            rows.append({
                "fips": g, "county": f"{names.NAMELSAD.get(g, '?')}, {names.STUSPS.get(g, '?')}",
                "source_record": f"FracTracker DataCenterMoratoriums entry {r.entry_id}: {r.entry_name}",
                "jurisdiction_level": r.level_, "countywide": countywide, "category": r.category, "status": r.status,
                "effective_date": r.effective_date, "end_date": r.end_date,
                "end_date_passed_as_of_2026_10_03": bool(pd.notna(ended) and ended < AS_OF),
                "flagged_by_prior_local_rule": g in flags_local(main_county) and countywide,
                "flagged_by_main_rule": g in flags_main(main_county) and countywide,
                "should_trigger_county_hard_gate": bool(countywide and blocking and r.status == "active"
                                                        and not (pd.notna(ended) and ended < AS_OF)),
                "notes": r.notes, "source_urls": r.source_urls,
            })
    write(pd.DataFrame(rows), "fractracker_moratorium_differences.csv")
    muni = main_m[main_m.level_ == "municipality"]
    res["municipal_rows"] = int(len(muni))

    # Facilities: source change vs dedupe vs geography vs parsing.
    mf = pd.read_csv(RAW / "fractracker/ft_all.csv", dtype=str)
    lf = pd.read_csv(LOCAL_FT / "ft_facilities.csv", dtype=str) if have_local else mf.copy()
    fields = ["facility_name", "state", "county", "lat", "long", "status", "mw", "community_pushback", "delete_dup"]
    jj = lf[["facility_id"] + fields].merge(mf[["facility_id"] + fields], on="facility_id", how="outer",
                                            suffixes=("_l", "_m"), indicator=True)
    changed = jj[(jj._merge != "both") | jj.apply(lambda r: any(str(r[c + "_l"]) != str(r[c + "_m"]) for c in fields),
                                                  axis=1)]
    res["facility_records_changed_between_fetches"] = int(len(changed)) if have_local else None
    write(changed, "fractracker_facility_source_changes.csv")

    ft = mf.copy()
    ft["lat"], ft["long"] = pd.to_numeric(ft.lat, errors="coerce"), pd.to_numeric(ft.long, errors="coerce")
    ft = ft[~ft.state.fillna("").str.strip().isin(["AK", "HI", "PR"])]  # "CO " has a trailing space
    main_fips, local_fips, by_name, by_point = facility_assignments(ft, tiger, counties)
    kept, dropped = local_dedupe(ft)
    ft["fips_main"], ft["fips_local"] = main_fips, local_fips
    ft["local_dedupe_drop"] = ft.index.isin(dropped) | ft.delete_dup.notna()
    ft["mw_main"] = pd.to_numeric(ft.mw, errors="coerce").fillna(0.0)
    ft["mw_parsed"] = ft.mw.map(parse_mw)
    ft["pushback"] = ft.community_pushback.fillna("").str.lower().eq("yes")
    check_reproduces(ft, pd.read_parquet(TABLE))
    ft["cause"] = np.select(
        [ft.local_dedupe_drop & ft.fips_main.notna(), ft.fips_main.fillna("") != ft.fips_local.fillna("")],
        ["deduplication (prior local rule drops it)", "geographic matching (name-first vs point-first)"], default="")
    geo = ft[ft.cause != ""][["facility_id", "facility_name", "state", "county", "city", "status", "lat", "long",
                             "fips_main", "fips_local", "cause"]]
    write(geo, "fractracker_facility_assignment_differences.csv")
    existing, proposed = {"Operating", "Expanding"}, {"Proposed", "Approved/Permitted/Under construction", "Pre-proposal"}

    def county_counts(fcol, df):
        df = df[df[fcol].notna()]
        return pd.DataFrame({
            "existing": df[df.status.isin(existing)].groupby(fcol).size(),
            "proposed": df[df.status.isin(proposed)].groupby(fcol).size(),
            "stopped": df[df.status.isin({"Cancelled", "Suspended"})].groupby(fcol).size(),
            "pushback": df[df.pushback].groupby(fcol).size()}).fillna(0).astype(int)

    cm = county_counts("fips_main", ft)
    cl = county_counts("fips_local", ft[~ft.local_dedupe_drop])
    cc = cm.join(cl, how="outer", lsuffix="_main", rsuffix="_local").fillna(0).astype(int)
    cc = cc[(cc.filter(like="_main").values != cc.filter(like="_local").values).any(axis=1)]
    write(cc.rename_axis("fips").reset_index(), "fractracker_county_count_differences.csv")
    res["facility_totals"] = {
        "main_rule": {k: int(v) for k, v in cm.sum().items()},
        "prior_local_rule": {k: int(v) for k, v in cl.sum().items()},
        "rows_dropped_by_local_dedupe": int(ft.local_dedupe_drop.sum()),
        "rows_assigned_differently": int((ft.cause == "geographic matching (name-first vs point-first)").sum()),
        "rows_unplaced_main": int(ft.fips_main.isna().sum()), "rows_unplaced_local": int(ft.fips_local.isna().sum()),
    }
    unparsed = ft[ft.mw.notna() & pd.to_numeric(ft.mw, errors="coerce").isna()]
    res["mw"] = {
        "facilities_with_mw_text": int(ft.mw.notna().sum()),
        "facilities_mw_unparseable_by_main": len(unparsed),
        "mw_lost_by_main_parse": float(unparsed.mw_parsed.sum()),
        "unparseable_examples": unparsed.mw.head(10).tolist(),
        "existing_reporting_share": float(ft[ft.status.isin(existing)].mw_parsed.notna().mean()),
        "proposed_reporting_share": float(ft[ft.status.isin(proposed)].mw_parsed.notna().mean()),
    }
    write(unparsed[["facility_id", "facility_name", "state", "county", "status", "mw", "mw_parsed", "fips_main"]],
          "fractracker_mw_parse_differences.csv")
    return res


def shipped_positions():
    """Where counties touched by the FracTracker findings sit in the shipped results."""
    mor = pd.read_csv(OUT / "fractracker_moratorium_differences.csv", dtype=str)
    geo = pd.read_csv(OUT / "fractracker_facility_assignment_differences.csv", dtype=str)
    findings = ([(f, "expired county moratorium still listed active") for f in sorted(set(mor[mor.jurisdiction_level == "county"].fips))]
                + [(f, "facility county assignment differs") for f in sorted(set(geo.fips_main) | set(geo.fips_local))])
    rows = []
    for p in PRESETS:
        r = pd.read_csv(ROOT / "results" / f"{p}.csv", dtype={"fips": str}).set_index("fips")
        x = pd.read_csv(ROOT / "results" / f"{p}_excluded.csv", dtype={"fips": str}).set_index("fips")
        for f, why in findings:
            rows.append({"preset": p, "fips": f, "finding": why,
                         "shipped_rank": int(r.loc[f, "rank"]) if f in r.index else None,
                         "shipped_failed_gates": x.loc[f, "failed_gates"] if f in x.index else ""})
    return write(pd.DataFrame(rows), "fractracker_findings_in_shipped_results.csv")


def main():
    table = pd.read_parquet(TABLE)
    summary = {"queue": queue_audit(table)}
    with tempfile.TemporaryDirectory() as tmp:
        dirs, summary["harness"] = run_rankings(tmp)
        summary["rankings"], summary["watch"] = summarize(dirs)
    summary["fractracker"] = fractracker_audit()
    shipped_positions()
    SUMMARY.write_text(json.dumps(summary, indent=1, default=float) + "\n")
    print(json.dumps({k: summary[k] for k in ("queue", "harness")}, indent=1, default=float))


if __name__ == "__main__":
    main()
