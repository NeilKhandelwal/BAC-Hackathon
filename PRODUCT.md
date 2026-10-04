# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vite, React, and TypeScript in `app/cockpit/`, built to static files. D3
and TopoJSON render the county map, while React owns application state and
DOM composition. The synchronized map, ranking, comparison, URL state, and
presentation state justify a framework. No server and no live API calls on
demo day.

The Streamlit app at `app/app.py` stays as the team's working tool and
fallback. The cockpit is the recorded and judged demo.

The split:

- The engine of record is the Python package in `engine/` (`rank.py`). The
  cockpit ports its semantics and never redefines them. Where a rule is
  still being corrected, the cockpit reads it from adapter metadata.
- Python exports raw county values for every scored and gate column, plus
  the presets. The browser computes national percentiles, gates, pillar
  means, the weighted composite, the floor rule, and rank stability, so
  judges can change weights, gates, horizon, and county selection.
- A typed data adapter sits between the UI and the export. The shipped
  `engine-export.json` contains real county values; a clearly labeled
  synthetic fixture remains available only as a development fallback.
- A parity test checks the browser engine against `results/*.csv` for each
  preset, including gate and floor counts, the complete rank order, and
  shortlist scores.
- County geometry comes from `data/processed/counties.geojson`, simplified
  to TopoJSON at build time.
- Portfolio mode is a future capability, not part of the hackathon build.

## Presentation

One real application serves both a 2 to 3 minute recorded video and a live
judge demo. There's no separate demo build and no tooltip tour.

- A presentation preset loads a known-good scenario and viewport.
- App state is URL-addressable, so a recording opens directly at a scenario.
- One-click Reset Demo and Exit Presentation controls.
- Mostly single-screen and composed for 16:9 recording. Screenshots of it
  go into the pitch deck.
- Large labels, strong contrast, and no information that only appears on
  hover.
- Transitions show cause and effect, especially rank changes.
- Optional story cues with Next and Back. They come after the core decision
  workflow works.
- Unexpected input and missing values degrade gracefully. Examples: weights
  that sum to zero, gates that exclude every county, or a county with null
  pillars.

## Users

Primary audience for the demo: hackathon judges. The rubric weights
Technology, Presentation, Innovation, Execution, and Theme equally. Judges
see the product framed through its intended user: a site-selection lead at
a data center developer or hyperscaler. That user has conditions, needs a
defensible shortlist, and has to answer a board asking "why not county X."

Secondary user, named in the README but not a demo focus: a county economic
development office that runs the engine in reverse.

## Product Purpose

A decision engine that scores every county in the contiguous US (3,109) as
a site for a next-generation sustainable AI data center. Conditions go in.
A ranked, explained shortlist comes out. It reruns with new conditions, new
data, or a new region without changing the engine.

Success for the demo: judges see conditions change and the ranking respond.
They see why a county wins and why an obvious county loses. They leave
trusting that the method is transparent and defensible.

## Positioning

The engine scores both sustainable and buildable. Real projects fail on
power delivery timelines, local opposition and rezoning denials, water, and
electricity-bill politics. The ranking includes those, not only the brief's
sustainability factors.

- The ranking is transparent multi-criteria analysis, not ML. A learned
  ranker would reproduce where the industry already built.
- No ML output ships. A permitting model was trained on FracTracker
  outcomes and dropped for lack of skill (`research/permitting_model.md`).
- An LLM may write explanations. It never decides.
- Rank stability shows how often each county stays in the top 10 when the
  weights are resampled. It describes sensitivity to decision priorities,
  not a probability, and the product never calls it confidence or
  likelihood.

## Operating Context

- Live demo in front of judges, plus a deck of about twelve slides.
- Pipeline: `conditions.yaml` plus `county_features.parquet` go to gates,
  then percentile scores per pillar, then a weighted composite with a
  pillar floor rule. Rank stability and explanation layers follow.
- Eight pillars in `engine/pillars.yaml`: energy and carbon, water, climate
  resilience, grid and infrastructure, land, community, permitting, and
  cost. Permitting is exempt from the floor in the presets.
- Two horizons: today and 2050.
- Three presets in `engine/conditions/`: balanced, speed_to_power,
  sustainability_first.
- Hackathon ends Sunday morning. Execution and Presentation are 40 percent
  of the score. A broken demo costs more than a missing feature.

## Capabilities and Constraints

Planned demo capabilities:

- Pick a preset, then adjust pillar weights, gates, and horizon live.
- Choropleth map of county scores.
- Top-10 table with pillar breakdown and rank stability.
- County detail: per-pillar contributions, evidence, coverage, gate log,
  "why not" for excluded counties, and the 2050 shift.
- The interface keeps four kinds of number visibly distinct: observed
  source data, derived scores, rank stability under weight variation, and
  projected future climate.

Constraints:

- The demo must not depend on live API calls. Everything is precomputed to
  static files.
- Specs: `docs/schema.md` (county table), `docs/conditions.md` (conditions
  format), `engine/pillars.yaml` (pillar mapping).
- Climate projections are CMIP5 LOCA via CMRA, and the product says so.

Undecided:

- Product name. Choose one near the end of the build.
- Featured site. The deck currently leads with Grant County, WA from the
  committed results; the cockpit never hand-picks a winner.

## Evidence on Hand

- Committed county feature table, 3,109 counties
  (`data/processed/county_features.parquet` with manifest and quality
  report). The manifest lists scored columns not yet built, such as solar,
  land cover, and reliability; they lower coverage.
- Committed engine results per preset in `results/`, and county geometry
  in `data/processed/counties.geojson`.
- Opposition seed labels: 246 projects in
  `data/processed/opposition_seed_labels.csv`. Values ending in `?` were
  inferred, not checked. The approved class is noisy, and there are no
  true negatives.
- Context figures from Data Center Watch: 48 projects worth $156B blocked
  or delayed in 2025, and 75 worth $130B in Q1 2026.
- Research notes in `research/`.

Absent, and not to be fabricated: customers, testimonials, real
deployments, and model accuracy figures.

FracTracker Alliance data is free for non-commercial use with credit. The
credit must appear wherever the data is shown.

## Product Principles

1. Explain every ranking. A score without a reason doesn't belong in the
   UI.
2. Show the losers. "Why not county X" matters as much as the winner.
3. The user's weights decide. Defaults only need to be defensible.
4. Be honest about data limits: model vintage, inferred labels, missing
   columns.
5. Demo reliability beats feature count.
