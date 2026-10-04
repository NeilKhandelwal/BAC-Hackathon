# Data center location decision engine

A tool that ranks US counties as sites for a sustainable AI data center,
given a user's conditions. It returns a ranked, explained shortlist and can
be rerun with new conditions, new data, or a new region.

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
   pathway, and gate log. CLI, CSV, and a Streamlit app.

Conditions format and presets: `docs/conditions.md`, `engine/conditions/`.

## Where ML is used

Nowhere in the shipped ranking. A model that predicts whether a project in
a county meets opposition was trained on FracTracker outcomes and validated
leave-one-state-out. It failed: its skill came from features that encode
how the labels are built. The permitting pillar uses three sourced columns
instead, and every score is transparent. Findings:
`research/permitting_model.md`. Method: `docs/permitting.md`.

## Plan

Build procedure, roles, phases, and cut list: `docs/plan.md`.

## Repo

```
docs/             plan.md, schema.md, conditions.md, permitting.md
engine/           pillars.yaml, conditions/ presets, engine code
etl/              data adapters and scripts
research/         data inventory, source verification, label notes
data/raw/         downloads (gitignored)
data/processed/   county table, labels, lookup tables
app/              Streamlit UI
```

## Run

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

Engine and app commands are added as they're built.

## Data notes

- Source URLs, formats, and county joins: `research/data_inventory.md`.
- FEMA NRI v1.20 renamed riverine flooding to inland flooding (`IFLD_*`).
- Climate projections come from CMRA and are CMIP5 LOCA, not CMIP6.
- Opposition labels: `research/opposition_labels.md`. Values ending in `?`
  are inferred, not verified.
- FracTracker Alliance data is free for non-commercial use with credit.
