"""Smoke test for the Streamlit app on the fake table: every demo interaction must rerun without an exception."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fake_features import make

APP = "../app/app.py"  # resolved relative to this file


@pytest.fixture
def fake_env(tmp_path, monkeypatch, request):
    df = make(n=150)
    df.to_parquet(tmp_path / "county_features.parquet", index=False)
    feats = []
    for _, r in df.iterrows():  # one small square per county, at its centroid
        x, y = r["centroid_lon"], r["centroid_lat"]
        ring = [[x, y], [x + 0.3, y], [x + 0.3, y + 0.3], [x, y + 0.3], [x, y]]
        feats.append({"type": "Feature", "id": r["fips"], "properties": {"fips": r["fips"]},
                      "geometry": {"type": "Polygon", "coordinates": [ring]}})
    (tmp_path / "counties.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    monkeypatch.setenv("BAC_FEATURES", str(tmp_path / "county_features.parquet"))
    monkeypatch.setenv("BAC_GEOJSON", str(tmp_path / ("counties.geojson" if request.param else "absent.geojson")))
    df.attrs["path"] = str(tmp_path / "county_features.parquet")
    return df


def started():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception, at.exception
    return at


def headline(at):
    return next(m.value for m in at.markdown if "pass the gates" in m.value)


@pytest.mark.parametrize("fake_env", [True, False], ids=["geojson", "centroid-fallback"], indirect=True)
def test_every_preset_renders_a_shortlist_and_detail(fake_env):
    at = started()
    for preset in ["balanced", "speed_to_power", "sustainability_first"]:
        at.sidebar.selectbox(key="preset").set_value(preset).run()
        assert not at.exception, (preset, at.exception)
        assert preset in headline(at)
        assert any(s.value == "County detail" for s in at.subheader)


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_controls_rerun_the_engine_and_mark_the_conditions_edited(fake_env):
    at = started()
    before = headline(at)
    at.sidebar.checkbox(key="balanced:fiber:on").uncheck().run()  # drop the fiber gate
    assert not at.exception
    after = headline(at)
    assert "(edited)" in after and after != before  # more counties pass without the gate

    at.sidebar.slider(key="balanced:w:water").set_value(0.9).run()
    assert not at.exception
    at.sidebar.radio(key="balanced:horizon").set_value(2050).run()
    assert not at.exception and "horizon 2050" in headline(at)
    at.selectbox[0].set_value("pillar_water").run()  # map color selector
    assert not at.exception


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_county_search_opens_any_county_including_excluded_ones(fake_env):
    at = started()
    search = next(s for s in at.selectbox if s.label == "Find a county")
    excluded = [o for o in search.options if o]  # pick until we hit a gate-excluded county
    for label in excluded[:40]:
        search = next(s for s in at.selectbox if s.label == "Find a county")
        search.set_value(label).run()
        assert not at.exception, (label, at.exception)
        if at.error:
            break
    assert at.error, "expected at least one gate-excluded county among the first 40"


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_a_bigger_facility_shrinks_the_shortlist(fake_env):
    # The capacity gate reads facility.mw, so the demo must show fewer counties as the campus grows.
    at = started()
    passed = lambda: int(headline(at).split("**")[3].replace(",", ""))
    small = passed()
    at.sidebar.number_input(key="balanced:mw").set_value(3000).run()
    assert not at.exception
    assert passed() < small


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_all_weights_at_zero_shows_an_error_not_a_traceback(fake_env):
    at = started()
    for slider in at.sidebar.slider:
        if slider.key and slider.key.startswith("balanced:w:"):
            slider.set_value(0.0)
    at.run()
    assert not at.exception
    assert any("can't rank" in e.value for e in at.error)


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_downloaded_conditions_reproduce_the_shortlist(fake_env):
    # The conditions file is the product's interface: what the app exports must rerun to the same answer.
    import pandas as pd
    import yaml

    from engine.rank import load_features, load_yaml, rank

    at = started()
    at.sidebar.slider(key="balanced:w:water").set_value(0.6).run()
    at.sidebar.checkbox(key="balanced:fiber:on").uncheck().run()
    at.sidebar.number_input(key="balanced:mw").set_value(800).run()
    assert not at.exception
    exported = yaml.safe_load(at.sidebar.code[0].value)
    assert exported["name"] == "balanced_edited" and exported["facility"]["mw"] == 800

    shown = next(d.value for d in at.dataframe if "rank" in d.value.columns)
    df, _ = load_features(fake_env.attrs["path"])
    ranked = rank(df, exported, load_yaml("engine/pillars.yaml"))[0]
    assert ranked["county_name"].head(len(shown)).tolist() == shown["county_name"].tolist()


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_raw_2050_table_uses_readable_labels_from_the_mapping(fake_env):
    # A judge reads this table; raw column names like cdd_hist mean nothing on a projector.
    import importlib.util
    import yaml

    spec = importlib.util.spec_from_file_location("app_module", Path(__file__).resolve().parents[1] / "app/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    labels = module.METRIC_LABELS
    swapped = {m["column"] for ms in yaml.safe_load(open("engine/pillars.yaml")).values() for m in ms
               if m.get("horizon_2050")}
    assert swapped <= set(labels), "every column with a 2050 swap needs a label"

    at = started()
    table = next(d.value for d in at.dataframe if "metric" in d.value.columns)
    assert set(table["metric"]) <= set(labels.values())
    assert not set(table["metric"]) & swapped  # no raw column names leak through
    numeric = table[["today", "2050", "change"]].dropna().to_numpy().ravel()
    assert (abs(numeric * 10 - (numeric * 10).round()) < 1e-6).all()  # one decimal



@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_state_moratorium_flag_shows_in_headline_shortlist_and_detail(fake_env):
    import pandas as pd

    from engine.explain import MORATORIUM_WARNING
    from engine.rank import load_yaml, rank

    # Flag three counties that rank under balanced, so the flag is visible on the shortlist.
    df = fake_env.copy()
    df.attrs = {}
    ranked = rank(df, load_yaml("engine/conditions/balanced.yaml"), load_yaml("engine/pillars.yaml"))[0]
    flagged = set(ranked["fips"].head(3))
    df["moratorium_state_active"] = pd.array(df["fips"].isin(flagged), dtype="boolean")
    df.to_parquet(fake_env.attrs["path"], index=False)

    at = started()
    assert "**3** ranked counties are under a state moratorium" in headline(at)
    shortlist = next(d.value for d in at.dataframe if "rank" in d.value.columns)
    assert shortlist["moratorium_state_active"].head(3).astype(bool).all()
    search = next(s for s in at.selectbox if s.label == "Find a county")

    def open_county(fips):
        next(s for s in at.selectbox if s.label == "Find a county").set_value(
            next(o for o in search.options if o.endswith(f"({fips})"))).run()
        assert not at.exception
        return [w.value for w in at.warning]

    assert MORATORIUM_WARNING in open_county(sorted(flagged)[0])
    clear = next(f for f in fake_env["fips"] if f not in flagged)
    assert MORATORIUM_WARNING not in open_county(clear)


def load_app_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", Path(__file__).resolve().parents[1] / "app/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_2050_change_is_computed_from_the_rounded_cells():
    # Whitman WA read 0.0 -> 0.5 with a change of 0.4 when each cell rounded on its own.
    # A judge reading the row must see arithmetic that adds up.
    app = load_app_module()
    e = {"horizon_2050_raw": {
        "water_stress_bws": {"today": 0.04, "water_stress_2050": 0.46, "delta": 0.42},
        "cdd_hist": {"today": 362.14, "cdd_2050_rcp85": 838.26, "delta": 476.12},
        "days_above_95f_hist": {"today": 9.1, "days_above_95f_2050_rcp85": None, "delta": None}}}
    rows = app.raw_2050_rows(e).set_index("metric")
    water = rows.loc[app.METRIC_LABELS["water_stress_bws"]]
    assert (water["today"], water["2050"], water["change"]) == (0.0, 0.5, 0.5)
    assert rows.loc[app.METRIC_LABELS["cdd_hist"], "change"] == 476.2  # 838.3 - 362.1, not round(476.12)
    assert rows.loc[app.METRIC_LABELS["days_above_95f_hist"]].isna()[["2050", "change"]].all()


@pytest.mark.parametrize("fake_env", [True], indirect=True)
def test_every_rendered_2050_row_adds_up(fake_env):
    at = started()
    table = next(d.value for d in at.dataframe if "metric" in d.value.columns).dropna()
    assert ((table["2050"] - table["today"]).round(1) == table["change"]).all()
