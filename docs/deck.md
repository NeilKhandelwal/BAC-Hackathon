# Deck content

Slide-by-slide content for the final deck. Each slide has a headline that
states the finding, three or fewer points, its figure or table, and one line
of speaker note that names the committed file the numbers come from.

Numbers are from `main` with the eight-pillar engine (PR #28) and the
research write-ups from PRs #29 and #30. Figures and
`docs/figures/facts.json` come from `python docs/figures/make_figures.py`,
which reads only committed files and makes no network calls.

**Featured county.** Grant County, WA (53025). Slide 12 covers the global
country run. To swap the featured county, run
`python docs/figures/make_figures.py --featured <fips>` and update slides 1,
6, 7, 8, and 9 from the new `facts.json` and research files.

**Wording.** Say "sited next to hydro, powered by new clean supply the
project funds". Never say "runs on hydro". The three research write-ups
agree on this.

---

## 1. The answer

**Headline:** Grant County, Washington is the strongest site for a 300 MW
sustainable AI campus: first of 1,565 qualifying counties, and in the top 10
under 99.9% of weight resamples.

- Grant ranks first with a composite of 63.7, ahead of Wayne TN (63.2) and
  Whitman WA (63.1). Its lead is 0.5 points, so the robustness number
  carries the claim, not the rank.
- **Why it wins:** cheap power, favorable state policy, room to build, and an
  existing data center cluster with 99% fiber coverage.
- **Condition for it to hold:** the campus is sited next to hydro, powered by
  new clean supply the project funds. None of the utility's existing hydro is
  available to a new 300 MW load (slide 7).

**Figure:** `docs/figures/top10_table.png`, with `docs/figures/map_composite.png`
as the backdrop or the next build.

**Speaker note:** Ranks, composites, and robustness are in
`results/balanced.csv` and `docs/figures/facts.json` (`top10`,
`gap_first_to_second`). The supply condition is in `research/risk.md`.

## 2. Decision framework

**Headline:** Hard gates remove unbuildable counties, then eight weighted
pillars rank the rest, and a floor stops any county from winning on a single
strength.

- **Gates first:** flood, wildfire, and hurricane caps, fiber,
  interconnection queue age, county moratoria, workforce, and nearby
  generation of five times the facility's load. A missing value never
  excludes a county.
- **Pillars:** each column becomes a national percentile, and a pillar is the
  mean of its columns. Weights: energy and carbon 15%, grid 15%, permitting
  15%, cost of power 15%, water 12%, climate 12%, community 8%, land 7%. A
  county below the 10th percentile on any pillar ranks after every county
  that isn't.
- **The weights are stated judgments, not fitted values.** Grant is also first
  under equal weights, sharing 7 of the top 10. Across uniformly random
  weightings it lands in the top 10 50.5% of the time, more than any other
  county.

**Figure:** `docs/figures/framework.png`

**Speaker note:** Weights and the floor are in
`engine/conditions/balanced.yaml`. Equal-weight and random-weighting results
are in `docs/figures/facts.json` (`weights`), computed by
`docs/figures/make_figures.py`.

## 3. Data

**Headline:** Every one of 3,109 counties is scored from 20 documented
sources, and the proxies are labeled as proxies.

- 3,109 counties in the contiguous US by 83 columns. 35 of the 45 mapped
  columns are populated, so coverage is 0.73 to 0.78 across the top 10.
- Sources by pillar:
  - **Energy and carbon:** eGRID2023 subregions, the LBNL interconnection queue (clean generation excluding storage, and capacity delivered 2021-2025), the NREL WIND Toolkit, and eGRID plants within 100 km.
  - **Water:** the Drought Monitor, FEMA NRI, WRI Aqueduct 4.0, and CMRA.
  - **Climate:** FEMA NRI loss rates and CMRA projections.
  - **Grid:** the LBNL queue, FCC fiber, FracTracker, and EIA-860.
  - **Cost:** EIA-861 state industrial prices.
  - **Land:** Census TIGER.
  - **Community:** ACS, BLS LAUS, BEA 1969 employment, and Census history since 1950.
  - **Permitting:** the EPA Green Book and hand-coded state tables.
- Proxies:
  - **Fiber:** last-mile residential fiber stands in for backbone.
  - **Nearby capacity:** plant capacity within 100 km stands in for deliverable power.
  - **Price:** a state average price stands in for what a new load pays.
  - **Heat sink:** heating degree days times density stands in for heat reuse.

**Figure:** none. Use a two-column table of pillar to sources from the points
above.

**Speaker note:** Sources and versions are in
`data/processed/county_features.manifest.json` (`sources`). The column
contract is in `docs/schema.md`, and the mapping in `engine/pillars.yaml`.

## 4. Validation: how the pick changed

**Headline:** The engine screens and the feasibility study decides: three
corrections moved the answer, and the last one changed what the answer
means.

- **Seven pillars:** with price as one of seven grid columns (2.6% of the
  composite), Berkshire County, MA ranked first at 18.19 cents/kWh, and Grant
  seventh. Correcting a closed Massachusetts tax exemption, recomputed with
  today's queue measures, moves Berkshire to fifth and Grant to ninth.
- **Cost as its own pillar:** at 15%, cost moved Grant to first and Berkshire
  to 1,047th. Berkshire would pay $435M a year for power against Loudoun's
  $226M and Grant's $162M.
- **Then feasibility:** research found that $162M uses a state average price
  a new load won't get. At BPA's new-load rate the same energy costs $196M to
  $323M. Earlier, FEMA's dollar-loss scores had excluded Grant, Polk IA, and
  Dallas TX. Loss rates fixed that, and Grant is first even without the
  existing-facility column (fourth).

**Figure:** `docs/figures/pick_story.png`, with `docs/figures/corrections.png`
as a second build.

**Speaker note:**
- Stage ranks: `docs/figures/facts.json` (`pick_story`). The first stage is `results/balanced.csv` at tag `data-freeze-2026-10-03`.
- Energy costs and the new-load range: `research/impact.md` and `research/implementation.md`.
- FEMA counterfactual: `facts.json` (`corrections`).

## 5. What we tested and dropped

**Headline:** We tested two appealing ideas against data and dropped both
as predictions, then kept the second one as an explicit value choice.

- **Permitting model:** it reached AUC 0.72 to 0.79 only because facility
  counts leak the label. Without them, leave-one-state-out AUC is 0.48 to
  0.585, under our 0.60 bar. No model ships.
- **Deindustrialization hypothesis:** the idea was that deindustrialized
  counties accept data centers more readily. The economic features made the
  model worse (logistic AUC 0.57 to 0.49), and alone they score 0.48.
- **What we kept:** we kept the idea as a stated value choice. Community
  scores unemployment, decline from the county's own population peak, and
  1969 manufacturing share. Grid scores retired coal capacity as a reusable
  interconnection.

**Figure:** none. A three-row table of model, AUC with counts, and AUC
without counts works.

**Speaker note:** AUCs are in `data/processed/permitting_validation.json` and
`research/permitting_model.md`. The economic test is in
`research/economic_development.md`, the value choice in `docs/conditions.md`.

## 6. Sustainability impact

**Headline:** Sited next to hydro and powered by new clean supply the project
funds, a Grant campus emits about 236,000 metric tons of CO2 a year, a third
of Loudoun's, and dry cooling cuts its water to 28 million gallons.

- **CO2 is a range:** about 236,000 tons a year if new supply looks like
  BPA's mix, up to 700,390 at the Northwest regional average, against
  Loudoun's 675,455. The utility's own hydro rate of 0 lb/MWh describes its
  existing customers, not a new load.
- **Water:** with evaporative cooling Grant would use 210 million gallons a
  year, against Loudoun's 323. Its water stress forces dry cooling: 27.8
  million gallons a year for about 2% more energy.
- **Energy cost is a range too:** $162M a year at Washington's state average
  of 6.61 cents, which is a floor. At BPA's new-load rate it's $196M to
  $323M, against Loudoun's $226M. Assumptions: 300 MW IT load, load factor
  0.8, PUE and WUE from Lei and Masanet, with our own climate mapping and
  dry-cooling curve.

**Figure:** `docs/figures/impact.png`

**Speaker note:**
- Formulas, ranges, and limits: `research/impact.md`.
- New-load rates: `research/implementation.md`.
- The BPA rate is `BPA_CO2_LB_MWH` (212.458 lb/MWh, eGRID2023 BPAT) in `etl/impact.py`.
- Figure values are recomputed with `etl/impact.py` into `docs/figures/facts.json` (`grant_ranges`, `impact`).

## 7. Risk assessment

**Headline:** One risk is high: whether the utility can serve the load. Grant
holds as the pick only if the campus funds its own clean supply.

- **Power availability (residual high):** the utility's share of its dams
  averages about 633 MW, below its 757 MW load. About 800 MW of large-load
  requests are queued, and large users fund the generation and transmission
  they need. The campus would add 279 average MW.
- **Medium risks with known mitigations:** heat (heat wave score worse than
  97% of counties; days above 95°F rise from 14.5 to 35.9 by 2050), wildfire
  (worse than 87%), the carbon claim, and a sales tax exemption that no
  longer covers replacement servers.
- **Low:** water stress, once dry cooling is chosen. Also flood, hurricane,
  and tornado exposure, and community pushback (none recorded).

**Figure:** the risk table from `research/risk.md`, with five columns: risk,
data, why it matters, mitigation, residual. Lead with the power availability
row.

**Speaker note:** Every row, its columns, and its sources are in
`research/risk.md`. Rerun it with `python -m etl.risk 53025`.

## 8. Implementation vision

**Headline:** Start small behind the utility's queue, grow to 300 MW only as
new clean supply the campus pays for comes online, and cool without water.

- **Phases:** energize a first phase once Quincy's transmission upgrades land
  in 2027 and 2029. Contract about 1 GW of new solar, wind, and storage
  through the utility in the first decade, then firm clean power in the
  2030s. That meets Washington's 2030 and 2045 clean standards.
- **Cooling and heat:** closed-loop warm-water liquid cooling with dry
  coolers, designed for the tripling of 95°F days by 2050. Site next to a
  food processor so 45 to 65°C return water can feed process heat.
- **Cost:** energy costs $196M to $323M a year at the new-load rate, against
  $162M at today's average price and Loudoun's $226M. Grant costs more than
  Loudoun above about $92.50 per MWh.

**Figure:** the phase table from `research/implementation.md`.

**Speaker note:** The plan in five sentences, the phase table, and the
sources marked [C], [P], or [U] are in `research/implementation.md`.

## 9. The 2050 view

**Headline:** The shortlist holds through 2050. What changes is heat: by
mid-century Grant's cooling load matches Loudoun's today, and Grant already
has more days above 95°F.

- Grant's cooling degree days rise from 655 to 1,177 under RCP 8.5 at
  mid-century, about Loudoun's 1,132 today; Loudoun rises to 1,888. But
  Grant has more peak heat: 14.5 days above 95°F today against Loudoun's
  5.0, and 35.9 against 30.3 by 2050.
- Under the 2050 horizon, no top-10 county moves more than one place.
- Water stress barely moves: 727 of 1,254 US basins have the same Aqueduct
  score in 2050, all at 0 or the cap of 5, and Grant stays at 3.6. Cooling
  degree days and days above 95°F carry the horizon story. Design cooling
  for 2050 design days.

**Figure:** `docs/figures/horizon_2050.png`

**Speaker note:** County values are in `docs/figures/facts.json`
(`horizon_2050_figure`). Rank movement is in `results/balanced.csv`
(`rank_delta_2050`), Loudoun's cooling degree days in `research/impact.md`,
and the basin saturation in the manifest notes.

## 10. Limitations

**Headline:** The engine screens on what's installed and what's average. A
new 300 MW load gets neither, so the feasibility study has the last word.

- **Installed versus available:**
  - Nearby capacity counts installed generation. Grant has 16,193 MW within 100 km, yet its utility has no spare hydro for a new load.
  - Price is a state average. A new load pays more, so the cost pillar ranks states and adds nothing within a state.
  - NWPP's 632 lb/MWh overstates Pacific Northwest emissions.
- **Proxies and gaps:**
  - Fiber is last-mile, not backbone. The heat sink score is a rough stand-in for heat reuse.
  - Coverage is 0.73 to 0.78: 10 of 45 mapped columns aren't in the table.
  - Permitting is three hand-coded state-level integers, so it's exempt from the floor.
  - The engine doesn't score proximity to protected or sensitive land. We checked it by hand for Grant, Clark, and Franklin: no conflict at Quincy, where the nearest protected land is a state wildlife area 5.8 km away and the nearest tribal land is 75 km away. A county protected-land share was built and measured but isn't scored.
  - Retired coal is 0 in 2,884 counties and acts like a yes/no flag. Counties can rise on population decline, a stated value choice.
- **Judgment and cutoffs:**
  - The weights are judgments. The default robustness test varies each by only about 0.03; under uniformly random weights Grant is in the top 10 50.5% of the time.
  - First place leads by 0.5 points.
  - Indiana County PA, with Homer City and 2,230 MW of retired coal, misses the 0.2 fiber gate at 0.1996.
  - Loudoun VA fails our queue age gate.
  - Delivered queue capacity uses the actual online date where LBNL has one and the proposed date otherwise, which covers every ISO-NE project and 82% in the West. It's evidence the queue delivers, not capacity available to a new load.

**Figure:** none. Text slide.

**Speaker note:**
- Numbers: `docs/figures/facts.json` (`limitations`, `weights`, `gap_first_to_second`).
- The installed-versus-available gap: `research/risk.md` and `research/implementation.md`.
- Sensitive land: `research/sensitive_land.md`. Grant County is 12.8% PAD-US GAP 1-2 protected land, the 89th percentile, but none within 5 km of Quincy. Scoring that county share in the land pillar would move Grant from 1st to 4th behind Whitman WA, which is why it isn't scored without a team decision. A federal connection, such as a federal permit or a BPA interconnection, triggers Section 106 tribal consultation; state funding triggers Washington Executive Order 21-02 review.
- Proxy definitions: `docs/conditions.md` and the manifest notes.

## 11. The engine as the product

**Headline:** The deliverable is the engine, not the answer: change the
conditions file and you get a new, explained shortlist in seconds.

- One YAML file sets the facility, gates, weights, floor, and horizon. The
  same file runs from the app or the command line and gives the same
  ranking.
- Three presets show the range:
  - **balanced:** 1,565 pass, and Grant WA is first.
  - **speed_to_power:** 779 pass, and Wayne TN is first.
  - **sustainability_first:** 179 pass, and Whitman WA is first. Grant is fifth.
- Every ranked county comes with its reasons, its gate log, its coverage,
  and any flag, such as the 30 ranked counties under a state moratorium. No
  network calls are made at run time.

**Figure:** a screenshot of the app with the conditions YAML expander open.
Take it from the live demo; the click path is in `docs/demo_script.md`.

**Speaker note:** Preset counts are in `results/*_report.json` and
`docs/figures/facts.json` (`presets`). The conditions format is in
`docs/conditions.md`.

## 12. The engine carries to another region

**Headline:** The same engine ranked 196 countries after about 40 lines of
change. That shows it carries to another region; it isn't a country
recommendation.

- **What changed:** only the row identity. An optional `unit` block names the
  key, name, and group columns. Gates, percentiles, pillar means, weights,
  the floor, and robustness are the same code. The US presets still
  reproduce their results byte for byte.
- **Result:** 83 of 196 countries pass the gates and 55 pass the floor.
  Sweden, Switzerland, and Norway lead, with robustness 100%.
- **Why it isn't a recommendation:**
  - There's no cost pillar, because no open global industrial power price exists.
  - The United States ranks 58th of 83 because a national hazard average (climate pillar 16.2) fails the floor. That says nothing about a site in Ohio.
  - A country isn't a site. Use it to choose which country's sub-national data to build next.

**Figure:** `docs/figures/global_table.png`

**Speaker note:** The method, sources, and the United States explanation are
in `docs/global.md`. The ranks are in `results/global_balanced.csv` and
`results/global_balanced_report.json`, and `docs/figures/facts.json`
(`global`) has the counts.
