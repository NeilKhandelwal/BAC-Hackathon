# Build plan

Deadline: Sunday morning, about 20 working hours. Hours are counted from
the start of the build (H0).

## Workstreams

The work splits into three streams that can run in parallel.

| Stream | Produces | Hand-off |
| --- | --- | --- |
| Data | ETL adapters, county table, manifest | `data/processed/county_features.parquet` |
| Engine and UI | engine package, CLI, Streamlit app | `engine/`, `app/` |
| Permitting and deliverables | permitting model, lookup tables, impact numbers, deck | permitting columns, `research/permitting_model.md`, slides |

## Rules

1. `docs/schema.md` is the contract. Change it before changing code that
   depends on it.
2. No stream waits on another. The engine builds against a fake table. The
   permitting model builds against FracTracker and Census directly.
3. At H8, the data stream ships whatever exists. Missing columns are null.
   The engine drops missing columns with a warning.
4. No live API calls in the demo. The app reads one static file.
5. Data freezes at H16. Code freezes at H18.
6. Commit to a branch and open a PR. Merge to `main` only when it runs.

## Phase 1: setup (H0 to H2)

| Step | Done when |
| --- | --- |
| Read `docs/schema.md`, `docs/conditions.md`, `docs/permitting.md`. Agree or change them. | no open questions on core columns |
| Create a Python 3.11 venv and run `pip install -r requirements.txt`. | install works on every machine |
| Write `etl/fips.py` with `normalize_county(name, state)` and a test against the TIGER name list. | test passes |
| Write `etl/fake_features.py` that emits a table with every core column and random values. | engine and app can load it |
| Outline the deck: one slide per brief deliverable. | outline committed |

## Phase 2: core data, engine, permitting model (H2 to H8)

**Data.** One adapter per source in `etl/adapters/`, each returning a
DataFrame keyed by `fips`. `etl/build_features.py` joins them and writes the
parquet and manifest. Order:

1. Census TIGER boundaries and ACS population and income
2. FEMA NRI via ArcGIS service
3. CMRA climate projections via ArcGIS service
4. LBNL Queued Up 2026
5. FracTracker facilities and moratoria
6. Esri FCC county fiber layer
7. US Drought Monitor, one call per state
8. eGRID 2023 state sheet

URLs and field names are in `research/data_inventory.md`.

Done when: the parquet has about 3,110 rows, every core column exists, and
the manifest lists sources and missing columns.

**Engine.** In `engine/`:

1. Load features, conditions, and `pillars.yaml`.
2. Apply gates. Record a gate log per county.
3. Percentile-rank each column, direction-adjusted. Apply horizon swaps.
4. Average to pillar scores. Weighted composite. Floor rule.
5. CLI: `python -m engine rank` and `python -m engine explain`.
6. Unit tests for gates, floor rule, and missing columns, on the fake table.

Done when: `rank` runs on the fake table for all three presets and tests
pass.

**Permitting model.** Steps 1 to 4 of `docs/permitting.md`.

Done when: labels file exists, model is fit, AUC and named-case ranks are
recorded.

## Phase 3: integration (H8 to H12)

| Step | Done when |
| --- | --- |
| Run all three presets on the real county table. | three result CSVs in `results/` |
| Add robustness (Dirichlet resampling) and explanation output. | each result row has `robustness` and `top_reasons` |
| Join the permitting columns into the county table. | columns non-null for labeled and unlabeled counties |
| Build the three permitting lookup tables (step 5 of `docs/permitting.md`). | CSVs committed with source URLs |
| Fix name-join failures from the FIPS log. | unmatched count under 2 percent |
| Review results for the three presets. Note any county that looks wrong and trace why. | written list of anomalies and causes |

## Phase 4: app and analysis (H12 to H16)

| Step | Done when |
| --- | --- |
| Streamlit app: preset picker, weight sliders, gate toggles, choropleth, top-10 table, county detail panel with pillar bars, gate log, permitting card, 2026 vs 2050 toggle. | app runs from a clean clone |
| Pick the featured county from the balanced preset's top 3 by robustness. | one county chosen, reason written down |
| Impact numbers for a 300 MW facility in the featured county vs Loudoun County, VA: annual CO2 from grid intensity, annual cooling water from cooling degree days and cooling type. Write assumptions in `research/impact.md`. | two numbers per site with formulas shown |
| Risk assessment for the featured county: top hazards, permitting drivers, mitigation. | one table |
| Stretch, only if everything above is done: NREL 100 m wind raster. | column added, manifest updated |

## Phase 5: freeze and deliver (H16 to H20)

| Step | Done when |
| --- | --- |
| Data freeze. Commit final parquet and manifest. | tagged commit |
| Stretch, only if the app is stable: portfolio mode. | toggle works for 3 sites |
| Code freeze at H18. | tagged commit |
| Finish the deck. | all slides filled |
| Write the demo script: preset, change one condition, show the shortlist move, open the featured county. Five minutes. | script committed |
| Rehearse twice with a timer. Fix only demo-breaking bugs. | two clean runs |

## Deliverables

1. **App.** Streamlit, reads the frozen parquet, no network calls.
2. **Deck.** One slide per brief deliverable: recommended location (shortlist plus featured county), decision framework and weights, data and assumptions, sustainability impact, risk assessment, 20-to-30-year implementation. Plus one slide on permitting risk and one on limitations.
3. **Repo.** ETL, engine, app, specs, and research docs on `main`.

## Cut list

Not in this build: NREL solar raster, NLCD, Aqueduct overlay, EIA water
intensity, GDELT news, LLM site briefs, PAD-US.

Add back in this order if ahead of schedule: NREL wind, portfolio mode,
eGRID subregion join, LLM site briefs for the top 10.

## Risks

| Risk | Sign | Response |
| --- | --- | --- |
| County table is late | H8 with fewer than five sources joined | ship what exists; engine and permitting continue on partial data |
| Name joins drop rows | unmatched FIPS log above 5 percent | fall back to lat/lon spatial join for FracTracker |
| Permitting model is weak | AUC below 0.60 | use the equal-weighted index per `docs/permitting.md` |
| Results look wrong | a known-bad county ranks top 10 | trace the pillar breakdown before changing weights |
| Demo breaks | any error in rehearsal | revert to the last tagged commit |
