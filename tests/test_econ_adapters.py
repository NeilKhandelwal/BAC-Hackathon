"""Economic development adapters. A wrong FIPS remap or a misread flag silently moves jobs or
capacity onto the wrong county, and the permitting model would learn from it."""
import pandas as pd
import pytest

from etl.adapters import cbp_manufacturing, eia860_coal, ers_unemployment, tiger_acs
from etl.fips import load_tiger

RAW = "data/raw"


@pytest.fixture(scope="module")
def tiger():
    tiger_acs.fetch(RAW)
    return load_tiger(RAW)


@pytest.fixture(scope="module")
def cbp():
    cbp_manufacturing.fetch(RAW)
    return cbp_manufacturing.build(RAW).set_index("fips")


@pytest.fixture(scope="module")
def raw_2001():
    d = pd.read_csv(f"{RAW}/cbp/cbp01co.zip", dtype=str, usecols=["fipstate", "fipscty", "naics", "emp"])
    d["fips"] = d.fipstate + d.fipscty
    return d.set_index(["fips", "naics"]).emp.astype(float)


def test_dade_2001_jobs_land_on_miami_dade(cbp, raw_2001):
    # Dade (12025) became Miami-Dade (12086) in 1997 but kept its old code in CBP 2001.
    share = raw_2001["12025", "31----"] / raw_2001["12025", "------"]
    assert cbp.mfg_emp_share_2001["12086"] == pytest.approx(share)


def test_dc_unallocated_2001_code_maps_to_dc(cbp, raw_2001):
    # CBP 2001 has no 11001 rows. All of DC sits under 11999, which elsewhere means "statewide".
    share = raw_2001["11999", "31----"] / raw_2001["11999", "------"]
    assert cbp.mfg_emp_share_2001["11001"] == pytest.approx(share)


def _cbp_file(tmp_path, flag, flag_value):
    rows = pd.DataFrame({"fipstate": ["01", "01"], "fipscty": ["001", "001"],
                         "naics": ["------", "31----"], flag: [None, flag_value], "emp": [1000, 0]})
    path = tmp_path / f"{flag}.csv"
    rows.to_csv(path, index=False)
    return path


def test_2001_size_class_is_imputed_but_2022_noise_flag_is_not(tmp_path):
    # 2001 "A" is a withheld cell of 0-19 jobs. 2022 "G" is a noise flag on a real 0.
    y01 = cbp_manufacturing._employment(_cbp_file(tmp_path, "empflag", "A"), "empflag",
                                        cbp_manufacturing.FLAG_MIDPOINT)
    y22 = cbp_manufacturing._employment(_cbp_file(tmp_path, "emp_nf", "G"), "emp_nf")
    assert y01.mfg["01001"] == 10
    assert y22.mfg["01001"] == 0


def test_unemployment_has_only_counties(tiger):
    ers_unemployment.fetch(RAW)
    df = ers_unemployment.build(RAW)
    # State and US rows end in 000. One leaking in would give a county its state's rate.
    assert not df.fips.str.endswith("000").any()
    in_scope = df[df.fips.isin(set(tiger.GEOID))]
    assert len(in_scope) == len(tiger)
    assert in_scope.unemployment_rate_pct_2023.between(0, 30).all()  # percent, not a fraction


def test_retired_coal_is_zero_not_null_and_every_generator_is_placed(tiger):
    eia860_coal.fetch(RAW)
    df = eia860_coal.build(RAW).set_index("fips")
    # A renamed county in a future EIA edition would drop MW. Fail loudly instead.
    assert eia860_coal.UNMATCHED == []
    assert df.coal_retired_mw.notna().all()
    assert df.coal_retired_mw["51107"] == 0      # Loudoun, VA: no coal plant
    assert df.coal_retired_mw["42063"] > 1500    # Indiana, PA: Homer City
