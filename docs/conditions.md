# Conditions spec

A conditions file is the input to the engine. It describes the facility the
user wants to build and how they want the engine to judge counties. The
engine is a pure function: `rank(features, conditions) -> results`. Same
features, same conditions, same answer.

Presets live in `engine/conditions/`. Users start from one and edit.

## Structure

```yaml
name: balanced                    # label shown in the UI and exports
description: >
  Even weights, moderate gates. The default demo profile.

facility:
  mw: 300                         # IT load; drives the queue-wait and MW-availability checks
  online_year: 2029               # with the current year, sets the tolerable queue wait
  cooling: dry                    # dry | evaporative | hybrid
  acres: 150                      # not scored yet; reserved for a land gate

horizon: 2026                     # 2026 | 2050. Selects which climate columns score.
scenario: rcp85                   # rcp45 | rcp85. Only used when horizon is 2050.

gates:                            # hard exclusions, applied before scoring
  states_include: []              # empty means all 48 + DC
  states_exclude: []
  max_grid_co2_lb_mwh: null       # null disables the gate
  min_renewable_share: null
  max_queue_median_age_years: 5   # a county whose active projects have waited longer is out
  min_nearby_capacity_multiple: 5 # plant MW within 100 km must be at least this times facility.mw
  max_water_stress_if_evaporative: 2   # Aqueduct bws_raw category; only applies when cooling is evaporative or hybrid
  hazard_percentile_max:          # exclude counties above this national percentile on each hazard
    nri_inland_flood_score: 90
    nri_coastal_flood_score: 90
    nri_wildfire_score: 95
    nri_hurricane_score: 95
    nri_tornado_score: null
  exclude_moratorium_active: true
  exclude_moratorium_state_active: false
  min_fiber_share_locations: 0.4
  max_permitting_risk: null       # 0-1, applied to permitting_discretionary_risk; null disables
  exclude_air_nonattainment: false   # true excludes counties with any ozone or PM2.5 nonattainment
  min_population: 5000            # proxy for workforce until a labor layer exists

weights:                          # must sum to 1; the engine renormalizes and warns
  energy_carbon: 0.18
  water: 0.14
  climate_resilience: 0.14
  grid_infrastructure: 0.18
  land: 0.08
  community: 0.10
  permitting: 0.18

pillar_floor_percentile: 20       # a county below this percentile on any pillar can't rank above a county that isn't. Set 0 to disable.

robustness:
  samples: 2000                   # Dirichlet draws around the weights
  concentration: 20               # higher means draws stay closer to the stated weights
  top_n: 10                       # "share of samples in the top N" is the robustness score

portfolio:
  sites: 1                        # 1 returns a ranked list; >1 returns a diversified set
  diversity_keys: [state, grid_subregion]
  diversity_penalty: 0.3          # score deduction per shared key with an already-chosen site

output:
  top_n: 10
  explain: true                   # include per-pillar breakdown, gate log, and nearest-miss reasons
  include_excluded: true          # list counties that failed a gate, and which gate
```

## Semantics

**Gates** run first and produce a log per county: passed, failed on which
gate, or unknown because the column is null. Unknown never excludes. The
results carry the gate log so the UI can show "why not."
`hazard_percentile_max` caps the national percentile of each hazard score.
Most hazards are zero for many counties (coastal flood is zero for about
2,700 inland counties), so a cap below that share excludes every exposed
county. The report lists `hazard_gate_nonzero_counties` so you can see
when that happens.

`min_nearby_capacity_multiple` is the only gate whose threshold depends on
the facility. A county fails when `plant_capacity_mw_100km`, the nameplate
capacity of power plants within 100 km of its centroid, is below the
multiple times `facility.mw`. With the default 5 and a 300 MW facility, a
county needs 1,500 MW nearby. It's a proxy for transmission and substation
capacity, not a load-flow study: it says power is generated nearby, not
that the grid can deliver it to a new 300 MW load.

**Horizon** swaps the climate columns. With `horizon: 2050`, `cdd_hist`
becomes `cdd_2050_<scenario>`, and the same for heating degree days and days
above 95F. Water stress uses `water_stress_2050` when present. Everything
else is held at today's values and the deck says so. `horizon_delta`
is the 2050 composite minus the 2026 composite. It's relative by
construction: both are national percentiles, so warming that shifts every
county equally leaves it near zero. `rank_delta_2050` gives the rank
movement among gate-passed counties, and `explain` shows the raw change in
each swapped column.

**Pillars** are defined in `engine/pillars.yaml`, which maps each column to a
pillar, a direction (higher or lower is better), and an optional
transformation. Each column becomes a national percentile rank, direction
adjusted so 100 is always best. A pillar score is the mean of its columns'
percentiles, ignoring nulls. The composite is the weighted sum of pillar
scores, subject to the floor rule. Percentiles are computed over all
counties before gates run, so a county's scores don't change between
presets. A county with every column in a pillar null has a null pillar; its
composite renormalizes over its other pillars, and `coverage` shows the gap.

**Floor rule.** With `pillar_floor_percentile: 20`, counties are split into
those with every pillar at or above the 20th percentile and those with at
least one pillar below it. The first group always ranks above the second,
and within each group the weighted sum orders them. This enforces the
brief's "don't optimize for a single metric" without a nonlinear formula.
The floor compares the national percentile of each pillar score, not the
raw pillar score, because a mean of percentiles clusters near 50. A null
pillar never fails the floor.

**Robustness.** For each sample, draw a weight vector from a Dirichlet
distribution centered on the stated weights, recompute the ranking, and
record whether each county landed in the top N. The robustness score is the
share of samples where it did. Draws use alpha = `concentration` times the
weights times the number of pillars, so the mean draw equals the stated
weights. The floor rule applies in every draw. Set `robustness.seed`
(default 0) to change the reproducible draw. The headline map shows this, not the point
estimate.

**Portfolio.** Greedy. Pick the top county. For each remaining county,
subtract `diversity_penalty` times the number of `diversity_keys` it shares
with any already-chosen site, then pick the best. Repeat until `sites` are
chosen. Cheap, explainable, and it makes "three sites, three grids" a one-
toggle demo.

## Presets

| File | Intended user | What's different |
| --- | --- | --- |
| `balanced.yaml` | default demo | the values above |
| `speed_to_power.yaml` | developer with a 2028 deadline | grid_infrastructure 0.30, permitting 0.30; queue gate 3 years; permitting risk gate 0.6; state moratorium excluded |
| `sustainability_first.yaml` | hyperscaler with a 24/7 carbon-free commitment | energy_carbon 0.30, water 0.25, permitting 0.10; carbon gate 600 lb/MWh; evaporative cooling disallowed above water stress 1; horizon 2050 |

## CLI

```bash
python -m engine rank --conditions engine/conditions/balanced.yaml --features data/processed/county_features.parquet --out results/balanced.csv
python -m engine explain --conditions engine/conditions/balanced.yaml --fips 19161
```

Both read the manifest, warn about missing columns, and never make a
network call.

## Output

`rank` returns one row per county that passed the gates, sorted by
composite, with columns: `rank`, `fips`, `county_name`, `state`,
`composite`, one `pillar_<name>` column per pillar, `robustness`,
`coverage`, `floor_ok`, `permitting_discretionary_risk`, `permitting_pathway`, `horizon_delta` (composite under
2050 minus composite under 2026, when both can be computed), and
`top_reasons` (the three columns that contributed most). Excluded counties
are returned separately with `failed_gate`.
