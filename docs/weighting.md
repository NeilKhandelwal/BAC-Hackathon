# Pillar weighting: methods and results

This document answers the question a judge will ask first: why these
weights? It compares five ways to set or test pillar weights, shows where
they agree, and recommends a county to feature. The process, decisions, and
interim results are in `docs/weighting_log.md`. Code and outputs are in
`scratch/weighting/`. Charts are in `docs/img/`.

## Recommendation

**Feature Clark County, WA.** Two alternatives each win under a stated
condition.

| County | Role | Wins when |
| --- | --- | --- |
| Clark, WA | Featured | The base case. It leads the dollar ranking of the shortlist and the six-method consensus without entropy, and it beats Franklin in both Monte Carlo bounds. Clark's lead holds only if it can energize within about 2.25 years. |
| Franklin, NY | Alternative 1 | Any one of three: the carbon price is above about $200/t with both counties at state-average power ($166/t if delay costs $10M per month); Clark's new-load rate is above about $104/MWh; or Clark waits about 2 months longer for power than the queue proxy says. |
| Grant, WA | Alternative 2 | Both of two: its interconnection wait shrinks to Clark's level, and its power costs about $2/MWh less than Clark's. With its current queue, it needs power about $18/MWh cheaper than Clark's. |

**Clark leads in every scenario tested, but not decisively.** At a $190/t
carbon price, Clark's 25-year cost is $49M below Franklin's, about 1.4%. If
Clark pays BPA's new-load rate, its breakeven against Franklin is
$104/MWh, the middle of BPA's $80 to $132 range. Present Clark as the
leader of a close race, not a runaway winner.

**Featuring Clark means reworking the deck.** `docs/deck.md`,
`docs/demo_script.md`, `research/implementation.md`, and `research/risk.md`
are built around Grant. This branch doesn't change them. The team needs to
decide whether to switch the featured county or to present Grant as the
engine's pick and Clark as the dollar pick.

### Diligence items for Clark

The repo has no research on Clark's utility or sites. These are the first
things a judge will raise. Each needs a source before a slide claims it.

1. **Power availability.** Clark's 1-month time-to-power charge comes from
   a generation-queue age of 2.09 years. If a 300 MW load waits more than
   about 2.25 years, Franklin passes it. With a 1.5-year queue baseline,
   Franklin is #1 and Clark is 6th.
2. **Nearby generation.** Plants within 100 km total 4.7 GW, against
   16.2 GW for Grant. The gate needs 1.5 GW.
3. **Land.** Clark's land pillar is at the 22nd percentile because the
   county is suburban (314 people per km²). That's a density proxy. A
   150-acre campus is about 0.04% of the county's 1,628 km², so parcel
   availability is a diligence item, not a disqualifier.
4. **Fiber.** 29% of locations have fiber. That measures homes, not
   backbone access.
5. **No existing cluster.** FracTracker lists no data centers in Clark.
   Washington County, OR, across the Columbia River, has 9.

## The problem

The balanced preset's pillar weights were set by judgment. The #1 county
changed from Berkshire, MA to Grant, WA when the cost pillar went from about
2.6% of the composite to 15%. The same change also corrected
Massachusetts' closed data center tax exemption, so the flip had two causes,
not one.

## The framework: screen with the engine, rank in dollars

The recommendation uses two stages.

1. **Screen and shortlist with the engine.** The gates remove 1,544 of
   3,109 counties. The shortlist keeps the counties that at least 1% of
   random weightings put in the engine's top 10, with the floor off: 161
   counties. That rule doesn't depend on any single set of weights.
2. **Rank the shortlist in dollars and tonnes.** The monetized model prices
   each shortlisted county's 25-year cost, including carbon at a stated
   price.
3. **Test robustness.** Monte Carlo varies the model's prices and delays.
   SMAA varies the engine's weights.

**Why dollars do the ranking.** Two results show that percentile pillars
can't stand in for physical units:

- **The carbon example.** Franklin NY emits 2.7 times less CO2 than Grant
  WA: 260 against 700 thousand tonnes a year. In the engine, their
  energy_carbon pillars sit at the 97th and 94th percentiles. The pillar
  mixes grid carbon with renewable share, clean queue capacity, and clean
  plants within 100 km, where Grant scores near the top. Percentile scoring
  compresses a large physical gap into three points.
- **The weights don't transfer.** Running the engine with the monetized
  model's own implied weights (cost 0.54, energy_carbon 0.37) gives a top
  10 of Oklahoma and Texas counties. It shares none of its top 10 with the
  dollar ranking.

The shortlist result holds across four shortlist rules. Clark is #1 in
dollars whether the threshold is 1% or 5%, with the floor on or off.
Franklin drops out when the floor is on, because it fails the floor on
cost.

## Methods

### Monetized total cost

For each gate-passing county, the model prices a 300 MW IT campus over 25
years at 7%. It counts energy at the state industrial price, carbon at the
eGRID subregion rate, water, hazard loss, time to power, and moratorium
delay. Each component's share of the variance in total cost across counties
is the weight the data implies for that pillar.

- **Why it's defensible:** weights come from dollars and stated prices,
  and every price is a parameter anyone can change.
- **Main limitation:** energy uses one price per state and carbon one rate
  per subregion, and together they carry about 90% of the variance. Time to
  power uses generation-queue age as a proxy, and 68% of counties are
  imputed. Fiber, land, and community aren't monetized.

### Monte Carlo over the monetized model

The Monte Carlo runs 1,000 draws. Each draw varies:

- price, ±20% independently per state
- carbon rate, ±20% independently per subregion
- delay cost, from $10M to $50M per month
- New York moratorium, from 8 to 20 months
- carbon price, from $100 to $300/t

- **Why it's defensible:** it shows whether the #1 survives uncertainty
  in the inputs that matter.
- **Main limitation:** counties that share a state and subregion move
  together, so it ranks clusters. Its head-to-head percentages are
  sampling error under the chosen ranges, not probabilities about the
  world.

### SMAA weight-space mapping

SMAA draws 5,000 weight vectors uniformly from every possible weighting of
the eight pillars. It records how often each county ranks #1 and lands in
the top 10.

- **Why it's defensible:** it doesn't pick weights at all. It shows which
  counties win under which value systems.
- **Main limitation:** a uniform draw treats land and community as likely
  to matter as cost. And it inherits the engine's percentile pillars.

### CRITIC

CRITIC derives objective column weights from each column's spread and its
correlation with the others. It runs on raw values winsorized at the 1st
and 99th percentiles and min-max scaled.

- **Why it's defensible:** it's a standard method and down-weights
  redundant columns.
- **Main limitation:** correlations here are mostly low, so CRITIC comes
  out close to equal weight per column. Summed into pillars, its weights
  follow column count. It gives cost 0.018, because the price has one value
  per state.

### Entropy

Entropy weights a column by how concentrated its values are.

- **Why it's defensible:** it's a standard objective method.
- **Main limitation:** here it's an artifact. It puts 0.198 of all weight
  on existing data center count, because 88% of counties have none, and
  its weights depend on which way a column is coded. Its top 10 is metros
  with existing clusters.

### Revealed preference

A logistic regression predicts whether a county already has a data center
from every scored column except that count.

- **Why it's defensible:** it shows what industry has chosen.
- **Main limitation:** population alone predicts almost as well (AUC
  0.855 against 0.905 for all columns). The existing fleet reflects past,
  latency-driven siting near metros. The weights also mostly run against
  the pillar direction for land (industry picks dense counties) and
  permitting.

### Consensus

The consensus is a Borda count across the six methods' top 20 lists.
Within each list, rank 1 earns 20 points.

- **Why it's defensible:** a county that ranks well under many methods
  doesn't depend on one weighting choice.
- **Main limitation:** it mixes methods of very different quality. It's
  a cross-check, not the primary ranking.

## Weights by method

| Pillar | Balanced (judgment) | Monetized at $190/t | CRITIC | Entropy | Revealed preference |
| --- | --- | --- | --- | --- | --- |
| energy_carbon | 0.153 | 0.372 | 0.180 | 0.268 | 0.173 |
| water | 0.119 | 0 | 0.121 | 0.037 | 0.125 |
| climate_resilience | 0.119 | 0.012 | 0.254 | 0.091 | 0.228 |
| grid_infrastructure | 0.153 | 0.077 | 0.150 | 0.430 | 0.083 |
| land | 0.068 | 0 | 0.044 | 0.008 | 0.129 |
| community | 0.085 | 0 | 0.136 | 0.141 | 0.146 |
| permitting | 0.153 | 0 | 0.096 | 0.024 | 0.056 |
| cost | 0.150 | 0.539 | 0.018 | 0.002 | 0.060 |

Chart: `docs/img/weights_by_method.png`.

How to read the table:

- **Monetized:** the variance shares at $190/t, with negative shares set
  to 0 and the rest renormalized. They are weights on dollars, not engine
  weights. Land and community get 0 because they aren't monetized.
- **CRITIC and entropy:** column weights summed by pillar, so pillars with
  more columns get more. Climate resilience has 8 columns; cost has 1.
- **The carbon-price effect:** the monetized weights move with the carbon
  price. At $0/t cost takes 0.89. At $300/t energy_carbon takes 0.67.

## Results

### Stage 2: the shortlist ranked in dollars

Top 10 of the 161-county shortlist, by 25-year cost with carbon at $190/t:

| Rank | County | Cost, $B | CO2, kt/yr | Engine floor | Balanced rank |
| --- | --- | --- | --- | --- | --- |
| 1 | Clark, WA | 3.496 | 678 | passes | 7 |
| 2 | Franklin, NY | 3.545 | 260 | fails | 986 |
| 3 | Clinton, NY | 3.577 | 261 | fails | 1,031 |
| 4 | Chautauqua, NY | 3.592 | 262 | fails | 1,123 |
| 5 | Niagara, NY | 3.674 | 268 | fails | 1,097 |
| 6 | Walla Walla, WA | 3.678 | 701 | passes | 18 |
| 7 | Chesterfield, SC | 3.682 | 667 | passes | 17 |
| 8 | Whitman, WA | 3.741 | 682 | passes | 3 |
| 9 | Marlboro, SC | 3.753 | 669 | passes | 28 |
| 10 | Oneida, NY | 3.808 | 262 | fails | 1,065 |

Grant, WA is 28th in the shortlist and 92nd of all gate-passing counties.

### Robustness

| Test | Clark, WA | Franklin, NY | Grant, WA |
| --- | --- | --- | --- |
| Monte Carlo #1, state-average prices | 26.6% | 24.7% | 0% |
| Monte Carlo #1, Clark and Grant on BPA rates | 27.2% | 20.1% | 0% |
| Monte Carlo top 3, BPA rates | 31.8% | 34.3% | 3.8% |
| SMAA #1, floor on | 6.7% | 0% (fails floor) | 12.4% |
| SMAA top 10, floor on | 29.6% | 0% | 50.5% |
| SMAA top 10, floor off | 20.6% | 24.3% | 34.9% |

What the robustness results show:

- **No county wins most draws or most weightings.**
- **Clark against Franklin:** Clark beats Franklin in 59% of Monte Carlo
  draws at state-average prices and 53% with BPA rates. The two runs are
  bounds. BPA's whole range sits above Washington's $66/MWh state average,
  while Franklin keeps New York's average because no New York new-load rate
  is sourced.
- **Clark against Grant:** Clark beats Grant in every draw. The two share
  a state price and a grid, and Grant has the longer queue and needs dry
  cooling.
- **What moves the race:** state electricity prices move the Clark and
  Franklin gap more than the carbon price, 46% of its variance against
  28%.

Charts: `docs/img/cost_vs_co2.png`, `docs/img/mc_winners.png`,
`docs/img/mc_winners_bpa.png`, `docs/img/smaa_acceptability.png`.

### Consensus

Borda count across five methods, entropy excluded:

| Rank | County | Points | Balanced | Monetized | SMAA | CRITIC | Revealed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Clark, WA | 50 | 7 | 1 | 5 | 27 | 103 |
| 2 | Whitman, WA | 49 | 3 | 10 | 1 | 78 | 660 |
| 3 | Grant, WA | 48 | 1 | 92 | 2 | 12 | 120 |
| 4 | Scott, IA | 44 | 6 | 611 | 7 | 6 | 122 |
| 5 | Washington, OR | 39 | 120 | 652 | 14 | 1 | 9 |
| 6 | Wayne, TN | 37 | 2 | 560 | 3 | 208 | 1,475 |
| 7 | Rock Island, IL | 31 | 200 | 1,099 | 9 | 2 | 106 |
| 8 | Grady, OK | 27 | 9 | 624 | 6 | 266 | 504 |
| 9 | Mayes, OK | 26 | 4 | 271 | 12 | 118 | 1,003 |
| 10 | Multnomah, OR | 26 | 1,005 | 412 | 271 | 4 | 12 |

With entropy included, Washington, OR moves to first (54 points), ahead of
Clark (50). That reflects how entropy weights columns, not a better site.
Franklin scores 19 points with or without entropy, held back by the engine
floor and by revealed preference.

## Method notes

- **Hazard cost understates hazard risk for a data center.** The monetized
  model prices hazards with FEMA NRI building expected-annual-loss rates
  times the campus asset value. Building loss rates cover physical damage
  only. They exclude downtime, lost revenue, and service-level penalties,
  which dominate the cost of an outage at a data center. Treat the hazard
  component as a floor.
- **The pillar floor is a judgment rule.** The engine ranks every county
  below the 10th percentile on any non-exempt pillar under every county
  that isn't. That threshold and the exemption of permitting were chosen,
  not derived. Floor membership doesn't depend on the weights unless a
  weight is zero, so no weighting method can lift a county over the floor.
  Franklin fails on cost: 6.5th percentile against 10.

## Assumptions and parameter defaults

- **Facility:** 300 MW IT load, load factor 0.8 (`etl/impact.py`).
- **Discounting:** 25 years at 7%, an annuity factor of 11.654.
- **PUE and WUE:** linear in cooling degree days, from `etl/impact.py`.
  The evaporative values come from Lei and Masanet; the dry-cooling PUE
  curve is an unsourced assumption there.
- **Cooling:** evaporative where Aqueduct water stress is 2 or lower,
  otherwise dry. PUE and carbon follow the choice. Dry everywhere is a
  sensitivity.
- **Energy price:** 2024 state average industrial price from EIA-861.
- **New-load rate:**
  - BPA's $80 to $132/MWh (`research/impact.md`) for Clark and Grant as a
    scenario.
  - No sourced new-load rate for New York, so Franklin stays at the state
    average.
- **Carbon:**
  - eGRID2023 subregion average rate, not marginal.
  - BPA-like supply at `BPA_CO2_LB_MWH = 212.458` (`etl/impact.py`).
  - Prices $0, $51, $190 (EPA 2023 social cost of carbon), and $300 per
    tonne.
- **Water:** $7 per 1,000 gallons times (1 + water stress). Unsourced
  assumption; $3 and $15 are sensitivities.
- **Hazard:** sum of NRI v1.20 building expected-annual-loss rates over 17
  hazards, times a $10B asset value.
  - Drought has no building rate and is excluded.
  - A missing rate counts as 0.
  - The sum matches NRI's composite rate to machine precision for 95% of
    counties.
- **Time to power:** queue median age beyond 2 years, times 12, times $25M
  per month, as a one-time cost at year 0.
  - Counties without a queue age (1,072 of 1,565) take the national median
    of 2.89 years.
  - Sensitivities: $10M and $50M per month, time to power off, and
    baselines of 1.5 and 2.5 years.
- **Moratorium:**
  - An active state or county moratorium costs 12 months at p=1. The basis
    for New York is 8 months left on Executive Order 62 (in effect through
    2027-06-04), plus about a 1/3 chance that the Responsible Data Center
    Development Act starts a fresh 12-month clock.
  - A pending moratorium costs 12 months at p=0.5, and recorded facility
    pushback 6 months at p=0.3.
  - Sensitivities: 8 and 20 months.
- **Not monetized:** fiber, land, community.
- **Monte Carlo:** 1,000 draws, seed 42, uniform ranges as listed under
  Methods. Multipliers are independent per state and per eGRID subregion.
  In the BPA run, Clark and Grant share one BPA rate draw, and BPA carbon
  has no multiplier.
- **SMAA:** 5,000 Dirichlet(1) draws over 8 pillars, seed 0, floor on and
  off.
- **CRITIC and entropy:** 35 scored columns with data, pillars.yaml
  transforms, winsorized at the 1st and 99th percentiles, min-max scaled,
  direction applied. Nulls take the column median for the weight
  calculation only.
- **Revealed preference:** L2 logistic regression, C = 1.0, median
  imputation and standardization inside stratified 5-fold cross validation,
  seed 0, trained on all 3,109 counties.
- **Consensus:** Borda over each method's top 20.
- **Shortlist:** SMAA top-10 acceptability of at least 1%, floor off.

## Reproduce

From the repo root, fetch the raw NRI table once:

```bash
python -c "from etl.adapters import nri; from pathlib import Path; nri.fetch(Path('data/raw'))"
```

Then run the scripts in order:

```bash
python scratch/weighting/monetize.py
python scratch/weighting/montecarlo.py
python scratch/weighting/smaa.py
python scratch/weighting/critic.py
python scratch/weighting/revealed.py
python scratch/weighting/consensus.py
```

Each writes its outputs to `scratch/weighting/out/` and its chart to
`docs/img/`.
