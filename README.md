# Data center location decision engine

Software that takes a user's conditions (facility size, deadline, cooling
strategy, carbon target, risk tolerance, priorities) and returns a ranked,
explained shortlist of US counties for a sustainable AI data center. It runs
again with new conditions, new data, or a new region without changing the
engine.

This README is the onboarding doc. Deeper detail is in `research/` and
`docs/`.

## Who it's for

The site-selection lead at a data center developer or hyperscaler. They
have conditions, they need a defensible shortlist, and they'll be asked
"why not county X" by a board. The engine answers that. A county economic
development office is the secondary user, running it in reverse.

## What it does

```
conditions.yaml  +  county_features.parquet
        |
        v
  gates  ->  percentile scores per pillar  ->  weighted composite with a floor rule
        |
        v
  robustness (resample weights, how often is each county top 10?)
  portfolio (pick N sites that don't share a grid or a hurricane basin)
  explanation (per-pillar breakdown, gate log, "why not" for excluded counties)
        |
        v
  ranked shortlist  ->  Streamlit UI / CLI / CSV export
```

Six pillars from the brief: energy and carbon, water, climate resilience,
grid and infrastructure, land, community and economics. Two horizons: today
and 2050.

Specs:

- `docs/schema.md`: the county feature table, one row per county, the
  contract between ETL, engine, and opposition layer.
- `docs/conditions.md`: the conditions file format and what each field does.
- `engine/pillars.yaml`: which columns score which pillar, and in which
  direction.
- `engine/conditions/`: three presets, balanced, speed_to_power,
  sustainability_first.

## Where ML fits, and where it doesn't

The ranking is not ML. There's no ground truth for "optimal location," and a
learned ranker would reproduce where the industry already built, which is
the problem the brief asks us to fix. The engine is transparent
multi-criteria analysis that a judge can read line by line. The technology
story is the robustness analysis, the portfolio optimizer, and the
explainability, not a model.

ML is used in one place with a real target: the opposition risk model. A
gradient-boosted or logistic model predicts pushback or cancellation from
county features (farmland share, existing facility density, rurality, water
stress, moratoria), trained on FracTracker outcomes, validated
leave-one-state-out. Its output is one column in the feature table,
`opposition_risk`, weighted like everything else.

News sentiment from GDELT is a data source, not a model. It would add one or
two columns (local coverage volume and tone) and it carries a coverage bias.
It's cut from the hackathon build. The pipeline for it is documented in
`research/gdelt_feasibility.md` if there's time after the demo works.

An LLM may write the site brief and the plain-language explanation for the
top counties. It explains the decision. It doesn't make it.

## Why this framing

Real projects fail, in rough order, because power can't be delivered on
time, a rezoning is denied after local opposition, water, no tenant, or
electricity-bill politics. Data Center Watch counted 48 projects worth $156B
blocked or delayed in 2025, then 75 worth $130B in Q1 2026 alone. The brief
lists sustainability factors. The engine scores both sustainable and
buildable, and the user's weights decide the balance. Our defaults only need
to be defensible.

## What the research found

Full detail in `research/data_inventory.md`. The findings that changed the
plan:

- **Labels exist for free.** FracTracker Alliance publishes a public ArcGIS
  tracker: 1,701 US facilities with county, status, megawatts, and a
  community-pushback flag, plus 680 moratoria keyed by census GEOID. It's
  the training data for the opposition model and a feature in its own
  right (existing facility density).
- **FEMA's National Risk Index replaces four pulls.** One county table
  covers flood, wildfire, hurricane, drought, heat, tornado, winter. It's
  v1.20 and renamed riverine flooding to inland flooding.
- **CMRA replaces both the NOAA Normals and the 34 TB CMIP6 archive.** One
  feature service gives heating and cooling degree days and days above 95F
  for today and mid-century, per county. It's CMIP5 LOCA, and we say so.
- **eGRID has no water fields.** Grid water intensity needs EIA-923 Schedule
  8D. Stretch.
- **Hosts moved.** NREL is nlr.gov. LBNL's 2026 queue file has a FIPS
  column. FCC's site needs a login; an Esri county fiber layer doesn't.

Seed labels: `data/processed/opposition_seed_labels.csv`, 246 projects. Any
value ending in `?` was inferred, not checked. The approved class is noisy
and there are no true negatives. See `research/opposition_labels.md`.

## The 20-hour plan

Hackathon ends Sunday morning. Three people. The build uses only sources
that join on FIPS or county name with no spatial work.

| Hours | Person A: data | Person B: engine and UI | Person C: opposition, deck |
| --- | --- | --- | --- |
| 0-2 | agree on `docs/schema.md`, start adapters | engine skeleton against a fake table with random values; UI shell | deck outline, opposition features from FracTracker |
| 2-8 | ship the core table: Census, NRI, CMRA, Queued Up, Drought Monitor, FracTracker, Esri FCC, eGRID state sheet | gates, percentiles, pillars, composite, floor rule; CLI | opposition risk model, write `opposition_risk` column; baseline numbers vs Loudoun |
| 8-12 | fill nulls, manifest, name-join fixes | robustness, explanation, presets switch; first real run | check who wins; does the engine see Columbia Basin saturation? |
| 12-16 | stretch: NREL wind raster | portfolio mode, county detail panel | pick the featured site, carbon and water impact, risk assessment |
| 16-19 | freeze data | freeze code; LLM site briefs for top 10 if time | deck, demo script |
| 19-20 | rehearse twice | rehearse twice | rehearse twice |

Rule: Person A ships whatever is done at hour 8 with missing columns null.
The engine already handles missing columns. B and C never block on A.

Cut: NREL solar, NLCD, Aqueduct overlay, EIA water, GDELT, news
classification, PAD-US. Stretch, in order: NREL wind, portfolio mode, LLM
site briefs.

Rubric reminder: Execution and Presentation are 40 percent. A broken demo
costs more than a missing feature.

## Final deliverable

1. **Live demo.** Streamlit app: pick a preset or edit conditions, see the
   choropleth, the top-10 table with pillar breakdown and robustness, click
   a county for its explanation and 2050 shift, toggle portfolio mode. One
   static data file. No live calls.
2. **Deck**, about twelve slides mapped to the brief's six deliverables: the
   shortlist under default conditions with one site developed in depth, the
   framework and weights, data and assumptions, carbon and water impact vs a
   Loudoun baseline for a 300 MW facility, risk assessment, 20-to-30-year
   implementation vision, and the opposition layer as "think beyond the
   building."
3. **The repo**: ETL adapters, the county table and manifest, the engine as
   a package with a CLI, and the research docs.

## Repo layout

```
docs/          schema.md, conditions.md
engine/        pillars.yaml, conditions/ presets; engine code goes here
etl/           adapters that build the county table; FracTracker and GDELT scripts
research/      data inventory, GDELT feasibility, opposition label notes
data/raw/      gitignored downloads
data/processed/ county_features.parquet, manifest, seed labels
app/           Streamlit UI
CLAUDE.md      conventions for Claude Code sessions
```

## Getting started

```bash
pip install pandas geopandas pyarrow pyyaml requests streamlit plotly
python etl/fetch_fractracker.py        # pulls FracTracker layers to data/raw/fractracker/
python etl/build_seed_labels.py        # rebuilds data/processed/opposition_seed_labels.csv
```

## One prediction to test

A naive weighting lands on the Columbia River basin: cheap hydro, cold
climate. That region is saturated with multi-year interconnection waits. If
the queue and opposition columns push the shortlist somewhere less obvious,
that's the headline. Don't force it. Check whether the engine can see it.

## Credits

FracTracker Alliance data is free for non-commercial use with credit. Put
the credit on the data slide.
