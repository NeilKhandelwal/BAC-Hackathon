"""Impact numbers go on a slide. A unit slip (lb for tonnes, MWh for kWh) would be off by 1,000."""
import pandas as pd
import pytest

from etl import impact

# One made-up county so that every figure below can be checked by hand.
TABLE = pd.DataFrame([{"fips": "00001", "county_name": "Test", "state": "ZZ", "cdd_hist": 2000.0,
                       "cdd_2050_rcp85": 4000.0, "grid_co2_lb_mwh": 1000.0}])


def test_dry_cooling_by_hand():
    r = impact.impact("00001", mw=100, cooling="dry", table=TABLE)
    assert r["it_mwh"] == pytest.approx(100 * 8760 * 0.8)             # 700,800 MWh
    assert r["pue"] == pytest.approx(1.25)                            # halfway from 1.12 to 1.38
    assert r["facility_mwh"] == pytest.approx(876_000)
    assert r["co2_tonnes"] == pytest.approx(876_000 * 1000 / 2204.62)  # 397,347 t
    # 700,800 MWh = 700.8 million kWh at 0.05 L/kWh = 35.04 million L = 9.257 million gal
    assert r["water_million_gal"] == pytest.approx(35.04 / 3.78541)


def test_evaporative_cooling_trades_energy_for_water():
    dry = impact.impact("00001", mw=100, cooling="dry", table=TABLE)
    wet = impact.impact("00001", mw=100, cooling="evaporative", table=TABLE)
    assert wet["co2_tonnes"] < dry["co2_tonnes"]
    assert wet["water_million_gal"] > 10 * dry["water_million_gal"]
    # 0.95 L/kWh at 2,000 CDD: 700.8 million kWh -> 665.76 million L
    assert wet["water_million_gal"] == pytest.approx(665.76 / 3.78541)


def test_2050_changes_climate_but_not_the_grid_rate():
    today = impact.impact("00001", mw=100, cooling="evaporative", table=TABLE)
    later = impact.impact("00001", mw=100, cooling="evaporative", horizon="2050", table=TABLE)
    assert later["grid_co2_lb_mwh"] == today["grid_co2_lb_mwh"]
    assert later["pue"] == pytest.approx(1.25) and later["water_million_gal"] > today["water_million_gal"]


def test_results_scale_with_facility_size():
    small = impact.impact("00001", mw=100, table=TABLE)
    large = impact.impact("00001", mw=300, table=TABLE)
    assert large["co2_tonnes"] == pytest.approx(3 * small["co2_tonnes"])


def test_runs_on_the_committed_table_against_loudoun():
    result = impact.compare(["36033"], baseline="51107")
    row = result[(result.fips == "36033") & (result.cooling == "dry") & (result.horizon == "today")].iloc[0]
    assert row.co2_tonnes_vs_baseline < 0  # upstate New York's grid is cleaner than Virginia's
    loudoun = result[result.fips == "51107"]
    assert (loudoun.co2_tonnes_vs_baseline == 0).all()
