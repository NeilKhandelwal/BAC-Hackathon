"""Smoke test for the Streamlit app on the fake table: every demo interaction must rerun without an exception."""
import json

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
