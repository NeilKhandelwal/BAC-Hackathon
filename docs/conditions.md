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
  min_fiber_share_locations: 0.2 # share of broadband locations, mostly homes, with last-mile fiber; a weak proxy for backbone
  max_permitting_risk: null       # needs permitting_discretionary_risk; no model ships, so keep null
  exclude_air_nonattainment: false   # true excludes counties with any ozone or PM2.5 nonattainment
  min_population: 5000            # proxy for workforce until a labor layer exists
  max_pct_protected: null         # 0-1, PAD-US GAP 1-2 share of the county; null disables
  max_tribal_land_share: null     # 0-1, share inside federally recognized reservations or trust land; null disables

weights:                          # must sum to 1; the engine renormalizes and warns
  energy_carbon: 0.153
  water: 0.119
  climate_resilience: 0.119
  grid_infrastructure: 0.153
  land: 0.068
  community: 0.085
  permitting: 0.153
  cost: 0.15                      # industrial electricity price; the largest operating cost

pillar_floor_percentile: 10       # a county below this percentile on any pillar can't rank above a county that isn't. Set 0 to disable.
pillar_floor_exempt: [permitting] # pillars that score in the composite but never fail the floor

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
A gate key the engine doesn't recognize, or a gate whose column is missing
from the table, adds a warning to the report instead of passing silently.
`states_include` and `states_exclude` must be lists.

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
that the grid can deliver it to a new 300 MW load. It measures installed
generation, not spare capacity, so a county that just clears the gate still
scores low on the grid pillar.

**Horizon** swaps the climate columns. It must be 2026 or 2050, as a number
or numeric string; any other value is an error. With `horizon: 2050`, `cdd_hist`
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
`coverage` is the share of every column mapped in `engine/pillars.yaml` that
is non-null for the county, so columns absent from the table lower it too.

**Cost** is its own pillar: `industrial_price_cents_kwh`, the state average
industrial electricity price, lower is better. Energy is the largest
operating cost of a campus, and the brief asks for long-term economic
viability. As one of seven grid columns, price carried about 2.6% of the
composite; as a pillar it carries 15% in `balanced`, 18% in
`speed_to_power`, and 10% in `sustainability_first`. The floor applies to it
like any other pillar. It's a state average, so a new large-load tariff
could be higher.

**Industrial reuse and economic opportunity** are two separate additions.
`coal_retired_mw` scores in grid and infrastructure: a retired coal plant's
grid interconnection can be reused, which lets a project skip the queue for
a new high-voltage connection. It makes no claim about community attitudes.
`unemployment_rate_pct_2023` (higher is better), `pop_change_pct_since_peak`
(lower is better: a county further below its highest census count scores
higher), and `mfg_emp_share_1969` (higher is better: industrial legacy)
score in community. This is a stated value choice, not a prediction: the
brief lists economic development opportunities under community impact, and
a campus brings more benefit, and finds more available workforce, where jobs
are scarce and the county has declined against its own history. The
long-run measures replaced 2001-based ones, which put the Detroit and
Youngstown counties near the national median; the 1969 manufacturing share
puts them in the top fifth. The opposition model found no dependable link between these columns
and community pushback (`research/economic_development.md`), so the engine
doesn't use them to predict acceptance.

**State moratoria** are flagged, not excluded, unless
`exclude_moratorium_state_active` is true (only `speed_to_power` sets it).
A ranked county with `moratorium_state_active` carries the flag in the
ranked output, the app's shortlist and headline count, and a warning in
`explain` and the county detail panel: "State moratorium in effect. A
facility this size can't get state permits today." The flag comes from the
data column, so it follows whichever states the table marks. As of the
current table that's New York, where Executive Order 62, signed July 14,
2026, pauses state environmental permits for data centers of 50 MW or more
until a statewide environmental study finishes, about a year. Sources:
[Jones Day](https://www.jonesday.com/de/insights/2026/07/new-york-enacts-first-statewide-data-center-moratorium),
[Foley](https://www.foley.com/insights/publications/2026/08/new-york-just-pressed-pause-on-large-data-center-permitting/).
`explain` and the panel also show two unscored facts: whether the county
has an IRA energy community coal closure tract, and whether it's in an IRA
fossil fuel employment area.

**Floor rule.** With `pillar_floor_percentile: 10`, counties are split into
those with every pillar at or above the 10th percentile and those with at
least one pillar below it. The first group always ranks above the second,
and within each group the weighted sum orders them. This enforces the
brief's "don't optimize for a single metric" without a nonlinear formula.
The floor compares the national percentile of each pillar score, not the
raw pillar score, because a mean of percentiles clusters near 50. A null
pillar never fails the floor, and neither does a pillar weighted zero. A
lower floor trades protection against lopsided counties for stability: at
20, small differences on a value-choice column moved counties across the
floor and hundreds of ranks, so `balanced` uses 10. `speed_to_power` also
uses 10, and `sustainability_first` uses 15 as the strict preset. At 25 its
four highest composites sat below the floor.

`pillar_floor_exempt` lists pillars that still score in the composite but
can't fail a county on the floor. Robustness and `rank_delta_2050` use the
same rule. An unknown pillar name is an error. All three presets exempt
`permitting`, because the pillar is three coarse state-level integers (air
nonattainment, water permit risk, and state policy risk), and one step on
one of them moved a county 380 ranks.

**Robustness.** For each sample, draw a weight vector from a Dirichlet
distribution centered on the stated weights, recompute the ranking, and
record whether each county landed in the top N. The robustness score is the
share of samples where it did. Draws use alpha = `concentration` times the
weights times the number of pillars, so the mean draw equals the stated
weights. The floor rule applies in every draw. Set `robustness.seed`
(default 0) to change the reproducible draw. Only counties that pass the
gates and the floor can count as top N hits. When that field has `top_n`
counties or fewer, every one would score 1.0, so `robustness` is null and
the report warns. The headline map shows this, not the point
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
| `speed_to_power.yaml` | developer with a 2028 deadline | grid_infrastructure 0.246, permitting 0.246, cost 0.18; queue gate 3 years; fiber gate 0.3 instead of 0.2; state moratorium excluded |
| `sustainability_first.yaml` | hyperscaler with a 24/7 carbon-free commitment | energy_carbon 0.27, water 0.225, permitting 0.09, cost 0.10; carbon gate 670 lb/MWh, set in the gap between eGRID subregions NWPP (632) and AZNM (704), with no renewable-share gate so nuclear-led grids count as clean; evaporative cooling disallowed above water stress 1; pillar floor 15; horizon 2050 |

## CLI

```bash
python -m engine rank --conditions engine/conditions/balanced.yaml --features data/processed/county_features.parquet --out results/balanced.csv
python -m engine explain --conditions engine/conditions/balanced.yaml --fips 19161
```

Both read the manifest, warn about missing columns, and never make a
network call.

## Output

`rank` returns one row per county that passed the gates. Rows sort by floor
group first (every county with `floor_ok` true ranks above every county
without), then by composite. Columns:

- `rank`, `fips`, `county_name`, `state`
- one `pillar_<name>` column per pillar with data, then `composite` and
  `coverage`
- `floor_ok`
- `horizon_delta` (composite under 2050 minus composite under 2026) and
  `rank_delta_2050` (rank under 2050 minus rank under 2026 among
  gate-passed counties), both null when no 2050 column exists
- `top_reasons`: up to three columns above the national median that add
  most to the composite, as a semicolon list. It can be empty.
- `robustness`, null when too few counties pass the gates and the floor
- `failed_gates` (always empty here) and `unknown_gates`, semicolon lists
- `moratorium_state_active`, carried from the table unscored so the flag
  sits next to the score

The CLI writes these rows to `<out>.csv`, excluded counties with
`failed_gates` and `unknown_gates` to `<out>_excluded.csv`, and the run
summary (per-gate counts, `hazard_gate_nonzero_counties`, `weights_used`,
`moratorium_state_active_ranked`, warnings) to `<out>_report.json`. The engine doesn't emit a permitting
pathway or a permitting model score.
