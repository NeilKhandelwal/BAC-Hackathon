# Economic development and data center siting

Date: 2026-10-03. Purpose: test whether a county's economic trajectory
changes how readily it accepts a data center, and add features to the
permitting model so the engine can use the answer.

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

Every feature points the way the claim predicts. Opposition succeeds less
often in counties with more manufacturing history and more job loss. Only
the two manufacturing features come near significance. An in-sample logistic
regression that controls for density and income keeps every economic
coefficient negative, the largest being manufacturing share at -0.29 per
standard deviation. That fit isn't cross-validated, so don't quote it as a
result.

Read this with the label caveats in `research/opposition_labels.md`. The
approved class is noisy, and the labels show which fights succeed, not where
fights start.

## How to test it properly

1. Add the five columns as candidate features in `docs/permitting.md`.
   Clip `mfg_loss_share_emp_2001` to [-1, 1] and use `coal_retired_mw > 0`
   or `log1p`.
2. Refit with leave-one-state-out folds. Keep the features only if pooled
   AUC rises by 0.02 or more, the same rule as the news features.
3. Report the sign of each coefficient after controlling for density and
   cropland. The claim holds only if manufacturing loss lowers predicted
   risk with those controls in.
4. If AUC doesn't move, say so in the deck. "Economic distress doesn't
   predict opposition once you control for rurality" is a finding too.

## How to use it in the presentation

The angle: the places most willing to host a data center gain the least
from it. The engine can show both sides at once: lower permitting risk and
faster power on one side, thin local job spillover on the other. That makes
community benefit a real decision input, not a footnote.

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
