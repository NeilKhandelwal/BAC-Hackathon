# Economic development and data center siting

Date: 2026-10-03. Purpose: test whether a county's economic trajectory
changes how readily it accepts a data center, and add features to the
permitting model so the engine can use the answer.

**Result: the data doesn't support it.** On the permitting model's labels,
the economic features don't separate counties that saw opposition from those
that didn't, and they add no predictive skill. See "Second check" below. The
claim rests on case studies and published research, not on our data.

## The claim

The starting idea: deindustrializing counties are more willing to host a
data center than strong, growing ones. The evidence supports a narrower
version:

> Counties with an industrial past, meaning manufacturing job loss plus
> existing heavy grid connections, get data centers faster and with less
> opposition than either affluent growing suburbs or greenfield farmland.
> They also capture the least economic benefit.

The split that matters is brownfield versus greenfield, not poor versus rich.

## What the evidence says

**For the claim:**

- Rich growth counties push back. Loudoun County passed a 12-month
  moratorium. Prince William County's Digital Gateway was stopped in court,
  and its board rejected Dulles Cloud South in July 2026.
- Hyperscalers reuse industrial land: Microsoft on the Foxconn site in Mount
  Pleasant, WI; SoftBank in Lordstown, OH; Homer City and Cheswick on former
  Pennsylvania coal plant sites.
- The mechanism is power, not just willingness. A retired coal plant's
  interconnection lets a project skip the multi-year queue for a new
  high-voltage connection. Enverus estimates 70 GW of retired coal capacity
  could be reused.

**Against the claim:**

- Historically, data centers went to counties that were already growing.
  Brookings, using about 1,500 facilities, finds faster pre-arrival growth in
  data center counties. Power, land, and fiber drive siting. Incentives are
  about 2% of construction cost in hyperscale counties.
- Rural counties fight hard too. Kosciusko County, IN rejected a 550-acre
  Prologis rezoning. "Keep Haralson Rural" signs went up in Georgia.
  Opposition blocks or delays two of every three projects it targets, and 55%
  of opposing officials are Republican.
- Distressed places gain least. A 2026 study finds metro counties gained
  about 4.1% employment and 5.5% wages. Non-metro counties saw almost nothing.

## Features added to the county table

Branch `etl/econ-features`. Columns are stretch tier in `docs/schema.md`.

| Column | Source | Measures |
| --- | --- | --- |
| `mfg_emp_share_2001` | Census CBP 2001 | industrial legacy |
| `mfg_loss_share_emp_2001` | Census CBP 2001 and 2022 | manufacturing jobs lost, as a share of all 2001 jobs |
| `unemployment_rate_pct_2023` | BLS LAUS via USDA ERS | current distress |
| `pop_change_pct_2010_2024` | Census population estimates | decline versus growth |
| `coal_retired_mw` | EIA-860 2025 | reusable grid connection |

Brownfields beyond coal plants aren't included. EPA's ACRES list is too broad
to use as a power-site proxy without hand filtering.

Known data limits are in each adapter's `NOTES` and go to the manifest. The
important ones:

- CBP 2001 withholds small cells, and they take the size-class midpoint.
- `mfg_loss_share_emp_2001` has no lower bound. Storey County, NV reads
  -19.4 because its jobs grew from 438 to 13,367. That county holds the
  Tahoe-Reno Industrial Center and Switch's data center campus. Clip the
  value or use its rank before modeling.
- Two Connecticut regions, Broomfield, CO, and King County, TX have null
  manufacturing values.

## First look at the labels

This is a descriptive check, not the model test. It uses
`opposition_seed_labels.csv`: 180 counties, 122 where opposition cancelled,
withdrew, or delayed a project, and 58 where projects were only approved.

| Feature | Blocked, median | Approved, median | Mann-Whitney p |
| --- | --- | --- | --- |
| Manufacturing share 2001 | 0.131 | 0.169 | 0.07 |
| Manufacturing loss share | 0.018 | 0.031 | 0.06 |
| Unemployment 2023 (%) | 3.4 | 3.5 | 0.28 |
| Population change 2010-2024 (%) | 7.2 | 6.6 | 0.68 |
| Any retired coal | 17% | 21% | 0.58 |

Every feature pointed the way the claim predicts, but only the two
manufacturing features came near significance. This check compared counties
with different facility histories, so the second check supersedes it.

Read this with the label caveats in `research/opposition_labels.md`. The
approved class is noisy, and the labels show which fights succeed, not where
fights start.

## Second check: the permitting model labels

The permitting model (`research/permitting_model.md`) labels 447 counties:
298 positive (opposition recorded) and 149 negative. A county can be
negative only if it already has a facility, so comparing all labeled
counties mixes "had opposition" with "has no data center yet." The fair
comparison is among the 184 labeled counties with at least one existing
facility, where either label is possible: 76 positive, 108 negative.

| Feature | Positive, median | Negative, median | Mann-Whitney p |
| --- | --- | --- | --- |
| Manufacturing share 2001 | 0.128 | 0.123 | 0.78 |
| Manufacturing loss share (clipped) | 0.019 | 0.023 | 0.22 |
| Unemployment 2023 (%) | 3.4 | 3.5 | 0.30 |
| Population change 2010-2024 (%) | 10.8 | 7.5 | 0.06 |
| Any retired coal | 0% | 0% | 0.26 |

Leave-one-state-out AUC in the same 184 counties:

| Features | AUC |
| --- | --- |
| The five economic features alone | 0.48 |
| Density, income, heating degree days | 0.57 |
| Those three plus the five economic features | 0.50 |

The manufacturing signal from the first look is gone. Across all 447
labeled counties it reverses: counties with opposition had a higher 2001
manufacturing share (0.149 against 0.127, p = 0.11). The economic features
have no skill alone and make the base features worse. The only hint left is
that faster-growing counties saw more opposition. That fits the "rich growth
counties push back" half of the claim, but p = 0.06 among the 15 rank tests in this brief is
what chance produces.

Limits: 184 counties is small, and FracTracker records pushback as Yes or
Unknown, never No. A negative county has no recorded opposition. It isn't
confirmed acceptance.

## How to use it in the presentation

Use it on the "what we tested" slide, not as a headline. The honest version:

- The idea: deindustrializing counties accept data centers more readily.
  Case studies support it: Mount Pleasant, Lordstown, Homer City.
- We built five county features and tested them against opposition
  outcomes. They don't predict opposition once you compare like with like.
- The other half, that rural counties gain the least, comes from the 2026
  study cited above, not from our data.

That a plausible story didn't hold up on the data is itself a result worth
showing.

## Sources

- [Brookings: New evidence on data center employment effects](https://www.brookings.edu/articles/new-evidence-on-data-center-employment-effects/)
- [Fortune: metro jobs up 4%, rural barely affected](https://fortune.com/2026/07/14/data-centers-urban-rural-jobs-study/)
- [CSG South: data center tax breaks](https://csgsouth.org/policies/take-that-for-data-incentivizing-innovation-or-inefficiency/)
- [Fierce Network: Loudoun moratorium](https://www.fierce-network.com/cloud/data-center-capital-world-says-enough)
- [Virginia Mercury: Dulles Cloud South rejected](https://virginiamercury.com/2026/07/09/after-digital-gateway-project-fails-prince-william-supervisors-reject-dulles-cloud-south-data-center-proposal/)
- [Route Fifty: $64B stalled by community pushback](https://www.route-fifty.com/infrastructure/2025/05/report-highlights-community-pushback-stalling-64-billion-data-center-development-nationwide/405480)
- [Inside Indiana Business: Kosciusko County](https://www.insideindianabusiness.com/articles/kosciusko-county-board-rebukes-data-center-project-measure-not-dead-yet)
- [FOX 5 Atlanta: Keep Haralson Rural](https://www.fox5atlanta.com/news/keep-haralson-rural-residents-fight-potential-data-center-deal)
- [DCD: Pennsylvania's data center rise](https://www.datacenterdynamics.com/en/analysis/shaking-off-the-rust-pennsylvanias-data-center-rise/)
- [Fortune: old coal plants and the AI boom](https://fortune.com/2025/08/31/ai-data-center-boom-old-coal-plants/)
- [PNNL: coal to data center](https://www.pnnl.gov/sites/default/files/media/file/PNNL-SA-201505-CoaltoDataCenter.pdf)
