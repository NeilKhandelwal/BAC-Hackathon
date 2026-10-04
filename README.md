# Data center location decision engine

A tool that ranks US counties as sites for a sustainable AI data center,
given a user's conditions. It returns a ranked, explained shortlist and can
be rerun with new conditions, new data, or a new region.

## Current result

The balanced preset scores all 3,109 counties in the contiguous US for a
300 MW campus. 1,565 counties pass the hard gates and 883 pass the pillar
floor. Grant, WA (63.70) and Whitman, WA (63.69) are level at the top, which
is a tie. Benton, WA (62.69), Mayes, OK (62.03), and Payne, OK (61.97) follow.

The deck features Grant County, WA. The case for it, and its limits, are in
`research/impact.md`, `research/risk.md`, and `research/implementation.md`.
Full results for every preset are in `results/`.

## User

A site-selection lead at a data center developer or hyperscaler. Input is a
conditions file: facility size, online year, cooling type, carbon limit,
hazard tolerance, and weights. Output is a shortlist with the reasons for
each rank and each exclusion.

## How it works

1. **Data.** ETL adapters build one table with a row per county and a
   column per metric. See `docs/schema.md`.
2. **Gates.** Counties that fail a hard condition, such as a flood
   percentile or an active moratorium, are excluded and logged.
3. **Scores.** Each metric becomes a national percentile. Metrics average
   into eight pillars: energy and carbon, water, climate resilience, grid
   and infrastructure, land, community, permitting, cost. See `engine/pillars.yaml`.
4. **Composite.** Weighted sum of pillars. A county below the 10th
   percentile on any pillar (in the balanced preset) ranks below every
   county that isn't.
5. **Robustness.** Weights are resampled 2,000 times. Each county gets the
   share of samples where it ranked top 10.
6. **Output.** Ranked list with pillar breakdown, robustness, permitting
   pathway, and gate log. CLI, CSV, a React cockpit, and a Streamlit app.

Conditions format and presets: `docs/conditions.md`, `engine/conditions/`.
Why the weights are what they are, and how the ranking holds up under other
weighting methods: `docs/weighting.md`.

## Run the demo

Neither app needs a network connection once its dependencies are installed.
Both read committed data.

### Cockpit

The cockpit in `app/cockpit/` is the recorded and judged demo. It's a static
React app that recomputes gates, scores, and ranks in the browser when you
change a weight, gate, preset, cooling type, or horizon. It needs Node
20.19 or later, or 22.12 or later. It doesn't need Python.

```bash
cd app/cockpit
npm install
npm run dev        # http://localhost:5173
```

The page shows a **Real engine data** badge when it loads the committed
export. The URL carries the scenario, so a link such as
`http://localhost:5173/?preset=balanced&h=2050` opens the same view every
time. **Reset demo** returns to the starting state.

To serve the built files instead, as you would on demo day:

```bash
npm run build
npm run preview    # http://localhost:4173
```

Port 5173 and port 4173 are fixed. If one is in use, the command exits
instead of picking another port.

After the county table or a preset changes, refresh the cockpit's data and
check it against the Python engine:

```bash
npm run data       # needs the Python environment at .venv in the repo root
npm test           # includes the parity test against results/*.csv
```

`npm run e2e` runs the browser tests. Run `npx playwright install chromium`
and `npm run data:fixture` once first.

### Streamlit app

The Streamlit app is the team's working tool and the fallback demo. Run
these from the repo root:

```bash
pip install -r requirements.txt
streamlit run app/app.py    # http://localhost:8501
```

After a county's ranking detail, the app shows **Industrial reuse and
community transition**. This unscored, post-ranking screening covers
economic transition, industrial reuse, infrastructure context, and EPA
brownfield properties, and offers a downloadable screening brief. The
property table needs `data/processed/brownfield_sites.parquet`, which the
ETL generates and git ignores. Without it, the app explains that and still
shows county totals from the committed table. See `docs/industrial_reuse.md`
and the click path in `docs/demo_script.md`.

## Run the engine

```bash
python -m engine rank --conditions engine/conditions/balanced.yaml \
  --features data/processed/county_features.parquet \
  --out results/balanced.csv
python -m engine explain --conditions engine/conditions/balanced.yaml --fips 53025
```

`rank` writes the ranked list, the excluded list with the gate each county
failed, and a report. `explain` prints one county's gates, pillar scores,
and the metrics behind them. Add `--json` for machine-readable output.

Run the tests with `python -m pytest -q`. Skipped tests print their reason.

## Beyond the US

The same engine ranks 196 countries from a country table and its own
pillar and conditions files. It's a proof that the method ports to a new
region, not a recommendation. See `docs/global.md`.

## Where ML is used

Nowhere in the shipped ranking. A model that predicts whether a project in
a county meets opposition was trained on FracTracker outcomes and validated
leave-one-state-out. It failed: its skill came from features that encode
how the labels are built. The permitting pillar uses three sourced columns
instead, and every score is transparent. Findings:
`research/permitting_model.md`. Method: `docs/permitting.md`.

## Repo

```
PRODUCT.md        what the product is, who it's for, and what it claims
DESIGN.md         visual system for the cockpit
docs/             schema, conditions, weighting, permitting, industrial reuse,
                  global version, deck outline and figures, demo script, plan
engine/           rank.py, explain.py, reuse.py, pillars.yaml, conditions/ presets
etl/              data adapters, table build, impact and risk calculations
research/         data inventory, findings, impact, risk, implementation plan
data/raw/         downloads (gitignored)
data/processed/   county table, country table, labels, lookup tables
results/          ranked and excluded lists and a report for each preset
app/app.py        Streamlit app
app/cockpit/      React cockpit
scratch/weighting/  code and outputs behind docs/weighting.md
tests/            engine, ETL, and Streamlit app tests
```

## Rebuild the data

You don't need this to run the demo. The county table is committed.

```bash
pip install -r requirements.txt
python etl/fetch_fractracker.py
python etl/build_seed_labels.py
python -m etl.build_features   # downloads to data/raw/, writes the county table and manifest
```

`build_features` caches every download. Pass `--no-fetch` to rebuild from
`data/raw/` without network calls. Delete a file under `data/raw/` to refetch it.

The build also writes `county_features_quality_report.json` (validation
checks and column profiles) and `brownfield_sites.parquet` (gitignored). The
BLS LAUS host refuses requests without a contact address, so set
`BLS_CONTACT_EMAIL=you@example.com` before the first online build. Cached
files need nothing.

The committed county table and `results/` are frozen hackathon artifacts.
A rebuild is semantically reproducible but not always byte-identical, and
it can swap tied counties outside the leading results. Reproduce exact
rankings from the committed table. See "Frozen artifacts and
reproducibility" in `docs/schema.md`.

## Plan

Build procedure, roles, phases, and cut list: `docs/plan.md`.

## Data notes

- Source URLs, formats, and county joins: `research/data_inventory.md`.
- FEMA NRI v1.20 renamed riverine flooding to inland flooding (`IFLD_*`).
- Climate projections come from CMRA and are CMIP5 LOCA, not CMIP6.
- Opposition labels: `research/opposition_labels.md`. Values ending in `?`
  are inferred, not verified.
- FracTracker Alliance data is free for non-commercial use with credit.
