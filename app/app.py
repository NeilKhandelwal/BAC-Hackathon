"""Demo UI for the decision engine. Run: streamlit run app/app.py [-- --features PATH --geojson PATH]

Everything runs in process from local files; no network calls. The engine
does the ranking; this file only edits a conditions dict and draws results.
"""
import argparse
import copy
import json
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.explain import explain  # noqa: E402
from engine.rank import load_features, load_yaml, rank  # noqa: E402

PRESETS = {p.stem: p for p in sorted((ROOT / "engine/conditions").glob("*.yaml"))}
PILLARS = load_yaml(ROOT / "engine/pillars.yaml")
GREY = "#c8c8c8"


def paths():
    p = argparse.ArgumentParser()
    p.add_argument("--features", default=os.environ.get(
        "BAC_FEATURES", ROOT / "data/processed/county_features.parquet"))
    p.add_argument("--geojson", default=os.environ.get(
        "BAC_GEOJSON", ROOT / "data/processed/counties.geojson"))
    args, _ = p.parse_known_args(sys.argv[1:])
    return Path(args.features), Path(args.geojson)


@st.cache_data(show_spinner="Loading county table")
def features(path, mtime):  # mtime busts the cache when the ETL rewrites the file
    return load_features(path)


@st.cache_data(show_spinner=False)
def geojson(path, mtime):
    return json.loads(Path(path).read_text())


@st.cache_data(show_spinner="Ranking counties")
def run(path, mtime, conditions_json):
    df, _ = features(path, mtime)
    return rank(df, json.loads(conditions_json), PILLARS)


@st.cache_data(show_spinner=False)
def detail(path, mtime, conditions_json, fips):
    df, _ = features(path, mtime)
    return explain(df, json.loads(conditions_json), PILLARS, fips, result=run(path, mtime, conditions_json))


def optional_slider(label, value, lo, hi, step, key, help=None):
    """Checkbox plus slider; returns None when the gate is off."""
    on = st.checkbox(label, value=value is not None, key=key + ":on", help=help)
    if not on:
        return None
    return st.slider(label, lo, hi, value if value is not None else lo, step, key=key,
                     label_visibility="collapsed")


def sidebar():
    s = st.sidebar
    preset = s.selectbox("Preset", list(PRESETS), key="preset")
    c = copy.deepcopy(load_yaml(PRESETS[preset]))
    k = f"{preset}:"  # widget keys per preset, so switching presets resets every control
    g = c.setdefault("gates", {})

    with s.expander("Weights", expanded=True):
        for p, w in c["weights"].items():
            c["weights"][p] = st.slider(p.replace("_", " "), 0.0, 1.0, float(w), 0.01, key=k + "w:" + p)
        total = sum(c["weights"].values()) or 1
        st.caption("Normalized: " + ", ".join(f"{p} {w / total:.0%}" for p, w in c["weights"].items()))

    with s.expander("Facility and horizon", expanded=True):
        c["horizon"] = st.radio("Horizon", [2026, 2050], index=[2026, 2050].index(c.get("horizon", 2026)),
                                horizontal=True, key=k + "horizon")
        if c["horizon"] == 2050:
            c["scenario"] = st.radio("Scenario", ["rcp45", "rcp85"],
                                     index=["rcp45", "rcp85"].index(c.get("scenario", "rcp85")),
                                     horizontal=True, key=k + "scenario")
        c["facility"]["mw"] = st.number_input("Facility IT load (MW)", 10, 5000, int(c["facility"].get("mw", 300)),
                                              50, key=k + "mw")
        cooling = ["dry", "evaporative", "hybrid"]
        c["facility"]["cooling"] = st.selectbox("Cooling", cooling, index=cooling.index(c["facility"]["cooling"]),
                                                key=k + "cooling")

    with s.expander("Gates", expanded=True):
        for col, v in (g.get("hazard_percentile_max") or {}).items():
            name = col.removeprefix("nri_").removesuffix("_score").replace("_", " ")
            g["hazard_percentile_max"][col] = optional_slider(
                f"Max {name} percentile", v, 50, 100, 1, k + "hz:" + col)
        g["min_fiber_share_locations"] = optional_slider(
            "Min fiber share", g.get("min_fiber_share_locations"), 0.0, 1.0, 0.05, k + "fiber")
        g["min_nearby_capacity_multiple"] = optional_slider(
            "Min nearby plant MW, as a multiple of facility MW", g.get("min_nearby_capacity_multiple"), 1, 20, 1,
            k + "cap", help="Plant nameplate MW within 100 km. A proxy for deliverable power, not a load-flow study.")
        g["max_queue_median_age_years"] = optional_slider(
            "Max queue median age (years)", g.get("max_queue_median_age_years"), 1, 10, 1, k + "queue")
        g["min_population"] = optional_slider(
            "Min population", g.get("min_population"), 0, 100_000, 1000, k + "pop")
        g["exclude_moratorium_active"] = st.checkbox(
            "Exclude county moratoria", bool(g.get("exclude_moratorium_active")), key=k + "mor")
        g["exclude_moratorium_state_active"] = st.checkbox(
            "Exclude state moratoria", bool(g.get("exclude_moratorium_state_active")), key=k + "mors")
        c["pillar_floor_percentile"] = st.slider(
            "Pillar floor percentile", 0, 50, int(c.get("pillar_floor_percentile", 0)), 5, key=k + "floor",
            help="A county below this percentile on any pillar ranks below every county that isn't. "
                 f"Exempt from the floor: {', '.join(c.get('pillar_floor_exempt') or []) or 'none'}.")

    edited = c != load_yaml(PRESETS[preset])
    if edited:
        c["name"] = f"{preset}_edited"
    text = yaml.safe_dump(c, sort_keys=False)
    s.download_button("Download conditions YAML", text, file_name=f"{c['name']}.yaml", mime="text/yaml")
    with s.expander("Conditions YAML"):
        st.code(text, language="yaml")
    return c, edited


def county_map(df, ranked, excluded, color, geo):
    """Choropleth of gate-passed counties; excluded counties grey with the failed gate on hover."""
    label = color.removeprefix("pillar_").replace("_", " ")
    ranked = ranked.assign(hover=ranked["county_name"] + ", " + ranked["state"] + "<br>rank " +
                           ranked["rank"].astype(str) + "<br>" + label + " " + ranked[color].round(2).astype(str))
    excluded = excluded.assign(hover=excluded["county_name"] + ", " + excluded["state"] +
                               "<br>excluded: " + excluded["failed_gates"].str.replace(";", ", "))
    layout = dict(map_style="white-bg", map_zoom=3.1, map_center={"lat": 38.5, "lon": -96},
                  margin=dict(l=0, r=0, t=0, b=0), height=520)
    if geo is not None:
        fig = px.choropleth_map(ranked, geojson=geo, locations="fips", featureidkey="properties.fips",
                                color=color, color_continuous_scale="Viridis", hover_name="hover",
                                hover_data={"fips": False, color: False})
        fig.add_trace(go.Choroplethmap(geojson=geo, locations=excluded["fips"], featureidkey="properties.fips",
                                       z=[0] * len(excluded), colorscale=[[0, GREY], [1, GREY]], showscale=False,
                                       text=excluded["hover"], hoverinfo="text", marker_line_width=0))
        fig.update_traces(marker_line_width=0)
    else:
        pts = df.set_index("fips")[["centroid_lat", "centroid_lon"]]
        ranked, excluded = ranked.join(pts, on="fips"), excluded.join(pts, on="fips")
        fig = px.scatter_map(ranked, lat="centroid_lat", lon="centroid_lon", color=color,
                             color_continuous_scale="Viridis", hover_name="hover",
                             hover_data={"centroid_lat": False, "centroid_lon": False, color: False})
        fig.add_trace(go.Scattermap(lat=excluded["centroid_lat"], lon=excluded["centroid_lon"], mode="markers",
                                    marker=dict(color=GREY, size=5), text=excluded["hover"], hoverinfo="text",
                                    showlegend=False))
    fig.update_layout(**layout, coloraxis_colorbar=dict(title=label))
    return fig


def fmt(v, spec):
    return "n/a" if v is None else format(v, spec)


def show_detail(e, path, mtime, conditions):
    st.subheader(f"{e['county_name']}, {e['state']} ({e['fips']})")
    if e["passed_gates"]:
        floor = "passes the floor" if e["floor_ok"] else "below the floor on at least one pillar"
        st.markdown(f"**Rank {e['rank']} of {e['of']}** · composite {fmt(e['composite'], '.1f')} · {floor} · "
                    f"robustness {fmt(e['robustness'], '.0%')} · coverage {fmt(e['coverage'], '.0%')}")
        st.markdown("**Top reasons:** " + (", ".join(r.replace("_", " ") for r in e["top_reasons"])
                                           or "no column above the national median"))
    else:
        st.error("Excluded by: " + ", ".join(e["failed_gates"]))
    if e["unknown_gates"]:
        st.caption("No data, so not excluded: " + ", ".join(e["unknown_gates"]))

    # Floor crossing between horizons, from a cached rank under each horizon.
    floors = {}
    for h in (2026, 2050):
        r, _, _ = run(path, mtime, json.dumps({**conditions, "horizon": h}, sort_keys=True))
        hit = r.loc[r["fips"] == e["fips"], "floor_ok"]
        floors[h] = bool(hit.iloc[0]) if len(hit) else None
    if floors[2026] and floors[2050] is False:
        st.warning("Falls below the floor in 2050.")
    elif floors[2026] is False and floors[2050]:
        st.info("Rises above the floor in 2050.")

    left, right = st.columns(2)
    bars = pd.DataFrame([{"pillar": p.replace("_", " "), "score": d["score"], "weight": d["weight"]}
                         for p, d in e["pillars"].items()])
    fig = px.bar(bars, x="score", y="pillar", orientation="h", range_x=[0, 100], text_auto=".0f",
                 hover_data={"weight": ":.0%"})
    fig.update_layout(height=40 * len(bars) + 60, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None)
    left.plotly_chart(fig, width="stretch")

    with right:
        if e["horizon_2050_raw"]:
            rows = []
            for col, d in e["horizon_2050_raw"].items():
                fut = next(k for k in d if k not in ("today", "delta"))
                rows.append({"metric": col, "today": d["today"], "2050": d[fut], "change": d["delta"]})
            st.markdown("**Raw change by 2050**")
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if "permitting" in e["pillars"]:
            st.markdown("**Permitting**")
            st.dataframe(pd.DataFrame(e["pillars"]["permitting"]["columns"]), hide_index=True,
                         width="stretch")

    with st.expander("Every scored column"):
        rows = [{"pillar": p, **c} for p, d in e["pillars"].items() for c in d["columns"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def main():
    st.set_page_config(page_title="Data center site engine", layout="wide")
    fpath, gpath = paths()
    if not fpath.exists():
        st.error(f"No county table at {fpath}. Set BAC_FEATURES or pass -- --features PATH.")
        st.stop()
    mtime = fpath.stat().st_mtime
    df, load_warnings = features(fpath, mtime)
    geo = geojson(gpath, gpath.stat().st_mtime) if gpath.exists() else None

    conditions, edited = sidebar()
    cjson = json.dumps(conditions, sort_keys=True)
    try:
        ranked, excluded, report = run(fpath, mtime, cjson)
    except ValueError as err:  # for example, every pillar with data has weight 0
        st.error(f"The engine can't rank with these conditions: {err}")
        st.stop()

    st.title("Where to build a sustainable AI data center")
    st.markdown(f"**{conditions['name']}**{' (edited)' if edited else ''} · horizon {conditions['horizon']} · "
                f"**{report['passed']:,}** of {report['counties']:,} counties pass the gates · "
                f"**{report['floor_ok']:,}** pass the pillar floor")
    dropped = [p for p, w in conditions["weights"].items() if w and p not in report["pillars"]]
    with st.expander(f"Data notes ({len(dropped)} pillars dropped, {len(load_warnings) + len(report['warnings'])} warnings)"):
        if dropped:
            st.markdown("**Pillars with no data, weight spread over the rest:** " + ", ".join(dropped))
        st.markdown("**Weights used:** " + ", ".join(f"{p} {w:.0%}" for p, w in report["weights_used"].items()))
        for w in load_warnings + report["warnings"]:
            st.text(w)
        if report.get("hazard_gate_nonzero_counties"):
            st.markdown("**Hazard gates, counties with any exposure:** " + ", ".join(
                f"{g.split('.')[-1]} {n:,}" for g, n in report["hazard_gate_nonzero_counties"].items()))
        if geo is None:
            st.markdown(f"TODO: no county GeoJSON at {gpath}; the map shows county centroids instead.")

    pillar_cols = [c for c in ranked.columns if c.startswith("pillar_")]
    color = st.selectbox("Color the map by", ["composite", "robustness"] + pillar_cols,
                         format_func=lambda c: c.removeprefix("pillar_").replace("_", " "))
    st.plotly_chart(county_map(df, ranked, excluded, color, geo), width="stretch")

    st.subheader("Shortlist")
    top_n = (conditions.get("output") or {}).get("top_n", 10)
    cols = ["rank", "county_name", "state", "composite", "robustness", "coverage"] + pillar_cols
    top = ranked.head(top_n)
    shown = top[cols].round({c: 1 for c in ["composite"] + pillar_cols})
    table = st.dataframe(shown.rename(columns=lambda c: c.removeprefix("pillar_")), hide_index=True,
                         width="stretch", on_select="rerun", selection_mode="single-row",
                         column_config={"robustness": st.column_config.NumberColumn(format="percent"),
                                        "coverage": st.column_config.NumberColumn(format="percent")})

    st.subheader("County detail")
    names = df["county_name"].fillna("") + ", " + df["state"].fillna("") + " (" + df["fips"] + ")"
    options = dict(zip(names, df["fips"]))
    picked_rows = table.selection.rows if table and table.selection else []
    default_fips = top.iloc[picked_rows[0]]["fips"] if picked_rows else (top["fips"].iloc[0] if len(top) else df["fips"].iloc[0])
    labels = list(options)
    choice = st.selectbox("Find a county", labels, index=labels.index(names[df["fips"] == default_fips].iloc[0]),
                          key=f"county:{default_fips}")
    show_detail(detail(fpath, mtime, cjson, options[choice]), fpath, mtime, conditions)


main()
