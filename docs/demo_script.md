# Demo script

A five-minute click path through the app. It shows one decision engine
answering a site-selection lead's question, then answering a harder version
of it when one condition changes.

Every number below was checked against the live app on `main` (commit
`fa2de5a`) with the committed `data/processed/county_features.parquet`. If
the table or presets change, rerun the click path and update the numbers
before you rehearse.

## Before you start

1. From the repo root, run `streamlit run app/app.py`. It needs no network
   connection and no environment variables; it reads
   `data/processed/county_features.parquet` and
   `data/processed/counties.geojson`.
2. Open `http://localhost:8501` and wait for the map to draw.
3. Make sure the preset is `balanced` and the facility is 300 MW. If you
   changed anything while practicing, reload the page.
4. Use a window at least 1,400 px wide so the shortlist table fits.

## Click path

| Time | Click | What the screen shows | What you say |
| --- | --- | --- | --- |
| 0:00 | Nothing. | Headline: `balanced · horizon 2026 · 1,301 of 3,109 counties pass the gates · 397 pass the pillar floor`. The map colors the 1,301 counties; excluded counties are grey. | "You're a site-selection lead with a 300 MW AI campus to place. The engine scores all 3,109 counties in the contiguous US on seven pillars: energy and carbon, water, climate resilience, grid, land, community, and permitting." |
| 0:40 | Hover a grey county, then a colored one. | Grey hover names the gate that excluded it, for example `excluded: min_fiber_share_locations` on Centre County, PA. Colored hover shows the rank and composite. | "Hard gates come first: flood and wildfire caps, fiber, interconnection queue age, moratoria, and enough power generation nearby. A grey county failed one, and the engine tells you which." |
| 1:00 | Scroll to **Shortlist**. | Top 10, led by Hillsborough NH, Onondaga NY, Worcester MA. Grant WA is 7th. Columns show each pillar score, robustness, and coverage. | "Among the counties that pass, each pillar is a national percentile. A county weak on any one pillar can't outrank a county that isn't; that's the floor rule. Robustness is the share of 2,000 random weight draws in which the county stays in the top 10." |
| 1:40 | In the sidebar, open **Facility and horizon** and set **Facility IT load (MW)** to `1000`. Press Enter. | Headline: `balanced_edited (edited) · 847 of 3,109 counties pass the gates · 274 pass the pillar floor`. More counties turn grey. | "Now the tenant wants 1,000 MW instead of 300. One condition changes. The engine requires five times the facility's load in power plants within 100 km, so the bar goes from 1,500 MW to 5,000 MW. 454 counties drop out." |
| 2:20 | Scroll to **Shortlist**. | Erie NY and Clinton NY are gone. Luzerne PA and Olmsted MN enter. Grant WA moves from 7th to 6th. | "Erie has 4,600 MW nearby and Clinton has 2,600: fine for 300 MW, not for 1,000. Grant County, Washington, has 16,000 MW of plants within 100 km, mostly Columbia River hydro, so it moves up." |
| 2:50 | In **Find a county**, type `53025` and pick `Grant, WA (53025)`. | `Rank 6 of 847 · composite 65.2 · passes the floor · robustness 96% · coverage 72%`. Top reasons: state policy risk, land area, existing data centers. Pillar bars, all above 50. | "Grant ranks sixth, and it stays in the top 10 in 96% of weight draws. That's a robust answer, not an artifact of our weights. The reasons are specific: no adverse state policy, plenty of land, and three operating data centers in the FracTracker tracker, which means power and fiber are proven there." |
| 3:30 | Point at **Raw change by 2050**. | Cooling degree days 655 to 1,177. Days above 95F 14 to 36. | "The facility runs 30 years, so the engine also scores 2050 climate. Grant's cooling load nearly doubles by mid-century under RCP 8.5. A site lead needs that number before signing, and the ranking alone hides it." |
| 3:55 | In **Find a county**, type `41067` and pick `Washington, OR (41067)`. | Red box: `Excluded by: min_nearby_capacity_multiple`. | "Hillsboro, Oregon, is a real hub, and the engine excludes it at 1,000 MW. It has 4,200 MW of plants within 100 km, but a real hub draws on the regional grid beyond that radius. Our gate counts nearby generation, not transmission, and we say so in the methods. The engine shows exactly why a county is out, so you can overrule it." |
| 4:25 | In the sidebar, open **Conditions YAML**. | The YAML shows `name: balanced_edited` and `mw: 1000`. **Download conditions YAML** sits above it. | "Everything you just changed is a plain conditions file. Download it, edit it, rerun it from the command line, and you get the same shortlist. The conditions file is the product's interface." |
| 4:50 | Stop. | | "Conditions in, a ranked and explained shortlist out, repeatable with new data. That's the decision engine." |

## Likely questions

- **Why is permitting a whole pillar if the model was dropped?** It scores
  three sourced columns: air quality nonattainment, water permit risk, and
  state policy risk. The machine-learning model had no skill once facility
  counts were removed, so we cut it rather than ship a score we couldn't
  defend.
- **What are the 12 warnings in Data notes?** Scored columns that aren't in
  the table yet, such as NREL solar and NLCD land cover. The engine drops
  them from scoring and shows the gap as lower coverage, which is why
  Grant's coverage is 72%.
- **Why does heat reuse appear as a reason so often?** The community pillar
  has two columns, so each carries more weight than a single climate column.
  That's the composite's arithmetic, not a bug, and the weights are
  adjustable in the sidebar.
- **Is 5x nearby generation a real capacity check?** No. It's a proxy for
  transmission and substation capacity, not a load-flow study. Hillsboro is
  the honest counterexample.

## If something goes wrong

- **The map is slow to redraw:** keep talking. Reruns take about 1.5 s; the
  first change after a reload takes about 3 s.
- **A number differs from this script:** the table changed after this script
  was checked. Say the number on screen, not the one here.
- **The app shows an error box after a slider change:** you set every weight
  to 0. Reload the page.
