# Permitting model: tested and dropped

The labels can mark a county negative only if it already has a data center,
so facility counts encode the label. Without those counts, no feature set
beats chance by a useful margin at predicting opposition (AUC 0.48
logistic, 0.55 boosted, leave-one-state-out). On the counties where either
label is possible, the best run reaches 0.59, still under the 0.60 bar.

Decision: `permitting_discretionary_risk` and `permitting_drivers` stay
null. The permitting pillar scores the three sourced columns: air
nonattainment, water permit risk, and state policy risk. No ML output
ships in the ranking.

Reproduce: `python -m etl.permitting`. It writes
`data/processed/permitting_labels.csv` and
`data/processed/permitting_validation.json`.

## Labels

Built per `docs/permitting.md` step 1 from FracTracker and the seed label
table.

| Class | Counties | Definition |
| --- | --- | --- |
| Positive | 298 | a seed project was cancelled, withdrawn, or delayed, or a FracTracker facility has `community_pushback == Yes` |
| Negative | 149 | has an operating, approved, or expanding facility and no positive row |
| Unlabeled | 2,662 | everything else |

Labeled counties span 46 states. Two thirds are positive, so a random
ranking has an average precision of 0.667.

FracTracker records pushback as Yes or Unknown, never No. A negative county
is one with no recorded opposition, not one with confirmed acceptance.

## Validation

Leave-one-state-out, pooled out-of-fold scores, 447 labeled counties.

| Run | AUC | Average precision |
| --- | --- | --- |
| Logistic, all nine features | 0.721 | 0.791 |
| Logistic, without the two facility counts | 0.477 | 0.636 |
| Logistic, the two facility counts alone | 0.693 | 0.753 |
| Boosted trees, all nine features | 0.790 | 0.879 |
| Boosted trees, without the two facility counts | 0.553 | 0.712 |
| Logistic, without the counts, permitted subset | 0.572 | 0.504 |
| Boosted trees, without the counts, permitted subset | 0.585 | 0.549 |

The permitted subset is the 275 labeled counties that have at least one
operating, approved, or expanding facility. Both labels are possible there,
so it is the fairest test. 46 percent of the subset is positive, so a
random ranking has an average precision of 0.458. The runs beat that by a
small margin and stay under an AUC of 0.60.

The nine features are population density, existing facility count,
proposed facility count, drought weeks, NRI drought score, clean queue MW,
state moratorium, median household income, and heating degree days.
Cropland share is not in the county table.

## Why the headline AUC is not real

The two facility counts carry all of the skill, and they carry it because
of how the labels are built, not because they predict opposition.

- A county can be negative only if it has an operating, approved, or
  expanding facility. A county with no such facility that appears in the
  labels is positive by definition.
- All 63 labeled counties with zero existing and zero proposed facilities
  are positive.
- Labeled counties with no existing facility are 84 percent positive. With
  at least one, 41 percent.
- The logistic coefficient on existing facility count is negative (-0.43).
  That reflects the label rule, not a finding that hubs meet less
  opposition.

Applied to all counties, the fitted model gives an unlabeled county a
median score of 0.62, against 0.72 for labeled ones scored out of fold. It says a county with
no data center is more likely than not to see opposition. That is the
two-thirds base rate of the label set, not information about the county.
The boosted model with isotonic calibration is worse: it scores three
quarters of all counties at or near 1.0.

## Named cases

Percentile of each county among all 3,109 under the full logistic model.
Each labeled county, including these five, takes its out-of-fold score from
a model that did not see its state. The method asks for the top third.

| County | Percentile | Top third |
| --- | --- | --- |
| Pima, AZ | 0.93 | yes |
| Monroe, GA | 0.97 | yes |
| Porter, IN | 0.98 | yes |
| Cass, MO | 0.72 | yes |
| Prince William, VA | 0.00 | no |

Prince William has one of the best-known opposition fights in the country
and many existing facilities. The model ranks it near the bottom because
existing facilities push the score down.

## Decision

`docs/permitting.md` step 3.6 says to drop the model below an AUC of 0.60.
The AUC that counts is the one without the facility counts: 0.477 and
0.553 on all labeled counties, 0.572 and 0.585 on the permitted subset. All
four are under 0.60. The model is dropped.

The method's fallback is an equal-weighted index of the same features. It
was built and rejected:

- It needs a direction for each feature, and those are assumptions.
- Its AUC against the labels is 0.41, below chance.
- Facility counts dominate it. It ranks Loudoun, Prince William, Maricopa,
  and Washington County, OR as the riskiest counties in the country.

A null column is more honest than a score nobody can defend. The engine
treats null as unknown.

## What would fix it

Project-level outcomes with true negatives: projects that were approved and
drew no opposition. FracTracker does not record those. With them, the unit
of analysis becomes the project, facility counts stop encoding the label,
and county features can be tested fairly.

## Seed rows not placed in a county

Six of 154 positive seed rows have no usable county. They are left out, not
fixed by hand.

| State | County in source | Project |
| --- | --- | --- |
| GA | Carroll and Haralson | Project Bus |
| KS | Ogle | LFF Industrial |
| NJ | none | American Tower Data Center |
| PA | none | Silver Spring Township Data Center |
| TX | none | Priority Power Management Data Center |
| WI | none | Microsoft Project Nova |
