# Demo script

A five-minute click path through the app. It shows one decision engine
answering a site-selection lead's question, flagging a policy risk the score
can't capture, and giving a different answer when one condition changes: the
cooling technology.

Checked against the live app at commit `c192e5e` (engine and app) on the
`longrun-moratorium` branch, with the committed
`data/processed/county_features.parquet` (3,109 counties). If the table or
presets change, rerun the click path and update the numbers before you
rehearse.

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
| 0:00 | Nothing. | Headline: `balanced · horizon 2026 · 1,565 of 3,109 counties pass the gates · 993 pass the pillar floor · 30 ranked counties are under a state moratorium`. Colored counties passed; grey counties failed a gate. | "You're a site-selection lead placing a 300 MW AI campus. The engine scores all 3,109 counties in the contiguous US on seven pillars: energy and carbon, water, climate resilience, grid, land, community, and permitting." |
| 0:30 | Hover a grey county in Pennsylvania, then a colored one in Illinois. | Grey: `Centre, PA excluded: min_fiber_share_locations`. Colored: `Kane, IL rank 546 composite 51.02`. | "Hard gates come first: flood and wildfire caps, fiber, interconnection queue age, moratoria, and enough power generation nearby. A grey county failed one, and the engine says which." |
| 0:50 | Scroll to **Shortlist**. | Top 10: Berkshire MA, Franklin NY, Erie NY, Clinton NY, Onondaga NY, Worcester MA, Grant WA (7th), Whitman WA, Luzerne PA, Rock Island IL. The **state moratorium** column is checked for the four New York counties. | "Each pillar is a national percentile, and a county weak on any pillar can't outrank one that isn't. Robustness is the share of 2,000 random weight draws in which a county stays in the top 10. Four of the top five are in New York, and they're flagged." |
| 1:20 | In **Find a county**, type `36033` and pick `Franklin, NY (36033)`. | `Rank 2 of 1565 · composite 63.6 · passes the floor · robustness 98% · coverage 78%`. Yellow box: `State moratorium in effect. A facility this size can't get state permits today.` | "On the physical merits, Franklin County is second, and robust. But New York's Executive Order 62 pauses state environmental permits for data centers of 50 MW or more for about a year. The engine doesn't hide a good site, and it doesn't pretend you can build there today. It tells you both." |
| 2:00 | In **Find a county**, type `53025` and pick `Grant, WA (53025)`. | `Rank 7 of 1565 · composite 61.4 · passes the floor · robustness 65% · coverage 78%`. Top reasons: state policy risk, land area, nearby clean generation. | "Grant County, Washington, is the Quincy data center cluster. It's a strong site for an air-cooled campus: favorable state policy, room to build, and clean generation nearby." |
| 2:30 | In the sidebar, under **Facility and horizon**, set **Cooling** to `evaporative`. | Headline: `balanced_edited (edited) · 826 of 3,109 counties pass the gates · 601 pass the pillar floor · 29 ranked counties are under a state moratorium`. More counties turn grey on the map. | "Now the operator wants evaporative cooling. It uses far less power than chillers, but it consumes water. One condition changes, and it switches on a water stress gate: no county above 2 on the 0 to 5 Aqueduct scale. 739 counties drop out." |
| 3:00 | In **Find a county**, pick `Grant, WA (53025)` again. | Red box: `Excluded by: max_water_stress_if_evaporative`. **Raw change by 2050** shows Water stress (Aqueduct, 0 to 5) at 3.6 today. | "Grant scores 3.6 of 5 for water stress, which is high. The engine won't put an evaporatively cooled campus there, and it tells you exactly why. Switch back to dry cooling and Grant is seventh again. Cooling technology is a siting decision." |
| 3:40 | In **Find a county**, type `53075` and pick `Whitman, WA (53075)`. | `Rank 7 of 826 · composite 61.1 · passes the floor · robustness 61% · coverage 76%`. **Raw change by 2050**: water stress 0.0 today and 0.5 in 2050; cooling degree days 362.1 to 838.3. | "Whitman County, also in eastern Washington and on the same clean Northwest grid, scores 0 for water stress today, so the same operator can stay in the region. Its cooling load more than doubles by 2050 under RCP 8.5, which a 30-year facility has to plan for." |
| 4:20 | In the sidebar, open **Conditions YAML**. | The YAML shows `name: balanced_edited` and `cooling: evaporative`. **Download conditions YAML** sits above it. | "Everything you just changed is a plain conditions file. Download it, rerun it from the command line, and you get the same shortlist. The conditions file is the product's interface." |
| 4:50 | Stop. | | "Conditions in, a ranked and explained shortlist out, repeatable with new data. That's the decision engine." |

## If you have an extra minute

Set **Cooling** back to `dry`, then set **Facility IT load (MW)** to `1000`.
The headline drops to 1,023 counties passing the gates and 679 passing the
floor, because the engine requires plants within 100 km totaling five times
the facility's load. Franklin, Erie, and Clinton in New York drop out of the
top 10, and Grant WA rises to 4th. Washington OR, the Hillsboro hub, is
excluded by `min_nearby_capacity_multiple`: it has 4,200 MW of plants within
100 km, but a real hub also draws on the regional grid beyond that radius.
Use it as the honest limitation: the gate counts nearby generation, not
transmission.

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
  seventh; that's the point of making it a condition rather than a fixed rule.

- **Why rank New York counties at all if they can't be permitted?** The
  moratorium is a policy pause of about a year, not a physical limit, and a
  site lead planning for 2028 or later needs to know these are the
  strongest sites on the merits. The flag comes from the data, so it follows
  whichever states the table marks. To drop them, turn on
  `exclude_moratorium_state_active`, as the `speed_to_power` preset does.
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
