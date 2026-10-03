"""County name joins. A wrong or colliding key silently puts one county's data on another."""
import pandas as pd
import pytest

from etl.adapters import tiger_acs
from etl.fips import build_lookup, load_tiger, normalize_county, to_fips
from tests.conftest import RAW, require_raw

NAMES = "tests/fixtures/tiger_names.csv"  # GEOID, NAMELSAD, STUSPS from the TIGER 2024 county file


@pytest.fixture(scope="module")
def tiger():
    return pd.read_csv(NAMES, dtype=str)


def test_committed_name_list_matches_tiger(tiger):
    require_raw(tiger_acs.RAW)
    pd.testing.assert_frame_equal(load_tiger(RAW)[["GEOID", "NAMELSAD", "STUSPS"]], tiger)


def test_table_is_contiguous_us_plus_dc(tiger):
    assert len(tiger) == 3109
    assert tiger.STUSPS.nunique() == 49
    assert not {"AK", "HI", "PR"} & set(tiger.STUSPS)


def test_every_tiger_name_maps_to_its_own_fips(tiger):
    lookup = build_lookup(tiger)
    keys = [normalize_county(n, s) for n, s in zip(tiger.NAMELSAD, tiger.STUSPS)]
    assert len(set(keys)) == len(tiger), "two counties share a key"
    wrong = [(n, s) for n, s, f in zip(tiger.NAMELSAD, tiger.STUSPS, tiger.GEOID)
             if to_fips(n, s, lookup) != f]
    assert wrong == []


@pytest.mark.parametrize("name, state, fips", [
    ("St. Louis", "MO", "29189"),            # bare name means the county, not the city
    ("St. Louis city", "MO", "29510"),
    ("Saint Louis County", "MO", "29189"),
    ("De Kalb", "IL", "17037"),              # TIGER spells it DeKalb
    ("Richmond", "VA", "51159"),             # Richmond County, not the independent city
    ("Richmond city", "VA", "51760"),
    ("Alexandria", "VA", "51510"),           # independent city with no same-named county
    ("Charles City", "VA", "51036"),         # a county despite the name
    ("East Baton Rouge Parish", "LA", "22033"),
    ("Dona Ana", "NM", "35013"),             # TIGER has the tilde
    ("Fairfield", "CT", "09190"),            # old county maps to its dominant planning region
    ("loudoun county", "va", "51107"),
])
def test_known_hard_names(tiger, name, state, fips):
    assert to_fips(name, state, build_lookup(tiger)) == fips


def test_unknown_name_is_none_not_a_guess(tiger):
    lookup = build_lookup(tiger)
    assert to_fips("Atlantis", "VA", lookup) is None
    assert to_fips("Loudoun", "MD", lookup) is None  # right name, wrong state
