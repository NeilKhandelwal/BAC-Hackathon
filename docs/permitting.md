# Permitting risk: method

Output: the permitting columns in `docs/schema.md`.

## Scope

Permitting risk is the chance that required approvals delay or block a
greenfield campus. It has five scored parts. Power interconnection is
scored in the grid pillar, not here.

| Part | Column | Method |
| --- | --- | --- |
| Discretionary land-use approval | `permitting_discretionary_risk` | logistic regression, below |
| Air permit for backup generation | `air_nonattainment_count` | EPA Green Book lookup |
| Water rights | `water_permit_risk` | state table lookup |
| State policy | `state_policy_risk` | state table lookup |
| Wetlands and habitat | `pct_forest_wetland` | NLCD, stretch |

Not modeled: zoning. No national dataset of by-right industrial land
exists. Existing facility count stands in for "a permit was granted here
before." State this on the assumptions slide.

## Procedure

### 1. Labels (45 minutes)

Inputs: `data/raw/fractracker/ft_all.csv`, `data/processed/opposition_seed_labels.csv`.

1. Positive county: any seed row with status cancelled, withdrawn, or
   delayed, or any FracTracker facility with `community_pushback == Yes`.
2. Negative county: has a FracTracker facility with status Operating,
   Approved, or Expanding, and no positive row.
3. All other counties are unlabeled. The model predicts for them.
4. Map county names to FIPS with `etl/fips.py`. Log unmatched names.
5. Write `data/processed/permitting_labels.csv` with `fips, label`.

Check: roughly 300 positives and 400 to 500 negatives. If either is under
150, stop and report.

### 2. Features (30 minutes)

From the county table, standardized:

- `log1p(pop_density_per_sqkm)`
- `log1p(dc_existing_count)`, `log1p(dc_proposed_count)`
- `drought_share_weeks_d2plus`, `nri_drought_score`
- `log1p(queue_active_mw_clean)`
- `moratorium_state_active`
- `median_household_income`
- `hdd_hist` (keeps the model from learning region alone)
- `pct_cropland` if present

Excluded because they are outcomes of opposition: `dc_pushback_count`,
`moratorium_active`, `moratorium_pending`.

### 3. Fit and validate (90 minutes)

1. Fit L2 logistic regression with scikit-learn.
2. Validate leave-one-state-out. Report pooled AUC.
3. Fit a gradient-boosted model with the same folds. Keep logistic unless
   the boosted AUC is at least 0.03 higher.
4. Calibrate with isotonic regression on the out-of-fold predictions.
5. Named-case check. These counties should land in the top third:
   Pima AZ, Prince William VA, Monroe GA, Porter IN, Cass MO. Record ranks.
6. Decision rule:
   - AUC 0.70 or above: report as a model.
   - 0.60 to 0.70: report as a risk index.
   - Below 0.60: drop the model. Use an equal-weighted index of the same
     standardized features and say so.

### 4. Outputs (30 minutes)

For every county:

- `permitting_discretionary_risk`: calibrated probability.
- `permitting_drivers`: three features with the largest coefficient times
  standardized value.

Write `research/permitting_model.md` with AUC, coefficients, the named-case
table, and the decision taken in step 3.6.

### 5. Lookup tables (60 minutes)

Commit as small CSVs in `data/processed/`:

| File | Rows | Source |
| --- | --- | --- |
| `air_nonattainment.csv` | county FIPS, ozone, PM2.5 | EPA Green Book county download |
| `state_water_regime.csv` | 49 | water law references; Arizona AMAs and other managed groundwater areas |
| `state_policy.csv` | 49 | NCSL data center bill tracker, FracTracker state moratoria, state tax statutes, utility tariff filings |

Each row carries a `source_url`.

### 6. Optional: news signal (only if BigQuery is set up)

Add county news volume and tone from `etl/gdelt_gkg_county.sql` as two
extra features. Refit. Report the AUC with and without them. Keep them only
if AUC rises by 0.02 or more.

## Pathway tier

The engine derives `permitting_pathway` per county. Durations are stated
assumptions from industry reporting, not model output.

| Tier | Condition | Assumed duration |
| --- | --- | --- |
| established | `dc_existing_count >= 3` and risk below 0.33 | 6 to 12 months |
| discretionary | not established and risk below 0.66 | 12 to 24 months |
| contested | risk 0.66 or above, or nonattainment, or `water_permit_risk == 2`, or `state_policy_risk >= 2` | 24 months or more, denial possible |

## Mitigation map

Shown on the county card for the top driver.

| Driver | Mitigation |
| --- | --- |
| drought, water rights | dry cooling, recycled-water agreement |
| nonattainment | battery or fuel-cell backup instead of diesel |
| low density, cropland | site on previously developed land, setbacks, community benefit agreement |
| existing facility density | noise enclosures, shared-infrastructure commitments |
| state policy | tariff structure that protects residential rates, early public announcement |
