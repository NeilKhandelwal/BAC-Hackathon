"""Checks on the built county table. The engine trusts these properties without re-checking.

Run `python -m etl.build_features` first.
"""
import json

import pandas as pd
import pytest

from etl.schema import CORE, STRETCH

OUT = "data/processed/county_features"


@pytest.fixture(scope="module")
def table():
    return pd.read_parquet(OUT + ".parquet")


@pytest.fixture(scope="module")
def manifest():
    with open(OUT + ".manifest.json") as fh:
        return json.load(fh)


def test_one_row_per_county_keyed_by_string_fips(table):
    assert len(table) == 3109
    assert table.fips.is_unique
    assert (table.fips.str.len() == 5).all()  # an integer key would drop Alabama's leading zero
    assert "11001" in set(table.fips) and not table.fips.str.startswith("02").any()


def test_every_core_column_exists_with_schema_dtype(table):
    actual = {c: "string" if pd.api.types.is_string_dtype(table[c]) else str(table[c].dtype) for c in CORE}
    assert actual == CORE


def test_manifest_missing_columns_match_the_table(table, manifest):
    empty = {c for c in table.columns if table[c].isna().all()}
    absent = set(STRETCH) - set(table.columns)
    assert set(manifest["columns_missing"]) == empty | absent
    assert set(manifest["columns_present"]) == set(table.columns) - empty


@pytest.mark.parametrize("column", ["grid_renewable_share", "queue_withdrawal_rate",
                                    "drought_share_weeks_d2plus", "fiber_share_locations"])
def test_shares_are_fractions_not_percents(table, column):
    assert table[column].dropna().between(0, 1).all()
    assert table[column].max() > 0.2  # all-tiny values would mean a double division by 100


def test_nri_scores_are_0_to_100(table):
    for column in [c for c in table.columns if c.startswith("nri_")]:
        assert table[column].dropna().between(0, 100).all(), column


def test_inapplicable_hazard_is_zero_not_null(table):
    row = table.set_index("fips")
    assert row.nri_coastal_flood_score["19161"] == 0   # Sac County, Iowa: no coast
    assert row.nri_coastal_flood_score["12086"] > 50   # Miami-Dade


def test_undefined_queue_metrics_are_null_not_zero(table):
    # A zero median age would rank a county with no queue as the least congested in the country.
    assert table.queue_median_age_years.isna().sum() > 1000
    assert (table.queue_median_age_years.dropna() > 0).all()
    assert (table.queue_active_mw_clean <= table.queue_active_mw_total + 1e-9).all()


def test_known_counties_look_right(table):
    row = table.set_index("fips")
    assert table.loc[table.dc_existing_count.idxmax(), "fips"] == "51107"  # Loudoun, VA
    assert row.cdd_2050_rcp85["04013"] > row.cdd_hist["04013"] > row.cdd_hist["19161"]  # Maricopa warms
    assert row.moratorium_state_active["36061"] == row.moratorium_state_active["36001"]  # state flag broadcasts


def test_grid_rates_describe_the_subregion_not_the_state(table):
    # A 300 MW load in Vermont draws from the New England grid, not Vermont's own hydro.
    row = table.set_index("fips")
    assert row.grid_subregion["50001"] == "NEWE"
    assert row.grid_co2_lb_mwh_state["50001"] < 100 < row.grid_co2_lb_mwh["50001"]
    assert row.grid_co2_lb_mwh["50001"] == row.grid_co2_lb_mwh["25025"]   # Vermont and Boston share a grid
    assert row.grid_co2_lb_mwh["36061"] > 2 * row.grid_co2_lb_mwh["36001"]  # NYC vs upstate
    assert table.grid_subregion.notna().all()


def test_hazard_scores_do_not_punish_counties_for_being_large(table):
    # Dollar-loss risk rates Dallas and Polk County, Iowa as flood-prone because there is a lot
    # to lose. The loss-rate percentile that the engine gates on must not.
    row = table.set_index("fips")
    for fips in ("48113", "19153", "51107"):
        assert row.nri_inland_flood_risks[fips] > 80 > 50 > row.nri_inland_flood_score[fips]
    assert row.moratorium_state_active["36061"] == row.moratorium_state_active["36001"]  # state flag broadcasts


def test_unknown_policy_inputs_give_null_risk_not_a_low_score(table):
    # Filling an unknown flag with false would make an unresearched state look permissive.
    inputs = table[["state_dc_bill_pending", "state_sales_tax_exemption", "state_large_load_tariff"]]
    assert (table.state_policy_risk.isna() == inputs.isna().any(axis=1)).all()
    known = table.dropna(subset="state_policy_risk")
    expected = (known.state_dc_bill_pending.astype(int) + (~known.state_sales_tax_exemption).astype(int)
                + known.state_large_load_tariff.astype(int))
    assert (known.state_policy_risk == expected).all()


def test_water_permit_risk_follows_the_schema(table):
    riparian = table.water_rights_regime == "riparian"
    managed = table.groundwater_managed_area.fillna(False)
    assert table.water_permit_risk.notna().all()  # an unresearched managed flag must not null the risk
    assert (table.water_permit_risk[riparian] == 0).all()
    assert (table.water_permit_risk[~riparian & managed] == 2).all()
    assert (table.water_permit_risk[~riparian & ~managed] == 1).all()
    assert table.set_index("fips").water_permit_risk["04013"] == 2  # Maricopa: Phoenix AMA


def test_wind_raster_is_oriented_north_up(table):
    # The source raster is stored south-up. A missed flip would swap North Dakota with Texas.
    row = table.set_index("fips")
    assert row.wind_speed_100m_ms["38015"] > 7 > 6.5 > row.wind_speed_100m_ms["22071"]  # Bismarck vs New Orleans
    assert row.wind_speed_100m_ms["48375"] > 7.5 > 6 > row.wind_speed_100m_ms["12095"]  # Amarillo vs Orlando
