# Pillar weighting: methods and results

This document answers the question a judge will ask first: why these
weights? It compares several ways to set or test pillar weights, prices
each site in dollars and tonnes, and recommends a county to feature. The
process, decisions, and interim results are in `docs/weighting_log.md`.
Code and outputs are in `scratch/weighting/`. Charts are in `docs/img/`.

Engine-based results (SMAA, CRITIC, entropy, revealed preference,
consensus, and the shortlist) are computed on `main` as of `b7ddfe6`, which
includes the queue-semantics correction. The dollar model gives identical
results before and after that merge.

Revision 1 adds a sales and use tax component, uses Grant County's own
power-timeline evidence in place of the queue proxy, and covers Neil's
review items. The tax component changed the recommendation.

## Recommendation

**Feature Grant County, WA, with Clark County, WA and Franklin County, NY
as conditional alternatives.**

With sales tax in the model, the three counties are within 1.1% of each
other over 25 years at a $190/t carbon price. The dollar model can't
separate them. The differences sit inside two uncertainties: the sales tax
rate at Clark's parcel, and how long Grant waits for power.

| County | 25-year cost at $190/t |
| --- | --- |
| Clark, WA (unincorporated, 8.0% sales tax) | $4.405B |
| Grant, WA (12-month delay, from its own evidence) | $4.452B |
| Franklin, NY (taxed) | $4.454B |

These costs and the gaps between the three don't depend on how other states
are treated. Their national ranks do, and two treatments bracket them:

- **Other states' refreshes exempt (base):** every state with an exemption
  flag in the repo's hand-coded `data/processed/state_policy.csv` exempts
  both initial and refresh purchases for 25 years. That's 91% of
  gate-passing counties, and the flags are mostly medium or low confidence.
  Clark, Grant, and Franklin rank 365th, 407th, and 410th.
- **Refreshes taxed everywhere:** every state taxes refreshes the way
  Washington's statute now does. The three rank 14th, 19th, and 22nd, and
  Umatilla, OR ranks first.

The Grant-Clark gap is $46M in both. Read the three-way comparison as solid
and the national ranks as unverified.

Grant is featured because it's the only one of the three whose power
timeline and tax status are both sourced:
- Grant's delay comes from Grant PUD's queue and transmission plans.
- Its exemption on initial equipment comes from the statute.
- Clark's lead ($46M) rests on a generation-queue proxy and on its parcel
  sitting outside Clark's transit area. Inside the transit area, Clark's
  tax rate is 8.7%, which adds about $80M and drops it below both Grant
  and Franklin.

Featuring Grant also matches the existing deck, demo script,
implementation plan, and risk assessment.

### What each county needs to win

| County | Wins when |
| --- | --- |
| Grant, WA (featured) | Grant PUD energizes the full 300 MW within about 10 months of the 2-year baseline (it beats Clark) or about 12 months (it beats Franklin). Its evidence-based estimate is 12 months, with a range of 8 to 18.5. Grant also wins if Clark's parcel is inside Clark's transit area (8.7%) or in Vancouver (8.9%). |
| Clark, WA | Its parcel is outside the transit area (8.0%), it energizes within about 2.25 years, and Grant's delay runs past about 10 months. Without any sales tax in the model, Clark is #1 nationally. |
| Franklin, NY | New York's Internet data center exemption, Tax Law §1115(a)(37), applies to the campus. Then Franklin is #1 nationally. That needs an operator that sells hosted services from the site, and the exemption must survive the repeal proposals. Without the exemption, Franklin beats Grant only if Grant's delay exceeds about 12 months, and beats Clark only if Clark's parcel is in the transit area. |

### Counties that rank above all three

With sales tax included, counties in states with full exemptions rank
above all three: Chesterfield SC, Kootenai ID, Marlboro SC, Florence SC,
Aiken SC, Emery UT, and Texas and Louisiana counties.

Treat them as a "verify before switching" item, not a featured pick:
- This rests on 37 state exemption flags in the repo's hand-coded state
  table. Those flags weren't verified for this analysis, and refreshes are
  assumed exempt.
- South Carolina's flag cites a 2026 bill version, not a statute.
- Idaho's flag is low confidence, and a restriction bill (HB 496) was
  enrolled there with its scope unverified.
- If equipment refreshes are taxed everywhere, as Washington now does,
  only states without a sales tax escape. Umatilla, OR then ranks first,
  and Clark, Grant, and Franklin rank 14th, 19th, and 22nd.

## Sales and use tax

### Washington

Washington's data center exemption covers eligible server equipment and
power infrastructure, including installation labor, at an eligible data
center in a rural county.
- **Statutes:** [RCW 82.08.986](https://app.leg.wa.gov/RCW/default.aspx?cite=82.08.986)
  and [RCW 82.12.986](https://app.leg.wa.gov/RCW/default.aspx?cite=82.12.986).
- **What it doesn't cover:** substations, racks, the building shell, and
  HVAC.
- **Rural county:** defined in [RCW 82.14.370](https://app.leg.wa.gov/RCW/default.aspx?cite=82.14.370)
  as a density under 100 people per square mile, a county with no city
  over 45,000, or a county under 225 square miles.
- **Grant qualifies:** 40.1 people per square mile in 2026 per the
  Office of Financial Management's
  [rural designation workbook](https://ofm.wa.gov/wp-content/uploads/2026/09/ofm_april1_rural_designations.xlsx).
- **Clark doesn't:** 875 per square mile, Vancouver is far over 45,000,
  and the county is 628.5 square miles.
- **Clark fails the urban route too.** [RCW 82.08.9861](https://app.leg.wa.gov/RCW/default.aspx?cite=82.08.9861)
  needs a county over 800,000.
- **DOR's workgroup agrees.** Its
  [December 2025 preliminary report](https://dor.wa.gov/sites/default/files/2025-12/2025DataCntrWrkgrpPrelimReport.pdf)
  (Executive Order 25-05) lists Clark among the counties excluded from both
  exemptions, in adopted finding T.6. The "cannot qualify" sentence in that
  report comes from a recommendation that failed 11-12; cite T.6 instead.
- **Since July 1, 2026, replacement server equipment is no longer
  eligible** (ESSB 6231, 2026 c 266;
  [final bill report](https://lawfilesext.leg.wa.gov/biennium/2025-26/Pdf/Bill%20Reports/Senate/6231-S.E%20SBR%20FBR%2026.pdf)).
  The model therefore exempts Grant's initial equipment and taxes its
  refreshes.
- **Conditions:** at least 100,000 square feet, 35 family-wage jobs
  within six years, and green building certification within three years.
  A 300 MW campus would plausibly meet them.

### New York

New York exempts equipment that an Internet data center operator buys
for Internet website services sold to customers.
- **Sources:** Tax Law §1115(a)(37) and (y); bulletin
  [TB-ST-405](https://tax.ny.gov/pubs_and_bulls/tg_bulletins/st/internet_data_centers.htm);
  memo [TSB-M-00(7)S](https://www.tax.ny.gov/pdf/memos/sales/m00_7s.pdf).
- **A cloud or colocation operator selling hosting from the site**
  plausibly qualifies.
- **An AI training campus with no hosted services for sale** probably
  doesn't. No guidance addresses that case, so it's a ruling question.
- **Repeal:** proposed in S9288 (referred to committee in February 2026)
  and by the governor in September 2026. Neither has passed.
- **IDA abatements** are discretionary, not statutory. Franklin County's
  IDA policy is unverified.
- **The model taxes Franklin in the base case** and shows the exempt case
  as a sensitivity.

### Rates

All rates are combined state plus local.
- **States:** Tax Foundation
  [midyear 2026](https://taxfoundation.org/data/all/state/2026-sales-tax-rates-midyear/)
  combined rates (`scratch/weighting/sales_tax_rates.csv`).
- **Washington counties:** WA DOR Q4 2026 unincorporated rates
  ([CSV](https://dor.wa.gov/taxes-rates/sales-use-tax-rates/lsu-quarterly-tax-rates.csv)).
  Clark 8.0% (8.7% inside the transit area, 8.9% in Vancouver), Grant 8.2%.
- **Franklin, NY:** 8.0%, from
  [Publication 718](https://www.tax.ny.gov/pdf/publications/sales/pub718.pdf).

Tax Foundation's state averages are population-weighted, so they overstate
rural rates.

### The tax component

- **Formula:** taxable equipment ($4B of IT and electrical equipment per
  purchase) times the county's combined rate.
- **Timing:** bought at year 0 and again every 5 years within the 25-year
  horizon, discounted at 7%.
- **Exempt counties** pay 0 on exempt purchases.
- **Size:** at 8% and a 5-year refresh, a fully taxed county pays $910M
  in present value. Grant pays $604M on refreshes only.
- **The tax base is an assumption.** $4B per purchase and a 5-year
  refresh were set in the revision request. Neither is sourced. The refresh
  cycle has 4- and 6-year sensitivities; the $4B base has none. Together
  they drive a swing of up to about $1B per county, and sales tax is the
  second-largest variance component at $0 carbon (0.24).
- **How the tax base relates to the hazard asset value.** The hazard
  component uses a $10B asset value: the whole campus exposed to physical
  loss, including the building, cooling, and electrical plant. The tax
  component uses $4B: the taxable IT and electrical equipment bought in one
  purchase cycle, a subset of capex that is bought again at each refresh.
  They measure different things, so they don't contradict. Both are
  assumptions.
- **Pillar:** the component maps to permitting, where the engine scores
  the exemption inside `state_policy_risk`. That mapping is a choice; it
  could also map to cost.

### With and without tax, and by refresh cycle

Ranks among the 1,565 gate-passing counties at $190/t:

| Case | Clark | Franklin | Grant | #1 |
| --- | --- | --- | --- | --- |
| No sales tax | 1 | 2 | 32 | Clark, WA |
| Tax, 5-year refresh (base) | 365 | 410 | 407 | Chesterfield, SC |
| Tax, 4-year refresh | 680 | 752 | 755 | Chesterfield, SC |
| Tax, 6-year refresh | 296 | 349 | 342 | Chesterfield, SC |
| Tax, Clark parcel at 8.7% | 447 | 409 | 406 | Chesterfield, SC |
| Tax, Clark parcel at 8.9% | 473 | 409 | 406 | Chesterfield, SC |
| Tax, New York exempt | 394 | 1 | 436 | Franklin, NY |
| Tax, refreshes taxed in every state | 14 | 22 | 19 | Umatilla, OR |

BPA Monte Carlo, with Clark and Grant on BPA's $80 to $132/MWh new-load
rate, 1,000 draws:

| Case | Clark #1 / top 3 | Franklin #1 / top 3 | Grant #1 / top 3 | Clark beats Grant |
| --- | --- | --- | --- | --- |
| No sales tax | 27.2% / 31.8% | 20.1% / 33.9% | 0% / 9.8% | 100% |
| Tax, 5-year refresh | 0.7% / 2.4% | 0.3% / 0.6% | 0.9% / 1.4% | 73% |
| Tax, 4-year refresh | 0.1% / 0.6% | 0% / 0.1% | 0.3% / 0.4% | 74% |
| Tax, 6-year refresh | 1.4% / 3.5% | 0.7% / 1.5% | 1.2% / 2.5% | 72% |
| Tax, Clark parcel at 8.7% | 0.3% / 1.6% | 0.3% / 0.6% | 1.0% / 1.5% | 55% |
| Tax, New York exempt | 0.1% / 0.6% | 29.7% / 37.6% | 0.2% / 0.2% | 73% |

With tax, Chesterfield SC (21%) and Kootenai ID (14%) take most #1 draws.

## The framework: screen with the engine, rank in dollars

1. **Screen and shortlist with the engine.** The gates leave 1,565 of
   3,109 counties. The shortlist keeps the 162 that at least 1% of random
   weightings put in the engine's top 10, with the floor off.
2. **Rank the shortlist in dollars and tonnes** with the monetized model.
3. **Test robustness** with Monte Carlo over the model's prices and delays,
   and SMAA over the engine's weights.

With sales tax, stage 2's #1 is Chesterfield, SC. Clark, Grant, and
Franklin rank 73rd, 78th, and 80th in the shortlist. The framework
therefore points away from all three. That result rests on the unverified
state exemption flags described above.

**Why dollars do the ranking.** Two results show percentile pillars can't
stand in for physical units:
- **The carbon example.** Franklin NY emits 2.7 times less CO2 than Grant
  WA, but their energy_carbon pillars sit at the 97th and 94th
  percentiles.
- **The weights don't transfer.** Running the engine with the dollar
  model's own implied weights gives a top 10 that shares no counties with
  the dollar ranking.

## Neil's review items

National ranks in this section use the base tax case, where other states'
refreshes are exempt. Compare the three counties with each other, not with
the national list.

### Variance shares that can't go negative

Covariance shares can be negative. With variance as the value function, a
Shapley decomposition reproduces the covariance shares exactly, so it can't
fix that. Standalone variance shares and a Shapley decomposition with
standard deviation as the value function can't go negative. With sales tax
in the model:

| Carbon price | Method | Energy | Carbon | Sales tax | Time to power | Others |
| --- | --- | --- | --- | --- | --- | --- |
| $0 | covariance | 0.673 | 0 | 0.241 | 0.072 | 0.014 |
| $0 | standalone | 0.752 | 0 | 0.169 | 0.059 | 0.019 |
| $0 | Shapley (SD) | 0.611 | 0 | 0.242 | 0.096 | 0.051 |
| $190 | covariance | 0.545 | 0.230 | 0.156 | 0.067 | 0.001 |
| $190 | standalone | 0.469 | 0.376 | 0.105 | 0.037 | 0.012 |
| $190 | Shapley (SD) | 0.463 | 0.262 | 0.160 | 0.080 | 0.035 |
| $300 | covariance | 0.344 | 0.533 | 0.080 | 0.047 | -0.004 |
| $300 | standalone | 0.301 | 0.600 | 0.067 | 0.024 | 0.007 |
| $300 | Shapley (SD) | 0.335 | 0.461 | 0.114 | 0.063 | 0.027 |

**The order of the top components doesn't change across the three
methods at any carbon price.** At $0 and $190 the order is energy, then
carbon, then sales tax, then time to power. At $300, carbon leads energy.
Only the small components (water, hazard, moratorium) reorder.

With tax in the model, energy and carbon together carry 0.67 of the
variance at $0, 0.78 at $190, and 0.88 at $300. The balanced preset gives
them 0.30.

### Time to power

1,072 of 1,565 gate-passing counties have no queue age and take the
national median. Ranks at $190/t with tax:

| Treatment of imputed counties | Clark | Franklin | Grant | #1 |
| --- | --- | --- | --- | --- |
| National median (base) | 365 | 410 | 407 | Chesterfield, SC |
| Charged $0 | 666 | 726 | 721 | Oconee, SC |
| Excluded | 183 | 192 | 191 | Chesterfield, SC |

The three move together, and their order holds in all three cases.

### Grant's row

Grant's time to power now comes from its own evidence, not the queue
proxy (`research/implementation.md`, `research/risk.md`):
- The first phase follows the 2027 Quincy transmission project.
- Full load needs the 2029 Wanapum-to-Quincy line.
- About 800 MW of large-load requests are queued ahead.
- New supply takes 2 to 2.5 years from contract.

From October 2026, that puts full load around 2029: about 12 months past
the 2-year baseline. The range is 8 months (the 2029 line lands mid-year
on time) to 18.5 months (the queue or supply slips, matching the proxy).
That's an inference from the evidence, not a utility commitment. **No
other county has equivalent evidence;** every other county uses the queue
proxy.

| Grant's delay | Grant's rank | Grant minus Clark | Grant minus Franklin |
| --- | --- | --- | --- |
| 8 months (evidence low) | 316 | -$54M | -$103M |
| 12 months (evidence central, base) | 407 | +$46M | -$3M |
| 18.5 months (evidence high, equals the proxy) | 646 | +$209M | +$160M |

Grant breaks even with Clark at 10.2 months and with Franklin at 12.1
months.

### Cooling

**County-specific cooling is a modeling choice.** The model uses
evaporative cooling where Aqueduct water stress is 2 or lower, and dry
cooling elsewhere. That choice favors Clark (water stress 0) over Grant
(3.6). With dry cooling everywhere, Clark still costs $35M less than Grant
at $190/t with tax (ranks 298 and 326).

### Hazard asset value

| Asset value | Clark | Franklin | Grant |
| --- | --- | --- | --- |
| $10B (base) | 365 | 410 | 407 |
| $3B | 383 | 438 | 460 |

Hazard loss is under 2% of the variance, so the asset value barely moves
the order.

### One table across methods

Top 10 and the ranks of four counties among the 1,565 gate passers:

| Method | Top 10 | Grant | Clark | Franklin | Berkshire |
| --- | --- | --- | --- | --- | --- |
| Balanced | Grant WA, Wayne TN, Whitman WA, Mayes OK, Scott IA, Benton WA, Clark WA, Scott TN, Adair OK, Grady OK | 1 | 7 | 952 | 1,047 |
| Monetized, $190/t with tax (other states' refreshes exempt) | Chesterfield SC, Kootenai ID, Marlboro SC, Florence SC, Aiken SC, Emery UT, El Paso TX, Grayson TX, Bossier LA, Houston TX | 407 | 365 | 410 | 1,552 |
| SMAA (rank-1, floor on) | Whitman WA, Grant WA, Wayne TN, Luzerne PA, Clark WA, Trumbull OH, Scott IA, Grady OK, Rock Island IL, Mayes OK | 2 | 5 | never top 10 | never top 10 |
| CRITIC | Rock Island IL, St. Joseph IN, Dakota MN, Henry IL, Washington OR, Scott IA, Ramsey MN, Onondaga NY, Cass MI, Winnebago IL | 11 | 48 | 34 | 204 |
| Entropy | Clark NV, Bexar TX, Milam TX, Berks PA, Cook IL, Mecklenburg VA, Salt Lake UT, St. Louis MO, El Paso CO, Will IL | 41 | 462 | 251 | 172 |
| Revealed preference | Maricopa AZ, Dallas TX, Hamilton OH, Wayne MI, Tarrant TX, Montgomery PA, Bexar TX, Clark NV, Salt Lake UT, Allegheny PA | 148 | 92 | 452 | 974 |
| Consensus (Borda, no entropy) | Grant WA, Scott IA, Whitman WA, Wayne TN, Rock Island IL, Clark WA, Mayes OK, Chesterfield SC, Luzerne PA, Grady OK | 1 | 6 | no points | no points |

How to read the table:
- **"Never top 10" and "no points" are tie groups, not ranks.** The CSV
  shows them as 271 and 79.
- **Grant's consensus #1 is mechanical.** With tax, the dollar top 20 is
  counties no other method ranks, so Clark lost its 20 points from the
  dollar method. It isn't new evidence for Grant.
- **With entropy included, Grant still leads the consensus;** Clark is 9th.

## Methods

### Monetized total cost

For each gate-passing county, the model prices a 300 MW IT campus over 25
years at 7%. It counts energy, carbon at a stated price, water, hazard
loss, time to power, moratorium delay, and sales tax on equipment. Each
component's share of cross-county variance is the weight the data implies.

- **Why it's defensible:** weights come from dollars and stated prices.
- **Main limitation:** energy uses one price per state and carbon one
  rate per subregion. Time to power uses a generation-queue proxy everywhere
  except Grant. The sales tax rests on unverified state flags outside WA
  and NY. Fiber, land, and community aren't monetized.

### Monte Carlo

The Monte Carlo runs 1,000 draws. Each varies state price and subregion
carbon rate by ±20%, delay cost from $10M to $50M per month, New York
moratorium length from 8 to 20 months, and carbon price from $100 to
$300/t.

- **Why it's defensible:** it tests whether the order survives
  uncertainty in the inputs that matter.
- **Main limitation:** it ranks state and subregion clusters, and its
  percentages are sampling error under chosen ranges.

### SMAA

SMAA draws 5,000 weight vectors uniformly over the eight pillars and
records how often each county ranks #1 and lands in the top 10.

- **Why it's defensible:** it picks no weights at all.
- **Main limitation:** it inherits the engine's percentile pillars.

### CRITIC and entropy

Both derive objective column weights from raw values winsorized at the 1st
and 99th percentiles and min-max scaled.

- **Why they're defensible:** they're standard objective methods.
- **Main limitation:** CRITIC comes out close to equal per column. Entropy
  is an artifact here: it puts 20% of its weight on existing data center
  count, and its weights depend on how columns are coded.

### Revealed preference

A logistic regression predicts existing data centers from the scored
columns.

- **Why it's defensible:** it shows what industry chose.
- **Main limitation:** population alone predicts almost as well (AUC
  0.855 against 0.906), and the fleet reflects past, latency-driven siting.

### Consensus

The consensus is a Borda count over each method's top 20.

- **Why it's defensible:** it shows agreement across methods.
- **Main limitation:** it mixes methods of very different quality. It's a
  cross-check.

## Weights by method

| Pillar | Balanced | Monetized at $190/t | CRITIC | Entropy | Revealed preference |
| --- | --- | --- | --- | --- | --- |
| energy_carbon | 0.153 | 0.228 | 0.185 | 0.249 | 0.171 |
| water | 0.119 | 0 | 0.120 | 0.038 | 0.123 |
| climate_resilience | 0.119 | 0.010 | 0.252 | 0.094 | 0.224 |
| grid_infrastructure | 0.153 | 0.066 | 0.150 | 0.441 | 0.086 |
| land | 0.068 | 0 | 0.044 | 0.008 | 0.156 |
| community | 0.085 | 0 | 0.136 | 0.144 | 0.129 |
| permitting | 0.153 | 0.155 | 0.096 | 0.024 | 0.053 |
| cost | 0.150 | 0.541 | 0.018 | 0.002 | 0.058 |

The monetized column holds the covariance shares at $190/t with tax, with
negative shares set to 0 and the rest renormalized. Permitting's 0.155 is
the sales tax component. These are weights on dollars, not engine weights.
Run through the engine, they give an Oklahoma-led top 10 that shares no
counties with the dollar top 10.

Chart: `docs/img/weights_by_method.png`.

## Method notes

- **Hazard cost understates hazard risk for a data center.** Building loss
  rates exclude downtime, lost revenue, and service-level penalties. Treat
  the hazard component as a floor.
- **The pillar floor is a judgment rule.** Its threshold and the
  permitting exemption were chosen, not derived. Franklin fails it on cost
  (6.5th percentile against 10).
- **Cooling by county is a modeling choice.** See Cooling above.
- **Sales tax maps to permitting by choice.** See The tax component above.

## Assumptions and parameter defaults

- **Facility:** 300 MW IT load, load factor 0.8.
- **Discounting:** 25 years at 7%.
- **PUE and WUE:** linear in cooling degree days (`etl/impact.py`).
- **Cooling:** evaporative where water stress is 2 or lower, otherwise
  dry.
- **Energy:** 2024 state average industrial price. BPA's $80 to $132/MWh
  for Clark and Grant as a scenario. No sourced New York new-load rate.
- **Carbon:** eGRID2023 subregion average. BPA-like supply at 212.458
  lb/MWh. Prices $0, $51, $190, and $300 per tonne.
- **Water:** $7 per 1,000 gallons times (1 + water stress), unsourced.
- **Hazard:** NRI v1.20 building loss rates over 17 hazards times a $10B
  asset value ($3B as a sensitivity). The asset value is an assumption:
  the whole campus, not the $4B taxable equipment base.
- **Time to power:**
  - Queue age beyond 2 years at $25M per month, one-time.
  - Imputed counties take the national median of 2.89 years.
  - Grant uses 12 months from its own evidence (range 8 to 18.5).
- **Moratorium:** 12 months at p=1 for an active state or county
  moratorium. Pending moratoria count 12 months at p=0.5, and recorded
  pushback 6 months at p=0.3.
- **Sales tax:**
  - $4B of taxable equipment per purchase, refreshed every 5 years (4 and
    6 as sensitivities). Both are assumptions from the revision request,
    not sourced.
  - Rates as in Sales and use tax above.
  - WA exemption for rural counties on initial equipment only.
  - New York taxed in the base case.
  - Other states follow the repo's state flags, with refreshes exempt.
- **Monte Carlo:** 1,000 draws, seed 42.
- **SMAA:** 5,000 draws, seed 0.
- **CRITIC and entropy:** winsorized 1st and 99th percentiles.
- **Revealed preference:** L2 logistic regression, C = 1, 5-fold.
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
python scratch/weighting/revisions.py
```

To repeat a tagged Monte Carlo run, pass overrides, for example
`python scratch/weighting/montecarlo.py --overrides '{"tax": false}' --tag notax`.
