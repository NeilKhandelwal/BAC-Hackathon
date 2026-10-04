# Demo script

A five-minute click path through the app. It shows one decision engine
answering a site-selection lead's question, then a different answer when one
condition changes: the cooling technology.

Numbers recomputed with the engine on `fix/sensitive-land`, after protected
land, tribal land, and NLCD land cover joined the committed
`data/processed/county_features.parquet` (3,109 counties). The app calls the
same engine, but the click path wasn't re-run by hand in the browser. If the
table or presets change, rerun the click path and update the numbers before
you rehearse.

## Before you start

1. From the repo root, run `streamlit run app/app.py`. It needs no network
   connection and no environment variables; it reads
   `data/processed/county_features.parquet` and
   `data/processed/counties.geojson`.
2. Open `http://localhost:8501` and wait for the map to draw.
3. Make sure the preset is `balanced` and **Cooling** is `dry`. If you
   changed anything while practicing, reload the page.
4. Use a window at least 1,400 px wide so the shortlist table fits.

## Click path

| Time | Click | What the screen shows | What you say |
| --- | --- | --- | --- |
| 0:00 | Nothing. | Headline: `balanced · horizon 2026 · 1,565 of 3,109 counties pass the gates · 883 pass the pillar floor · 30 ranked counties are under a state moratorium`. Colored counties passed; grey counties failed a gate. | "You're a site-selection lead placing a 300 MW AI campus. The engine scores all 3,109 counties in the contiguous US on eight pillars: energy and carbon, water, climate resilience, grid, land, community, permitting, and the cost of power." |
| 0:30 | Hover a grey county in Pennsylvania, then a colored one in Illinois. | Grey: `Centre, PA excluded: min_fiber_share_locations`. Colored: `Kane, IL rank 1355 composite 48.01`. | "Hard gates come first: flood and wildfire caps, fiber, interconnection queue age, moratoria, and enough power generation nearby. A grey county failed one, and the engine says which." |
| 0:50 | Scroll to **Shortlist**. | Top 10: Grant WA, Whitman WA, Benton WA, Mayes OK, Payne OK, Clark WA, Grady OK, Marshall IA, Hutchinson TX, Walla Walla WA. | "Each pillar is a national percentile, and a county weak on any pillar can't outrank one that isn't. Robustness is the share of 2,000 random weight draws in which a county stays in the top 10." |
| 1:20 | In **Find a county**, type `53025` and pick `Grant, WA (53025)`. | `Rank 1 of 1565 · composite 63.7 · passes the floor · robustness 100% · coverage 87%`. Top reasons: industrial price, forest and wetland share, state policy risk. The pillar bars include **cost**, and the land pillar now includes protected land and cropland. | "Grant County, Washington, home of the Quincy data center cluster, ranks first: cheap power, little forest or wetland to permit around, and favorable state policy. It's level with Whitman County, 0.01 points behind, and both stay in the top 10 in essentially every weight draw. The land pillar now counts protected land and cropland, so the engine checks sensitive land instead of leaving it to luck." |
| 2:00 | In the sidebar, under **Facility and horizon**, set **Cooling** to `evaporative`. | Headline: `balanced_edited (edited) · 826 of 3,109 counties pass the gates · 502 pass the pillar floor · 29 ranked counties are under a state moratorium`. More counties turn grey on the map. | "Now the operator wants evaporative cooling. It uses far less power than chillers, but it consumes water. One condition changes, and it switches on a water stress gate: no county above 2 on the 0 to 5 Aqueduct scale. 739 counties drop out, and so does our first choice." |
| 2:30 | In **Find a county**, pick `Grant, WA (53025)` again. | Red box: `Excluded by: max_water_stress_if_evaporative`. **Raw change by 2050** shows Water stress (Aqueduct, 0 to 5) at 3.6 today. | "Grant scores 3.6 of 5 for water stress, which is high. The engine won't put an evaporatively cooled campus there, and it tells you exactly why. Switch back to dry cooling and Grant is first again. Cooling technology is a siting decision." |
| 3:10 | In **Find a county**, type `53075` and pick `Whitman, WA (53075)`. | `Rank 1 of 826 · composite 63.7 · passes the floor · robustness 100% · coverage 84%`. **Raw change by 2050**: water stress 0.0 today and 0.5 in 2050; cooling degree days 362.1 to 838.3. | "Whitman County, also in eastern Washington, scores 0 for water stress today and ranks first, so the same operator can stay in the region with the same cheap power. Its cooling load more than doubles by 2050 under RCP 8.5, which a 30-year facility has to plan for." |
| 3:50 | In the sidebar, open **Conditions YAML**. | The YAML shows `name: balanced_edited` and `cooling: evaporative`. **Download conditions YAML** sits above it. | "Everything you just changed is a plain conditions file. Download it, rerun it from the command line, and you get the same shortlist. The conditions file is the product's interface." |
| 4:30 | Stop. | | "Conditions in, a ranked and explained shortlist out, repeatable with new data. That's the decision engine." |

## If you have an extra minute

Set **Cooling** back to `dry`, then set **Facility IT load (MW)** to `1000`.
The headline drops to 1,023 counties passing the gates and 611 passing the
floor, because the engine requires plants within 100 km totaling five times
the facility's load. Grant WA stays first: it has 16,193 MW of plants within
100 km. Use it as the honest limitation: that column counts installed
generation, not capacity available to a new customer, and a new large load
in Grant would need new supply. The sourced version is in the risk
write-up.

## Stage 2: industrial reuse (Boone County, IL)

Use this after the main click path, or in place of the extra minute. Grant
and Loudoun still demonstrate the national model; Boone demonstrates the
screening layer that comes after it.

| Click | What the screen shows | What you say |
| --- | --- | --- |
| In **Find a county**, type `17007` and pick `Boone, IL (17007)`. Scroll past the pillar bars. | **Industrial reuse and community transition**, captioned as unscored, post-ranking screening, and the yellow statement: "Economic need is not evidence of community support. Local engagement and project-level validation are still required." | "After the ranking, a site lead wants to know what a community has been through and what land might be reused. This section doesn't change any rank." |
| Point at **Economic transition**. | Manufacturing jobs 7,761 in 2015 and 2,070 in 2024: -5,691 (-73%), national percentile 1, read as "Low percentile = steeper decline". Unemployment 6.2% for 2022-2024 against a 3.6% national median. | "Boone lost almost three quarters of its manufacturing jobs since 2015, after the Belvidere assembly plant went idle. The 1st percentile here means one of the steepest losses in the country, not a good score." |
| Scroll to **Brownfield properties**. | 8 EPA brownfield properties in Belvidere, 0.8 to 11.9 acres, none listed ready for reuse, substations 1.3 to 2.0 miles away, 138 kV where reported. **Download this county's 8 brownfield properties (CSV)**. | "These are candidates with a cleanup history, not available land. None is large enough for a 300 MW campus on its own." |
| Point at the two blocks below. | **Why this community could benefit** (job losses, long-run manufacturing decline, unemployment, brownfields) beside **What still requires local verification** (utility capacity, ownership, cleanup, zoning, permits, transmission, local engagement, tax and community-benefit agreements). | "The data shows need and assets. Whether the community wants a data center is something only local engagement can answer." |
| Click **Download county screening brief (Markdown)**. | A file `screening_brief_17007.md`. | "Everything on screen, with the risks and missing data, in one file for the site team." |

If `data/processed/brownfield_sites.parquet` is missing (a fresh clone that
hasn't run the ETL), the property table is replaced by a note that the ETL
generates it. The county totals (8 properties, 43.6 reported acres) still
show from the committed feature table. Run `python -m etl.build_features
--no-fetch` with cached downloads, or `python -m etl.build_features`, to
produce it.

## Likely questions

- **Why does permitting score if the model was dropped?** It scores three
  sourced columns: air quality nonattainment, water permit risk, and state
  policy risk. They're coarse state-level integers, so the pillar counts in
  the composite but can't fail a county on the floor. The machine-learning
  model had no skill once facility counts were removed, so we cut it.
- **What are the warnings in Data notes?** Scored columns that aren't in the
  table yet, such as NREL solar, grid water intensity, and EIA reliability.
  The engine skips them and shows the gap as lower coverage, which is why
  coverage reads 84% to 87%.
- **Does the engine check protected or tribal land?** Yes, as county shares.
  The land pillar scores PAD-US protected land and NLCD cropland, and the
  sidebar has optional gates for maximum protected and tribal land share. A
  county share is a screen, not a siting check: Grant County is 12.8%
  protected, but the nearest protected land is 5.8 km from Quincy
  (`research/sensitive_land.md`).
- **Why does Grant's water stress not change by 2050?** Water is the pillar
  that moves least under the 2050 switch. Aqueduct's score saturates: 727
  of 1,254 US basins have the same baseline and 2050 business-as-usual
  score, all at 0 or at the cap of 5, so county averages over them stay
  flat. The horizon story is carried by cooling degree days and days above
  95°F.
- **Is the water gate too blunt?** It's a threshold on a basin-level score,
  set by the conditions file. Raise it to 4 and Grant passes and ranks
  first; that's the point of making it a condition rather than a fixed rule.

- **Where did New York go?** Under the old seven pillars, four upstate New
  York counties sat in the top five. With power cost weighted at 15%, New
  York's industrial price drops them below the cost floor; the best is
  Franklin NY at 986th. They'd still carry the state moratorium flag, which
  the headline counts.
- **Why does cost rank whole states?** The price column is one state
  average per state, so the cost pillar separates states, not counties
  within one, and a new 300 MW load would likely pay a higher large-load
  rate.
- **Why does the community pillar favor declining places?** It's a stated
  value choice, not a prediction: the brief lists economic development
  under community impact, and a campus brings more benefit where jobs are
  scarce and a county has declined against its own history. It's 10% of
  the balanced weight, and the opposition model found no dependable link
  between these measures and pushback.

## If something goes wrong

- **The map is slow to redraw:** keep talking. Reruns take about 1.5 s; the
  first change after a reload takes about 3 s.
- **A number differs from this script:** the table changed after this script
  was checked. Say the number on screen, not the one here.
- **The app shows an error box after a slider change:** you set every weight
  to 0. Reload the page.
- **Boone shows a note instead of a brownfield property table:** the
  generated site file is absent. Say "the property list comes from the ETL
  run" and continue; the county totals above it are still real.
