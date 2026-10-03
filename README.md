# Where should America's next sustainable AI data center be built?

A county-level decision framework that scores every county in the contiguous
US as a site for a next-generation AI data center, and shows which locations
hold up under different priorities.

This README is the onboarding doc. It covers the idea, what the research
found, what's in the repo, and what we build next. Deeper detail is in
`research/`.

## The idea in one paragraph

Site selection is a multi-criteria problem, not a prediction problem. Every
team will build a weighted scorecard. We win on three things the brief hints
at but most teams will skip: hard gates before scores, so a county with great
wind and a floodplain doesn't win; robustness instead of a single answer, so
we report the counties that stay on top across many reasonable weightings;
and a community-opposition risk layer, because local pushback is now the
second most common reason real projects die and none of the brief's 30
datasets capture it.

## Why this framing

The brief lists sustainability factors. Reality weights power and
permitting. Real projects fail, in rough order of frequency, because:

1. The utility can't deliver power on the developer's timeline. Interconnection
   waits of three to seven years are normal.
2. A rezoning is denied or voided after local opposition.
3. Water, especially in the Southwest.
4. The project was speculative and never had a tenant.
5. Residential electricity bills rose and politics turned.

Data Center Watch counted 48 projects worth $156B blocked or delayed in 2025,
then 75 projects worth $130B in Q1 2026 alone. Opposition groups went from
about 140 in early 2025 to 833 across 49 states by March 2026.

So the framework has to answer two questions, not one: where is sustainable,
and where is buildable. If those point to the same place, that's the
recommendation. If they don't, the tension is the headline of the deck.

## The framework

```
county table (about 3,100 rows, one column per metric)
  -> hard gates: floodplain, protected land, no fiber, extreme wildfire
  -> normalized scores per pillar
  -> user-adjustable weights (sliders in the demo)
  -> Monte Carlo over the weight space: how often is each county top 10?
  -> two horizons: today and 2050
  -> opposition risk overlay
```

Pillars match the brief: energy and carbon, water, climate resilience, grid
and infrastructure, land, community and economics. Heat reuse is scored as a
heat-sink proxy: heating degree days times nearby population or industrial
land.

The 2050 horizon uses county-level climate projections (cooling degree days,
days above 95F), Aqueduct's 2050 water stress, and the interconnection queue
as a decarbonization signal.

## The differentiator: opposition risk

Two pieces, each doing one job.

- **Structural risk model.** A small, interpretable model (logistic
  regression or gradient boosting) on county features: farmland share,
  existing data center density, rurality, water stress, active or pending
  moratoria, state bill activity. Trained against real outcomes.
- **Reason profile from local news.** GDELT's Global Knowledge Graph tags US
  city mentions with a county code, so we can measure local news volume and
  tone about data centers per county. An LLM or embedding classifier sorts
  articles into opposition type: water, noise, bills, farmland, secrecy, tax.
  Water objections and noise objections need different mitigations.

The honest limits: a county with no coverage is "no data," not "no
opposition." Score those with a state-level prior and show a confidence
band. Fine-tuning BERT on 150 labels overfits; use embeddings and a
structural model instead. See `research/opposition_labels.md`.

## What the research found

Full detail in `research/data_inventory.md`. The findings that change the
plan:

- **Labels exist for free.** FracTracker Alliance publishes a public ArcGIS
  tracker: 1,701 US facilities with county, status, megawatts, cooling type,
  and a community-pushback flag, plus 680 moratoria and zoning restrictions
  keyed by census GEOID. Data Center Watch sells the same thing. FracTracker
  also gives us existing facility density per county, a strong structural
  predictor on its own.
- **FEMA's National Risk Index replaces four pulls.** One county CSV covers
  flood, wildfire, hurricane, drought, heat wave, tornado, and winter
  weather. It's v1.20, moved into FEMA's RAPT tool, and renamed riverine
  flooding to inland flooding.
- **eGRID has no water fields.** Grid water intensity comes from EIA-923
  Schedule 8D joined through EIA-860 plant locations. The brief explicitly
  asks for water used in grid generation.
- **Don't download NEX-GDDP-CMIP6.** It's 34 TB. The CMRA feature service
  gives 2050 cooling degree days per county directly. It's CMIP5 LOCA, not
  CMIP6, and we say so.
- **GDELT resolves to county** through the GKG, not the search API. The
  pipeline is BigQuery (free sandbox tier, no credit card) for geolocation
  and tone. The search API rate-limits per IP and returns no locations.
- **Several hosts moved.** NREL is now nlr.gov. LBNL's 2026 queue file has a
  FIPS column. FCC's broadband site needs a login, but Esri publishes a
  county fiber layer without one.

## Seed labels

`data/processed/opposition_seed_labels.csv` has 246 projects with status
(approved 83, cancelled 69, delayed 59, withdrawn 26, moratorium 8), county,
and keyword-coded reasons. Any value ending in `?` was inferred by regex,
not checked by a person. Known problems: the approved class is noisy, there
are no true negatives, dates are sparse, and coverage skews to Texas,
Virginia, Pennsylvania, Indiana, and Ohio. The cheapest fix is two hours
hand-verifying the 63 approved-with-pushback rows.

## Repo layout

```
research/
  data_inventory.md       18 datasets: URLs, formats, sizes, county mapping, gotchas
  gdelt_feasibility.md    how to get county-level news tone, and what doesn't work
  opposition_labels.md    label sources, status mapping, biases
etl/
  fetch_fractracker.py    pulls FracTracker's three ArcGIS layers to data/raw/
  build_seed_labels.py    builds the seed label CSV
  gdelt_gkg_county.sql    BigQuery: GKG locations -> FIPS with tone per quarter
  gdelt_probe.py          collects data center article URLs from the GDELT DOC API
data/
  raw/                    gitignored; downloaded datasets go here
  processed/              small derived tables we commit
CLAUDE.md                 design decisions and conventions for Claude Code sessions
```

## Proposed build

Stack: Python with pandas and geopandas for ETL into one county-level
parquet file. Lightweight map UI on top, with weight sliders and a county
detail panel. The demo loads a static file and makes no live API calls, so
it can't fail on conference wifi.

Split for three people:

| Person | Owns | Done when |
| --- | --- | --- |
| A | County table ETL. TIGER, NRI, eGRID, Queued Up, Drought Monitor, FracTracker, CMRA first, then the spatial layers. | One parquet with one row per county and every metric. Frozen by the halfway point. |
| B | Scoring engine and UI. Gates, normalization, sliders, Monte Carlo, two horizons, map. | Demo runs end to end on a mock table by day one, on the real table when A delivers. |
| C | Opposition layer, deck, demo script. GDELT via BigQuery, label verification, structural model, reason classifier. | A per-county risk score and reason profile that drops into B's table as columns. |

Rubric reminder: Execution and Presentation are 40 percent of the score. A
broken demo costs more than a missing feature. Build the core pipeline
first, add the opposition layer second, rehearse third.

## One prediction to test

A naive weighting lands on the Columbia River basin: cheap hydro, cold
climate. That region is saturated with multi-year interconnection waits. If
our queue and opposition layers push the answer somewhere less obvious,
such as northern New England near Quebec hydro, the upper Midwest, or the
northern Plains, that's a more interesting result. Don't force it. Check
whether the framework can see the saturation.

## Getting started

```bash
pip install pandas geopandas requests
python etl/fetch_fractracker.py        # pulls FracTracker layers to data/raw/fractracker/
python etl/build_seed_labels.py        # rebuilds data/processed/opposition_seed_labels.csv
```

GDELT needs a Google Cloud project with the free BigQuery sandbox. Run
`etl/gdelt_gkg_county.sql` there. The DOC API collector in
`etl/gdelt_probe.py` must run from a laptop, not the cloud sandbox.

Registrations to start on day one: IPUMS NHGIS (optional NLCD county
summaries) and Global Energy Monitor (steel and cement, low priority). FCC
is not needed if you use the Esri layer.

## Credits

FracTracker Alliance data is free for non-commercial use with credit. Put
the credit on the data slide.
