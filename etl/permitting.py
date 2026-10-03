"""Permitting discretionary risk: labels and validation of the model in docs/permitting.md.

The model is not shipped. Without the facility-count features, which encode how the labels are
built, no fit beats chance, so permitting_discretionary_risk stays null. This module is the
evidence. Results: research/permitting_model.md.

Usage: python -m etl.permitting   # needs the built county table and data/raw/fractracker/
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict

from etl.adapters.fractracker import _facility_fips
from etl.fips import build_lookup, load_tiger, to_fips

SEED = Path("data/processed/opposition_seed_labels.csv")
LABELS = Path("data/processed/permitting_labels.csv")
REPORT = Path("data/processed/permitting_validation.json")

# feature name -> (county table column, take log1p)
FEATURES = {
    "pop_density": ("pop_density_per_sqkm", True),
    "dc_existing": ("dc_existing_count", True),
    "dc_proposed": ("dc_proposed_count", True),
    "drought_weeks": ("drought_share_weeks_d2plus", False),
    "nri_drought": ("nri_drought_score", False),
    "queue_clean_mw": ("queue_active_mw_clean", True),
    "state_moratorium": ("moratorium_state_active", False),
    "income": ("median_household_income", False),
    "heating_degree_days": ("hdd_hist", False),  # keeps the model from learning region alone
    "cropland": ("pct_cropland", False),         # used only if the column has data
}
# Facility counts are tied to how labels are built: a county is negative only if it has an
# operating or approved facility. Validation reports AUC with and without them.
EXPOSURE = ["dc_existing", "dc_proposed"]
MIN_AUC = 0.60  # below this, docs/permitting.md says to drop the model
# Outcomes of opposition. Using them as features would leak the label.
LABEL_DERIVED = {"dc_pushback_count", "dc_pushback_any", "moratorium_active", "moratorium_pending"}

POSITIVE_SEED = {"cancelled", "withdrawn", "delayed"}
NEGATIVE_STATUS = {"Operating", "Approved/Permitted/Under construction", "Expanding"}
NAMED_CASES = {"04019": "Pima AZ", "51153": "Prince William VA", "13207": "Monroe GA",
               "18127": "Porter IN", "29037": "Cass MO"}


def build_labels(raw_dir):
    """Return (labels, unmatched). labels has fips, label (1 opposition, 0 none recorded), and
    has_permitted_facility, which marks the counties where either label is possible."""
    tiger = load_tiger(raw_dir)
    lookup = build_lookup(tiger)
    ft = pd.read_csv(Path(raw_dir) / "fractracker/ft_all.csv", low_memory=False)
    ft["fips"] = _facility_fips(ft, raw_dir, tiger)
    seed = pd.read_csv(SEED, dtype=str)
    seed = seed[seed.status.isin(POSITIVE_SEED)]
    seed_fips = [to_fips(str(c).rstrip("?"), s, lookup) for c, s in zip(seed.county, seed.state)]
    unmatched = seed[[f is None for f in seed_fips]][["state", "county", "project_name"]]

    positive = set(ft[ft.community_pushback.str.lower() == "yes"].fips.dropna()) | set(filter(None, seed_fips))
    permitted = set(ft[ft.status.isin(NEGATIVE_STATUS)].fips.dropna())
    labels = pd.DataFrame({"fips": sorted(positive | permitted)})
    labels["label"] = labels.fips.isin(positive).astype(int)
    labels["has_permitted_facility"] = labels.fips.isin(permitted)
    return labels, unmatched


def feature_matrix(table, names=None):
    """Standardized model features for every county, indexed by fips. Nulls take the median."""
    leaked = {FEATURES[n][0] for n in (names or FEATURES)} & LABEL_DERIVED
    if leaked:
        raise ValueError(f"{sorted(leaked)} are outcomes of opposition and can't be features")
    names = [n for n in (names or FEATURES)
             if FEATURES[n][0] in table and table[FEATURES[n][0]].notna().any()]
    X = pd.DataFrame(index=table.fips)
    for name in names:
        column, log = FEATURES[name]
        values = table[column].astype(float).values
        values = np.log1p(values) if log else values
        values = np.where(np.isnan(values), np.nanmedian(values), values)
        X[name] = (values - values.mean()) / values.std()
    return X


def loso_scores(model, X, y, states):
    """Out-of-fold scores with each state held out in turn."""
    return cross_val_predict(model, X, y, groups=states, cv=LeaveOneGroupOut(), method="predict_proba")[:, 1]



def validate(table, labels):
    """Leave-one-state-out AUC and average precision for each feature set. Returns a report."""
    labeled = labels.merge(table[["fips", "state", "dc_existing_count", "dc_proposed_count"]], on="fips")
    X_all = feature_matrix(table)
    X, y, states = X_all.loc[labeled.fips], labeled.label.values, labeled.state.values
    both = labeled.has_permitted_facility.values  # counties where a negative label is possible
    others = [c for c in X.columns if c not in EXPOSURE]
    logit = LogisticRegression(C=1.0, max_iter=1000)
    boosted = HistGradientBoostingClassifier(random_state=0)
    runs = {"logistic_all_features": (logit, list(X.columns)),
            "logistic_without_dc_counts": (logit, others),
            "logistic_dc_counts_only": (logit, EXPOSURE),
            "boosted_all_features": (boosted, list(X.columns)),
            "boosted_without_dc_counts": (boosted, others)}
    metrics, out_of_fold = {}, {}
    for name, (model, columns) in runs.items():
        out_of_fold[name] = scores = loso_scores(model, X[columns], y, states)
        metrics[name] = {"auc": round(float(roc_auc_score(y, scores)), 3),
                         "average_precision": round(float(average_precision_score(y, scores)), 3)}
    # The cleanest test: only counties where both labels are possible, and no count features.
    for name, model in (("logistic", logit), ("boosted", boosted)):
        scores = loso_scores(model, X[others][both], y[both], states[both])
        metrics[f"{name}_without_dc_counts_permitted_subset"] = {
            "auc": round(float(roc_auc_score(y[both], scores)), 3),
            "average_precision": round(float(average_precision_score(y[both], scores)), 3)}

    # What the full logistic model would say about every county, to show why it can't ship.
    # Labeled counties take their out-of-fold score, so no county is scored by a model that saw it.
    logit.fit(X, y)
    score = pd.Series(logit.predict_proba(X_all)[:, 1], index=X_all.index)
    score.loc[labeled.fips] = out_of_fold["logistic_all_features"]
    percentile = score.rank(pct=True)
    is_labeled = X_all.index.isin(labeled.fips)
    no_facility = labeled[(labeled.dc_existing_count == 0) & (labeled.dc_proposed_count == 0)]
    best = max(m["auc"] for name, m in metrics.items() if "without_dc_counts" in name)
    return {
        "labels": {"positive": int(y.sum()), "negative": int((1 - y).sum()),
                   "states": int(len(set(states))), "positive_share": round(float(y.mean()), 3)},
        "permitted_subset": {"counties": int(both.sum()), "positive_share": round(float(y[both].mean()), 3)},
        "features": list(X.columns),
        "leave_one_state_out": metrics,
        "logistic_coefficients": {k: round(float(v), 3) for k, v in zip(X.columns, logit.coef_[0])},
        "labeled_counties_with_no_facility": {"count": len(no_facility),
                                              "positive_share": round(float(no_facility.label.mean()), 3)},
        "named_case_percentile": {name: round(float(percentile[f]), 3) for f, name in NAMED_CASES.items()},
        "median_score_labeled": round(float(score[is_labeled].median()), 3),
        "median_score_unlabeled": round(float(score[~is_labeled].median()), 3),
        "auc_without_dc_counts": best,
        "decision": "dropped" if best < MIN_AUC else "revisit",
    }


if __name__ == "__main__":
    labels, unmatched = build_labels("data/raw")
    labels.to_csv(LABELS, index=False)
    report = validate(pd.read_parquet("data/processed/county_features.parquet"), labels)
    report["unplaced_seed_rows"] = unmatched.fillna("").to_dict("records")
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
