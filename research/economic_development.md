# Economic development and data center siting

Date: 2026-10-03. Purpose: test whether a county's economic trajectory
changes how readily it accepts a data center, and add features to the
permitting model so the engine can use the answer.

**Result: the data doesn't support it.** On the permitting model's labels,
the economic features don't separate counties that saw opposition from those
that didn't, and they add no dependable predictive skill. See "Second check" below. The
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
negative only if it already has a permitted facility, so comparing all
labeled counties mixes "had opposition" with "has no data center yet." The
fair comparison uses only counties where either label is possible. There
are two ways to define them, and the results agree:

- **Permitted subset** (the permitting model's definition, column
  `has_permitted_facility`): 275 counties with an operating, approved, or
  expanding facility. 126 positive, 149 negative.
- **Existing-facility subset** (this brief's first definition):
  `dc_existing_count >= 1`. 184 counties, 76 positive, 108 negative.

| Feature | Permitted: positive / negative | p | Existing: positive / negative | p |
| --- | --- | --- | --- | --- |
| Manufacturing share 2001, median | 0.136 / 0.127 | 0.88 | 0.128 / 0.123 | 0.78 |
| Manufacturing loss share (clipped), median | 0.020 / 0.023 | 0.33 | 0.019 / 0.023 | 0.22 |
| Unemployment 2023 (%), median | 3.3 / 3.5 | 0.12 | 3.4 / 3.5 | 0.30 |
| Population change 2010-2024 (%), median | 10.8 / 6.0 | 0.01 | 10.8 / 7.5 | 0.06 |
| Share with retired coal | 21% / 14% | 0.15 | 22% / 16% | 0.26 |

p is a two-sided Mann-Whitney test.

Leave-one-state-out AUC on the permitted subset, using the permitting
model's seven non-count features as the base (`etl/permitting.py`):

| Features | Logistic | Boosted |
| --- | --- | --- |
| Base | 0.572 | 0.585 |
| Base plus the five economic features | 0.553 | 0.610 |
| The five economic features alone | 0.539 | 0.536 |

On the existing-facility subset, with density, income, and heating degree
days as the base, logistic AUC is 0.57 for the base, 0.49 with the economic
features added, and 0.48 for the economic features alone.

What this shows:

- The manufacturing features don't separate counties with and without
  opposition on either subset. Across all 447 labeled counties, the
  difference reverses: counties with opposition had a higher 2001
  manufacturing share (0.149 against 0.127, p = 0.11).
- Retired coal also goes the wrong way. Counties with opposition are more
  likely to have a retired coal plant, not less.
- The economic features make the logistic model worse. They lift the
  boosted model by 0.026, just past the 0.60 bar, but a paired bootstrap of
  that gain gives a 95% interval of -0.025 to 0.076. That isn't a
  dependable gain, and the logistic run disagrees.
- The one consistent difference is population growth. Faster-growing
  counties saw more opposition (p = 0.01 on the permitted subset). Added
  alone, it gives the largest boosted lift of the five features (AUC 0.636).
  That supports the "growth counties push back" half of the claim, not the
  deindustrialization half. It was picked after looking at five features
  and 20 rank tests, so treat it as a lead for a future label set, not a
  result.

Limits: the subsets are small, and FracTracker records pushback as Yes or
Unknown, never No. A negative county has no recorded opposition. It isn't
confirmed acceptance.

## Long-run measures

The 2001-2023 columns can't see Detroit or Gary. Their 2001 baseline comes
after the Rust Belt collapse of the 1970s and 1980s, 2023 unemployment barely
varies (median 3.4 percent), and 2010-2024 population change misses the long
decline. A first factor of the five ranked Wayne, MI at the 56th percentile. Five long-run
columns replace them as candidates. All are unscored stretch columns.

| Column | Source and years |
| --- | --- |
| `pop_change_pct_since_peak` | Census county counts 1950-1990 (Forstall table; census.gov no longer hosts it, so the NBER mirror), Census 2000 estimates base, 2010 census, 2020 estimates base, July 2024 estimate |
| `mfg_emp_share_1969` | BEA CAEMP25S, 1969, SIC manufacturing / total employment |
| `mfg_emp_share_change_1969_2022` | BEA CAEMP25S 1969 and CAEMP25N 2022 (NAICS) |
| `energy_community_coal_closure` | DOE/NETL IRA energy communities 2024: a tract in the county had a coal closure |
| `energy_community_ffe` | DOE/NETL 2024: the county's MSA or non-MSA meets the fossil fuel employment and unemployment tests |

Face validity, in `tests/test_deindustrialization.py`, on the committed table:

| County | Below peak | Decline rank | Mfg share 1969 | Percentile | Change to 2022 | Coal closure | FFE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Wayne, MI (Detroit) | -33.6% | top 16% | 0.335 | 84th | -0.238 | yes | no |
| Mahoning, OH (Youngstown) | -25.6% | top 20% | 0.332 | 83rd | -0.255 | yes | yes |
| Cambria, PA (Johnstown) | -37.9% | top 12% | 0.305 | 79th | -0.237 | yes | yes |
| Genesee, MI (Flint) | -10.7% | top 34% | 0.448 | 94th | -0.372 | no | no |
| Lake, IN (Gary, Hammond) | -7.9% | top 38% | 0.426 | 93rd | -0.338 | yes | yes |
| Trumbull, OH (Lordstown) | -17.2% | top 26% | 0.494 | 95th | -0.404 | yes | yes |
| Loudoun, VA | 0.0% (at peak) | n/a | 0.026 | 12th | +0.006 | no | no |

The 1969 manufacturing share works: every Rust Belt test county is in the
top quarter, and Loudoun is in the bottom quarter. Population decline since
peak works for Wayne, Mahoning, and Cambria, but not for Genesee (34th) or
Lake, IN (38th). A county measure dilutes a city's decline: Gary and Flint
are only part of their counties. The Genesee test is a strict expected
failure, so the gap shows in every test run instead of being tuned away.

The coal closure flag counts only tracts with a closure of their own. NETL
also designates tracts that adjoin a closure tract, which would add 364
counties, among them Loudoun, whose tracts adjoin a closure across the
Potomac.

## Case pairs

An Opus research agent gathered these on 2026-10-03. Spot checks against
the sources confirmed the Hammond agreement's expiry, the Widows Creek
announcement, and the Valparaiso cancellation. Markers: **[C]** confirmed by
a source, **[P]** partly confirmed or sources disagree, **[U]** unconfirmed.
Don't put a [P] or [U] item on a slide without its caveat.

### Hammond (Lake County, IN) against Porter County, IN

**Digital Crossroad, Hammond: a coal plant site, approved without a fight.**

- The campus sits on the former State Line Generating Plant on Lake
  Michigan at the Illinois line. **[C]**
  ([IBJ](https://www.ibj.com/articles/40m-data-center-opens-in-northwest-indiana))
- Dominion shut the plant by March 31, 2012. **[C]**
  ([WBEZ](https://www.wbez.org/news/2012/03/26/state-line-coal-powered-plant-may-shut-down-this-week))
- In August 2018, developers announced work on the 77-acre site. Indiana
  approved $9 million in conditional tax credits, and the mayor and governor
  backed it. The coverage mentions no opposition. **[C]**
  ([Inside Indiana Business](https://www.insideindianabusiness.com/articles/work-to-begin-on-power-plant-to-data-center-project-hammond-state-line-generating-facility-lake-county-digital-crossroads-of-america))
- The first phase, a $40 million, 105,000 sq ft building, opened in November
  2020. **[C]** ([IBJ](https://www.ibj.com/articles/40m-data-center-opens-in-northwest-indiana))
  Its capacity is reported as both 6 MW and 20 MW. **[P]**
  ([NWI Business](https://nwindianabusiness.com/npzl),
  [Baxtel](https://baxtel.com/data-centers/digital-crossroad))
- On June 9, 2025, the city council voted 8-0 for a 180 MW, 450,000 sq ft
  CoreWeave building on the same site. **[C]**
  ([City of Hammond](https://www.gohammond.com/hammond-approves-development-agreement-for-new-data-center/))
- That agreement expired on June 30, 2026, after two extensions, because
  required milestones weren't met. The city gave no reason. **[C]**
  ([City of Hammond](https://www.gohammond.com/?p=8210)) Trade press pointed
  to the pending utility power agreement. **[U]**

**Porter County: four proposals, all withdrawn or cancelled.**

- Chesterton: Provident Realty Advisors, $1.3 billion, eight buildings.
  Withdrawn in June 2024 after the town council said it could never support
  it. **[C]** Site type unknown. **[U]**
  ([Inside Indiana Business](https://insideindianabusiness.com/?p=170386))
- Valparaiso: Agincourt Investments, 180 acres of city-owned land. Approved
  as an option on January 9, 2025. The mayor ended it on March 11, 2025, the
  day after a packed council meeting: "Our citizens have spoken
  decisively." **[C]**
  ([GovTech](https://www.govtech.com/products/valparaiso-ind-mayor-says-data-center-dead-after-outcry))
- Union Township: QTS, about $2 billion on about 800 acres of farmland.
  More than 1,000 residents attended a May 2025 town hall. QTS withdrew in
  September 2025. **[C]**
  ([DCD](https://www.datacenterdynamics.com/en/news/qts-cans-data-center-scheme-in-porter-county-indiana-after-protests/))
- Burns Harbor: Provident, 102 acres owned by Worthington Steel. Opposed at
  a planning meeting in early 2025, then revised or scrapped; listings
  disagree on its status. **[P]**
  ([Baxtel](https://baxtel.com/data-center/provident-burns-harbor-in))
  This one cuts against the pairing: industrial land in a steel town still
  drew opposition.

**Gary itself.** No proposal had formally come before the Gary Common
Council as of March 16, 2026. **[C]**
([Capital B Gary](https://gary.capitalbnews.org/gary-indiana-data-centers/))
Lake County isn't uniformly welcoming either. Residents sued over an
approved Amazon data center in Hobart. **[C]** The ruling is unconfirmed.
**[U]** ([FOX 32](https://www.fox32chicago.com/news/lawsuit-seeks-block-amazon-data-center-permit-hobart-ind))

What the pair shows: the coal plant site won approval with little friction,
and every Porter County proposal failed after local opposition. But the
Hammond expansion stalled anyway, for reasons other than opposition, and the
Burns Harbor case shows industrial land isn't a shield.

### More brownfield reuse

- **Google, Widows Creek, Jackson County, AL.** Announced June 24, 2015, on
  the grounds of TVA's Widows Creek coal plant, which was scheduled for
  shutdown, to reuse its transmission lines. **[C]**
  ([Google](https://blog.google/inside-google/infrastructure/a-power-plant-for-internet-our-newest/))
  The last unit retired in 2015. **[C]**
  ([Argus](https://www.argusmedia.com/pt/news-and-insights/latest-market-news/1035460-tva-shuts-last-coal-unit-at-alabama-plant))
  Google broke ground in April 2018 for a $600 million campus. **[C]**
  ([Made in Alabama](https://www.madeinalabama.com/2018/04/google-kicks-off-construction-on-alabama-data-center/))
  Google announced a $1.5 billion expansion in June 2026. **[C]**
  ([Alabama Political Reporter](https://www.alreporter.com/2026/06/16/google-plans-1-5-billion-jackson-county-data-center-expansion/))
- **TeraWulf Lake Mariner, Niagara County, NY.** The Somerset plant, New
  York's last coal plant, retired on March 31, 2020. **[C]**
  ([Lockport Union-Sun & Journal](https://www.lockportjournal.com/news/local_news/operator-of-now-retired-somerset-generation-station-sees-rebirth-in-power-consumption/article_c3d98eb5-ef9a-5619-9e0d-18e020adb8f6.html))
  Lake Mariner reuses the site. **[C]** Only a single source with ties to
  TeraWulf states this.
  ([Data Center Richness](https://datacenterrichness.substack.com/p/inside-an-accelerated-ai-data-center))
  In August 2025, it signed AI hosting leases for over 200 MW, backstopped by
  Google. **[C]**
  ([SEC filing](https://www.sec.gov/Archives/edgar/data/1083301/000110465925078084/tm2523008d2_ex99-1.htm))
  It began as a bitcoin mine, and residents complained about fan noise.
  **[P]**

### Counterexample: xAI Colossus, Memphis, Shelby County, TN

xAI took over the former Electrolux factory in South Memphis in 2024. **[C]**
([Tech Policy Press](https://techpolicy.press/inside-selcs-clean-air-case-against-xai-in-memphis))
It ran gas turbines without permits. The county permitted 15 in July 2025
after more than 1,000 public comments. **[C]**
([Action News 5](https://www.actionnews5.com/2025/07/02/health-dept-grants-permit-xai-turbines/))
The NAACP, with the Southern Environmental Law Center, appealed and in April
2026 sued over turbines at a second site. **[C]**
([SELC](https://www.selc.org/news/xai-built-an-illegal-power-plant-to-power-its-data-center/))
The project runs, and the fight continues. The fight is over on-site gas
generation in an air-quality hotspot, not the land use. A brownfield site
didn't prevent it.

## How to use it in the presentation

Use it on the "what we tested" slide, not as a headline. The honest version:

- The idea: deindustrializing counties accept data centers more readily.
  Case studies support it: Mount Pleasant, Lordstown, Homer City, and the
  Hammond and Porter County pair. Burns Harbor and Memphis cut against it.
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
