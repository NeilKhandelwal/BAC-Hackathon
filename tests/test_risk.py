"""Risk profile. The comparison direction matters: a low fiber share is bad, a low flood score good."""
import pandas as pd
import pytest

from etl import impact, risk

COLUMNS = sorted({column for _, column, _ in risk.RISKS})


def _table(**overrides):
    """Four made-up counties, values 1 to 4 in every risk column, plus what impact needs."""
    table = pd.DataFrame({c: [1.0, 2.0, 3.0, 4.0] for c in COLUMNS})
    table["fips"] = ["00001", "00002", "00003", "00004"]
    table["county_name"], table["state"] = "Test", "ZZ"
    return table.assign(**overrides)


def test_worse_than_follows_each_risk_direction():
    p = risk.profile("00004", _table()).set_index("column").worse_than_pct
    assert p["nri_inland_flood_score"] == 75.0  # highest flood score: worse than the other three
    assert p["fiber_share_locations"] == 0.0    # highest fiber share: worse than none
    p = risk.profile("00001", _table()).set_index("column").worse_than_pct
    assert p["nri_inland_flood_score"] == 0.0 and p["fiber_share_locations"] == 75.0


def test_ties_do_not_count_against_a_county():
    # Most counties have zero data centers. Having zero must not read as "worse than most".
    table = _table(dc_existing_count=[0.0, 0.0, 0.0, 5.0])
    p = risk.profile("00001", table).set_index("column").worse_than_pct
    assert p["dc_existing_count"] == 25.0


def test_energy_cost_by_hand():
    table = _table(cdd_hist=[0.0] * 4, cdd_2050_rcp85=[0.0] * 4, grid_co2_lb_mwh=[500.0] * 4,
                   industrial_price_cents_kwh=[20.0, 10.0, 10.0, 10.0])
    cost = risk.energy_cost("00001", baseline="00002", mw=100, table=table)
    mwh = 100 * 8760 * 0.8 * 1.12                    # 784,896 MWh at the cold-climate PUE
    assert cost["usd_per_year"] == pytest.approx(mwh * 200)          # 20 cents/kWh is $200/MWh
    assert cost["difference_usd_per_year"] == pytest.approx(mwh * 100)


def test_berkshire_sits_just_under_the_flood_gate():
    # research/risk.md says the featured county passed the balanced flood gate (cap 90) narrowly.
    # If the table or the county changes, that sentence has to change too.
    flood = risk.profile("25003").set_index("column").worse_than_pct["nri_inland_flood_score"]
    assert 89 < flood < 90


def test_power_price_is_the_featured_countys_worst_risk():
    assert risk.worst("25003", 1).column.iloc[0] == "industrial_price_cents_kwh"
    assert risk.energy_cost("25003")["difference_usd_per_year"] > 150e6
    assert impact.impact("25003")["co2_tonnes"] < impact.impact("51107")["co2_tonnes"]
