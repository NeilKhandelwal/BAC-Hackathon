"""The permitting model is dropped. These tests pin why, and guard the label and feature rules.

Reads the committed county table and labels, so it runs on a clean clone.
"""
import pandas as pd
import pytest

from etl import permitting
from etl.adapters import tiger_acs
from tests.conftest import RAW, require_raw


@pytest.fixture(scope="module")
def table():
    return pd.read_parquet("data/processed/county_features.parquet")


@pytest.fixture(scope="module")
def labels():
    return pd.read_csv(permitting.LABELS, dtype={"fips": str})


def test_committed_labels_match_a_rebuild_from_raw(labels):
    require_raw("fractracker/ft_all.csv", tiger_acs.RAW)
    rebuilt = permitting.build_labels(RAW)[0]
    pd.testing.assert_frame_equal(rebuilt.reset_index(drop=True), labels)


def test_outcomes_of_opposition_cannot_be_features(table, monkeypatch):
    # Pushback counts and local moratoria are what the label measures. As features they leak it.
    assert not {column for column, _ in permitting.FEATURES.values()} & permitting.LABEL_DERIVED
    for leaked in permitting.LABEL_DERIVED:
        monkeypatch.setitem(permitting.FEATURES, "leak", (leaked, False))
        with pytest.raises(ValueError):
            permitting.feature_matrix(table)


def test_named_opposition_cases_are_positive(labels):
    positive = set(labels.fips[labels.label == 1])
    assert set(permitting.NAMED_CASES) <= positive


def test_a_negative_county_always_has_a_facility(table, labels):
    # This rule is why facility counts encode the label. If it changes, revisit the model.
    negative = table[table.fips.isin(labels.fips[labels.label == 0])]
    assert ((negative.dc_existing_count + negative.dc_proposed_count) > 0).all()
    assert labels.has_permitted_facility[labels.label == 0].all()


def test_model_has_no_skill_without_facility_counts(table, labels):
    # The reason permitting_discretionary_risk ships null. If better labels lift this above
    # 0.60, the decision in research/permitting_model.md must be revisited.
    report = permitting.validate(table, labels)
    assert report["auc_without_dc_counts"] < permitting.MIN_AUC
    assert report["decision"] == "dropped"
    assert report["labeled_counties_with_no_facility"]["positive_share"] == 1.0
    assert table.permitting_discretionary_risk.isna().all()
