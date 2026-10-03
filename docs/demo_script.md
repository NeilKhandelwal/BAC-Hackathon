# Demo script

A five-minute click path through the app. It shows one decision engine
answering a site-selection lead's question, then a different answer when one
condition changes: the cooling technology.

Checked against the live app on `main` at commit `c43828c`, with the
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
| 0:00 | Nothing. | Headline: `balanced · horizon 2026 · 1,565 of 3,109 counties pass the gates · 492 pass the pillar floor`. Colored counties passed; grey counties failed a gate. | "You're a site-selection lead placing a 300 MW AI campus. The engine scores all 3,109 counties in the contiguous US on seven pillars: energy and carbon, water, climate resilience, grid, land, community, and permitting." |
| 0:40 | Hover a grey county in Pennsylvania, then a colored one in Illinois. | Grey: `Centre, PA excluded: min_fiber_share_locations`. Colored: `Kane, IL rank 728 composite 52.98`. | "Hard gates come first: flood and wildfire caps, fiber, interconnection queue age, moratoria, and enough power generation nearby. A grey county failed one, and the engine says which." |
| 1:00 | Scroll to **Shortlist**. | Top 10: Berkshire MA, Franklin NY, Erie NY, Onondaga NY, Worcester MA, Clinton NY, Grant WA (7th), Washington OR (8th), Hillsborough NH, Bennington VT. | "Each pillar is a national percentile. A county weak on any pillar can't outrank one that isn't; that's the floor rule. Robustness is the share of 2,000 random weight draws in which a county stays in the top 10. Grant County, Washington, is the Quincy data center cluster. It's seventh." |
| 1:40 | In **Find a county**, type `53025` and pick `Grant, WA (53025)`. | `Rank 7 of 1565 · composite 63.6 · passes the floor · robustness 79% · coverage 76%`. Top reasons: state policy risk, land area, population. | "Quincy is a strong site for an air-cooled campus: favorable state policy, room to build, and 16,000 MW of plants within 100 km, mostly Columbia River hydro." |
| 2:10 | In the sidebar, under **Facility and horizon**, set **Cooling** to `evaporative`. | Headline: `balanced_edited (edited) · 826 of 3,109 counties pass the gates · 309 pass the pillar floor`. More counties turn grey on the map. | "Now the operator wants evaporative cooling. It uses far less power than chillers, but it consumes water. One condition changes, and it switches on a water stress gate: no county above 2 on the 0 to 5 Aqueduct scale. 739 counties drop out." |
| 2:40 | Scroll to **Shortlist**. | Grant WA is gone. Washington OR moves up to 7th; Clark WA enters at 10th. | "The rest of the top 10 holds, because those counties already have low water stress. The one that leaves is the most famous name on the list." |
| 3:00 | In **Find a county**, pick `Grant, WA (53025)` again. | Red box: `Excluded by: max_water_stress_if_evaporative`. **Raw change by 2050** shows Water stress (Aqueduct, 0 to 5) at 3.6 today. | "Grant scores 3.6 of 5 for water stress, which is high. The engine won't put an evaporatively cooled campus there, and it tells you exactly why. Switch back to dry cooling and Grant is seventh again. Cooling technology is a siting decision." |
| 3:40 | In **Find a county**, type `41067` and pick `Washington, OR (41067)`. | `Rank 7 of 826 · composite 62.9 · passes the floor · robustness 71% · coverage 76%`. Top reasons include water stress. **Raw change by 2050**: water stress 0 today and in 2050; cooling degree days 214 to 575. | "Hillsboro, Oregon, west of the Cascades, scores 0 for water stress, so the same operator can stay in the Pacific Northwest. Its cooling load more than doubles by 2050 under RCP 8.5, which a 30-year facility has to plan for." |
| 4:20 | In the sidebar, open **Conditions YAML**. | The YAML shows `name: balanced_edited` and `cooling: evaporative`. **Download conditions YAML** sits above it. | "Everything you just changed is a plain conditions file. Download it, rerun it from the command line, and you get the same shortlist. The conditions file is the product's interface." |
| 4:50 | Stop. | | "Conditions in, a ranked and explained shortlist out, repeatable with new data. That's the decision engine." |

## If you have an extra minute

Set **Cooling** back to `dry`, then set **Facility IT load (MW)** to `1000`.
The headline drops to 1,023 counties passing the gates and 352 passing the
floor, because the engine requires plants within 100 km totaling five times
the facility's load. Franklin, Erie, and Clinton in New York drop out of the
top 10, and Grant WA rises to 4th. Washington OR is excluded by
`min_nearby_capacity_multiple`: it has 4,200 MW of plants within 100 km, but
a real hub also draws on the regional grid beyond that radius. Use it as the
honest limitation: the gate counts nearby generation, not transmission.

## Likely questions

- **Why does permitting score if the model was dropped?** It scores three
  sourced columns: air quality nonattainment, water permit risk, and state
  policy risk. They're coarse state-level integers, so the pillar counts in
  the composite but can't fail a county on the floor. The machine-learning
  model had no skill once facility counts were removed, so we cut it.
- **What are the warnings in Data notes?** Scored columns that aren't in the
  table yet, such as NREL solar, NLCD land cover, and EIA reliability. The
  engine skips them and shows the gap as lower coverage, which is why
  coverage is 76%.
- **Why does Grant's water stress not change by 2050?** Aqueduct's 2050
  business-as-usual projection is nearly flat for that basin. The engine
  reports the source value as is.
- **Is the water gate too blunt?** It's a threshold on a basin-level score,
  set by the conditions file. Raise it to 4 and Grant passes and ranks
  seventh; that's the point of making it a condition rather than a fixed rule.

## If something goes wrong

- **The map is slow to redraw:** keep talking. Reruns take about 1.5 s; the
  first change after a reload takes about 3 s.
- **A number differs from this script:** the table changed after this script
  was checked. Say the number on screen, not the one here.
- **The app shows an error box after a slider change:** you set every weight
  to 0. Reload the page.
