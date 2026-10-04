# Demo script

A five-minute click path through the app. It shows one decision engine
answering a site-selection lead's question, then a different answer when one
condition changes: the cooling technology.

Checked against the live app at commit `91dc6eb` on the `cost-pillar` branch
(eight pillars, with the Massachusetts policy correction), using the
committed `data/processed/county_features.parquet` (3,109 counties). If the
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
| 0:00 | Nothing. | Headline: `balanced · horizon 2026 · 1,565 of 3,109 counties pass the gates · 915 pass the pillar floor · 30 ranked counties are under a state moratorium`. Colored counties passed; grey counties failed a gate. | "You're a site-selection lead placing a 300 MW AI campus. The engine scores all 3,109 counties in the contiguous US on eight pillars: energy and carbon, water, climate resilience, grid, land, community, permitting, and the cost of power." |
| 0:30 | Hover a grey county in Pennsylvania, then a colored one in Illinois. | Grey: `Centre, PA excluded: min_fiber_share_locations`. Colored: `Kane, IL rank 805 composite 46.89`. | "Hard gates come first: flood and wildfire caps, fiber, interconnection queue age, moratoria, and enough power generation nearby. A grey county failed one, and the engine says which." |
| 0:50 | Scroll to **Shortlist**. | Top 10: Grant WA, Wayne TN, Whitman WA, Mayes OK, Benton WA, Scott IA, Clark WA, Scott TN, Grady OK, Adair OK. | "Each pillar is a national percentile, and a county weak on any pillar can't outrank one that isn't. Robustness is the share of 2,000 random weight draws in which a county stays in the top 10." |
| 1:20 | In **Find a county**, type `53025` and pick `Grant, WA (53025)`. | `Rank 1 of 1565 · composite 63.7 · passes the floor · robustness 100% · coverage 78%`. Top reasons: industrial price, state policy risk, land area. The pillar bars include **cost**. | "Grant County, Washington, home of the Quincy data center cluster, ranks first: cheap power, favorable state policy, and room to build. It stays in the top 10 in essentially every weight draw." |
| 2:00 | In the sidebar, under **Facility and horizon**, set **Cooling** to `evaporative`. | Headline: `balanced_edited (edited) · 826 of 3,109 counties pass the gates · 542 pass the pillar floor · 29 ranked counties are under a state moratorium`. More counties turn grey on the map. | "Now the operator wants evaporative cooling. It uses far less power than chillers, but it consumes water. One condition changes, and it switches on a water stress gate: no county above 2 on the 0 to 5 Aqueduct scale. 739 counties drop out, and so does our first choice." |
| 2:30 | In **Find a county**, pick `Grant, WA (53025)` again. | Red box: `Excluded by: max_water_stress_if_evaporative`. **Raw change by 2050** shows Water stress (Aqueduct, 0 to 5) at 3.6 today. | "Grant scores 3.6 of 5 for water stress, which is high. The engine won't put an evaporatively cooled campus there, and it tells you exactly why. Switch back to dry cooling and Grant is first again. Cooling technology is a siting decision." |
| 3:10 | In **Find a county**, type `53075` and pick `Whitman, WA (53075)`. | `Rank 2 of 826 · composite 63.0 · passes the floor · robustness 98% · coverage 76%`. **Raw change by 2050**: water stress 0.0 today and 0.5 in 2050; cooling degree days 362.1 to 838.3. | "Whitman County, also in eastern Washington, scores 0 for water stress today and ranks second, so the same operator can stay in the region with the same cheap power. Its cooling load more than doubles by 2050 under RCP 8.5, which a 30-year facility has to plan for." |
| 3:50 | In the sidebar, open **Conditions YAML**. | The YAML shows `name: balanced_edited` and `cooling: evaporative`. **Download conditions YAML** sits above it. | "Everything you just changed is a plain conditions file. Download it, rerun it from the command line, and you get the same shortlist. The conditions file is the product's interface." |
| 4:30 | Stop. | | "Conditions in, a ranked and explained shortlist out, repeatable with new data. That's the decision engine." |

## If you have an extra minute

Set **Cooling** back to `dry`, then set **Facility IT load (MW)** to `1000`.
The headline drops to 1,023 counties passing the gates and 632 passing the
floor, because the engine requires plants within 100 km totaling five times
the facility's load. Grant WA stays first: it has 16,193 MW of plants within
100 km. Use it as the honest limitation: that column counts installed
generation, not capacity available to a new customer, and a new large load
in Grant would need new supply. The sourced version is in the risk
write-up.

## Likely questions

- **Why does permitting score if the model was dropped?** It scores three
  sourced columns: air quality nonattainment, water permit risk, and state
  policy risk. They're coarse state-level integers, so the pillar counts in
  the composite but can't fail a county on the floor. The machine-learning
  model had no skill once facility counts were removed, so we cut it.
- **What are the warnings in Data notes?** Scored columns that aren't in the
  table yet, such as NREL solar, NLCD land cover, and EIA reliability. The
  engine skips them and shows the gap as lower coverage, which is why
  coverage reads 76% to 78%.
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
