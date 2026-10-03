# BAC Hackathon: sustainable AI data center site selection

## Project

Multi-criteria site-suitability framework that scores every county in the
contiguous US as a location for a next-generation sustainable AI data center.
Deliverables are a slide deck and a live demo. The rubric weights Technology,
Presentation, Innovation, Execution, and Theme equally.

Working design decisions so far:

- The deliverable is a decision engine, not a single answer: conditions in,
  ranked and explained shortlist out, repeatable with new data or regions.
- Primary user is a site-selection lead at a developer or hyperscaler.
- Spatial unit is the county (FIPS). Everything aggregates to one county
  table. Schema is in `docs/schema.md`. Conditions format is in
  `docs/conditions.md`. Pillar mapping is in `engine/pillars.yaml`.
- Hard gates first, percentile scores per pillar, weighted composite with a
  pillar floor rule. Robustness by resampling weights. Portfolio mode for
  multiple sites.
- Two horizons: today and 2050, selected by the conditions file.
- The ranking is not ML. ML is used only for the opposition risk model
  (county features to pushback or cancellation, trained on FracTracker).
  News sentiment is a minor optional data source, cut from the hackathon
  build. An LLM may generate explanations but never decides.
- The demo must not depend on live API calls. Precompute to static files.
- Time box: hackathon ends Sunday morning. The 20-hour plan is in README.md.

## Working conventions for Claude

- Delegate research, data-gathering, and dataset-verification tasks to a
  subagent running on Opus (`model: "opus"` on the Agent tool). Keep the main
  session for synthesis, decisions, and code that touches the repo.
- Write temporary files to the scratchpad, not the repo. Only committed
  artifacts (code, data inventory, small lookup tables, docs) go in the repo.
- Do not commit raw downloaded datasets. Put them under `data/raw/` which is
  gitignored, and commit the scripts that fetch and transform them.
- Prose follows the Google developer documentation style guide: second person,
  present tense, active voice, short sentences, no em dashes.
- Be direct. Prefer honest assessment over encouragement.

## Environment notes

- The cloud sandbox network policy was opened on 2026-10-03. Most dataset
  hosts work. These still block the sandbox's shared IP: www.fema.gov,
  broadbandmap.fcc.gov, emp.lbl.gov, nrel.gov (use nlr.gov), web.archive.org.
  GDELT's search API rate-limits the shared IP, so test it from a laptop.
  Working alternatives for each are in research/data_inventory.md.
- Repo layout:
  - `docs/` schema and conditions specs
  - `engine/` pillar mapping, condition presets, engine code
  - `research/` notes, data inventory, findings
  - `etl/` scripts that build the county table
  - `data/raw/` (gitignored) and `data/processed/` (small outputs only)
  - `app/` demo UI
