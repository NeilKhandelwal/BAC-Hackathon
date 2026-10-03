"""Long-run deindustrialization columns. They exist because the 2001-2023 columns can't see
Detroit or Gary: the collapse came before 2001. These tests pin that the new columns do, on the
committed table, so they run offline."""
import pandas as pd
import pytest

from etl.adapters import bea_manufacturing, tiger_acs
from etl.fips import build_lookup, load_tiger
from tests.conftest import RAW, require_raw

RUST_BELT = {"26163": "Wayne, MI (Detroit)", "39099": "Mahoning, OH (Youngstown)",
             "42021": "Cambria, PA (Johnstown)", "26049": "Genesee, MI (Flint)"}
LOUDOUN = "51107"


@pytest.fixture(scope="module")
def table():
    return pd.read_parquet("data/processed/county_features.parquet").set_index("fips")


def _decline_rank(table, fips):
    # Share of counties with a smaller (more negative) value: low means steep decline.
    return (table.pop_change_pct_since_peak < table.pop_change_pct_since_peak[fips]).mean()


@pytest.mark.parametrize("fips", [f for f in RUST_BELT if f != "26049"])
def test_rust_belt_counties_are_in_the_top_quarter_for_population_decline(table, fips):
    assert _decline_rank(table, fips) <= 0.25, RUST_BELT[fips]


@pytest.mark.xfail(strict=True, reason="Genesee, MI is 10.7% below its 1980 peak, the 34th "
                   "percentile. A county measure dilutes a city's decline: Flint is one part of "
                   "Genesee County. Reported, not tuned away.")
def test_genesee_is_in_the_top_quarter_for_population_decline(table):
    assert _decline_rank(table, "26049") <= 0.25


@pytest.mark.parametrize("fips", RUST_BELT)
def test_rust_belt_counties_are_in_the_top_quarter_for_1969_manufacturing(table, fips):
    share = table.mfg_emp_share_1969
    assert share[fips] >= share.quantile(0.75), RUST_BELT[fips]


def test_loudoun_is_in_the_bottom_quarter_on_both(table):
    assert table.pop_change_pct_since_peak[LOUDOUN] >= table.pop_change_pct_since_peak.quantile(0.75)
    assert table.mfg_emp_share_1969[LOUDOUN] <= table.mfg_emp_share_1969.quantile(0.25)


def test_coal_closure_flag_needs_a_closure_in_the_county(table):
    # Every Loudoun tract qualifies only by adjoining a closure tract across the Potomac.
    # Counting adjoining tracts would flag 364 more counties with no closure of their own.
    assert not table.energy_community_coal_closure[LOUDOUN]
    assert table.energy_community_coal_closure["18089"]  # Lake, IN: State Line plant, Hammond


def test_virginia_combined_areas_go_to_the_right_city():
    # BEA's "Southampton + Franklin" means Franklin city (51620), not Franklin County (51067),
    # which BEA reports on its own.
    require_raw(bea_manufacturing.RAW, "bea/CAEMP25N.zip", tiger_acs.RAW)
    out = bea_manufacturing.build(RAW).set_index("fips").mfg_emp_share_1969
    assert out["51620"] == out["51175"]
    assert out["51067"] != out["51620"]
    lookup = build_lookup(load_tiger(RAW))
    assert bea_manufacturing._members("51949", "Southampton + Franklin, VA*", lookup) == ["51175", "51620"]
