# Sustainability impact: method and results

What a 300 MW facility emits and how much cooling water it uses, by county,
against Loudoun County, VA, where the industry builds now.

Reproduce: `python -m etl.impact 25003 36033 36019 36029 36067 53025 41067 39155 04013`.
The code is `etl/impact.py`. It reads the committed county table and takes
any list of counties, a facility size, and a baseline county.

## Formulas

| Quantity | Formula | Units |
| --- | --- | --- |
| IT energy | IT load x 8,760 x load factor | MWh per year |
| PUE | cold value + (hot value - cold value) x CDD / 4,000 | ratio |
| Facility energy | IT energy x PUE | MWh per year |
| CO2 | facility energy x `grid_co2_lb_mwh` / 2,204.62 | metric tons per year |
| WUE | cold value + (hot value - cold value) x CDD / 4,000 | litres per kWh of IT energy |
| On-site water | IT energy x 1,000 x WUE / 3.78541 | gallons per year |

CDD is the county's annual cooling degree days from the table: `cdd_hist`
for today and `cdd_2050_rcp85` for 2050.

## Assumptions

| Assumption | Value | Basis |
| --- | --- | --- |
| IT load | 300 MW | the conditions file |
| Load factor | 0.8 | assumption. LBNL 2024 models AI training servers at 80 percent operational time. Its fleet-wide capacity utilization is 50 percent. Every result scales in proportion. |
| PUE, evaporative | 1.12 cold to 1.25 hot | Lei and Masanet: about 1.12 in the coldest climate zone and 1.25 in the hottest for airside economizers with adiabatic cooling |
| PUE, dry | 1.12 cold to 1.38 hot | assumption: the same cold value and twice the climate penalty. LBNL 2024 says air-cooled systems use no water and more energy. No source gives a curve. |
| WUE, evaporative | 0.1 cold to 1.8 hot | Lei and Masanet, same design: about 0.1 to 1.8 L/kWh |
| WUE, dry | 0.05 | Lei and Masanet: 0.05 to 0.1 for humidification only. LBNL 2024 shows about 0. |
| Hot anchor | 4,000 CDD | assumption. Miami-Dade's value in the county table, standing for climate zone 1A. The cold anchor is 0. |
| Grid rate | eGRID2023 subregion annual average | the table's `grid_co2_lb_mwh`. Not a marginal rate. |

Sources:

- LBNL 2024: Shehabi et al., 2024 United States Data Center Energy Usage
  Report, https://escholarship.org/uc/item/32d6m0d1
- Lei and Masanet: climate- and technology-specific PUE and WUE estimates
  for US data centers, preprint at
  https://www.researchsquare.com/article/rs-769999/v1. Values were read from
  its charts and are accurate to about 0.05.

Two assumptions are ours and no source backs them: the mapping from cooling
degree days to the paper's climate zones, and the dry-cooling PUE curve.

"Evaporative" here means an airside economizer with adiabatic assist, the
common hyperscale design. A cooling-tower design uses about 2.2 L/kWh in
every climate (LBNL 2024), which is 1.2 billion gallons a year at this size.

## Results today

300 MW, load factor 0.8, so IT energy is 2,102,400 MWh a year at every
site. Differences are against Loudoun.

### Dry cooling

On-site water is 27.8 million gallons a year at every site. Energy cost is
facility energy times the state's `industrial_price_cents_kwh`
(`etl.risk.energy_cost`).

| County | CDD | Grid lb/MWh | PUE | CO2, tons/yr | vs Loudoun | Energy cost, $M/yr | vs Loudoun |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grant, WA | 655 | 632 | 1.163 | 700,390 | +24,936 | 162 | -64 |
| Berkshire, MA | 259 | 539 | 1.137 | 584,653 | -90,801 | 435 | +209 |
| Franklin, NY | 240 | 242 | 1.136 | 262,168 | -413,287 | 219 | -7 |
| Clinton, NY | 354 | 242 | 1.143 | 263,888 | -411,567 | 220 | -5 |
| Erie, NY | 457 | 242 | 1.150 | 265,420 | -410,034 | 222 | -4 |
| Onondaga, NY | 495 | 242 | 1.152 | 265,995 | -409,459 | 222 | -3 |
| Washington, OR | 214 | 632 | 1.134 | 683,128 | +7,674 | 192 | -34 |
| Trumbull, OH | 640 | 911 | 1.162 | 1,009,646 | +334,192 | 173 | -52 |
| Maricopa, AZ | 3,377 | 704 | 1.340 | 898,913 | +223,458 | 222 | -3 |
| Loudoun, VA | 1,132 | 593 | 1.194 | 675,455 | 0 | 226 | 0 |

Grant's CO2 in this table uses the regional average. See the range below.

### Evaporative cooling

| County | PUE | CO2, tons/yr | vs Loudoun | Water, million gal/yr | vs Loudoun |
| --- | --- | --- | --- | --- | --- |
| Berkshire, MA | 1.128 | 580,318 | -74,315 | 116.8 | -206.0 |
| Franklin, NY | 1.128 | 260,368 | -394,266 | 112.2 | -210.6 |
| Clinton, NY | 1.132 | 261,228 | -393,406 | 139.2 | -183.5 |
| Erie, NY | 1.135 | 261,994 | -392,640 | 163.3 | -159.4 |
| Onondaga, NY | 1.136 | 262,282 | -392,352 | 172.4 | -150.4 |
| Grant, WA | 1.141 | 687,564 | +32,930 | 210.2 | -112.6 |
| Washington, OR | 1.127 | 678,933 | +24,299 | 106.1 | -216.6 |
| Trumbull, OH | 1.141 | 991,555 | +336,922 | 206.7 | -116.0 |
| Maricopa, AZ | 1.230 | 825,258 | +170,624 | 852.7 | +529.9 |
| Loudoun, VA | 1.157 | 654,634 | 0 | 322.8 | 0 |

## Grant County, WA: CO2 as a range

Grant County is the featured site. Its emissions depend on which power
serves the new load, so the honest figure is a range. Facility energy is
2,444,212 MWh a year with dry cooling.

| Supply assumption | Rate, lb/MWh | CO2, tons/yr | vs Loudoun |
| --- | --- | --- | --- |
| Grant PUD's own generation (eGRID balancing authority GCPD) | 0 | 0 | -675,455 |
| Bonneville Power Administration (eGRID balancing authority BPAT) | 212 | 235,547 | -439,908 |
| Northwest subregion average (the county table's value) | 632 | 700,390 | +24,936 |

For assigning the county to its balancing authority: Grant PUD is the
county's utility, its plants are all inside the county, and all of them
are hydro. Against: a balancing authority rate describes what the utility
generates, not what a new customer receives. The PUD's share of its dams
averages about 633 MW, below its 2025 load of 757 average MW, and the
campus would add 279. The PUD says large users fund the generation they
need (its data center FAQ, 2026-08-28). So the first row is not available
to a new load. Use the middle row as the working estimate and show the
range. The county table and the engine keep the subregion value.

Energy cost has the same dependence on supply. The same 2,444,212 MWh:

| Price assumption | $/MWh | Energy cost, $M/yr | vs Loudoun |
| --- | --- | --- | --- |
| Washington average industrial price (the county table's value) | 66 | 162 | -64 |
| BPA rate for a new large load, low end | 80 | 196 | -30 |
| BPA rate for a new large load, high end | 132 | 323 | +97 |

Grant costs more than Loudoun above about $92 per MWh. The BPA range is
from `research/implementation.md`, which cites BPA's rule for new large
single loads and its BP-26 rate schedules.

## Results in 2050

Same grid rate as today. Only the climate changes.

| County | CDD 2050 | Dry: CO2, tons/yr | Evaporative: water, million gal/yr |
| --- | --- | --- | --- |
| Berkshire, MA | 679 | 598,684 | 215.8 |
| Franklin, NY | 620 | 267,865 | 201.8 |
| Clinton, NY | 804 | 270,626 | 245.2 |
| Erie, NY | 986 | 273,365 | 288.3 |
| Onondaga, NY | 1,055 | 274,392 | 304.5 |
| Grant, WA | 1,177 | 720,820 | 333.3 |
| Washington, OR | 575 | 697,273 | 191.4 |
| Trumbull, OH | 1,299 | 1,046,825 | 362.0 |
| Maricopa, AZ | 4,520 | 948,746 | 1,122.4 |
| Loudoun, VA | 1,888 | 703,244 | 501.1 |

Warming raises evaporative water use by about 80 percent in the upstate New
York counties and 55 percent in Loudoun. It raises dry-cooling CO2 by 2 to 6
percent.

## What the numbers say

- The grid decides CO2. PUE varies by a few percent across these sites.
  The grid rate varies by a factor of four.
- An upstate New York site emits about 410,000 tons a year less than
  Loudoun, a 61 percent cut. Over 30 years at today's rates, that is about
  12 million tons.
- Climate decides water. An evaporative site in upstate New York uses about
  a third to half of Loudoun's water today. Maricopa uses 2.6 times
  Loudoun's.
- Grant County costs $64M a year less than Loudoun to power. Its CO2 runs
  from zero to slightly above Loudoun's, depending on supply.
- Dry cooling removes almost all on-site water for a small energy cost in
  cool climates: about 1 percent more CO2 in upstate New York, 9 percent in
  Maricopa.

## Limits

- The 30-year figure holds today's grid rates. Grids are expected to get
  cleaner, so absolute emissions are an upper bound. No sourced trajectory
  is used.
- The subregion average hides local supply. Grant County, WA and
  Washington County, OR show slightly more CO2 than Loudoun because the
  Northwest subregion (NWPP, 632 lb/MWh) spans coal and gas plants in the
  interior West. Their local utilities are mostly hydro. The range above
  handles Grant. Washington County's row is overstated in the same way.
- Emissions are location-based annual averages. A new 300 MW load is served
  at the margin, which is usually dirtier than the average.
- Water used to generate the grid power is omitted. The county table has no
  `grid_water_gal_mwh` column, and no sourced factor is applied.
- Maricopa in 2050 is beyond the 4,000 CDD anchor, so its values are
  extrapolated.
- New York has an active statewide data center moratorium in the
  FracTracker data (2026-06-04 to 2027-06-04). The four New York counties
  rank because the balanced preset does not exclude state moratoria.
