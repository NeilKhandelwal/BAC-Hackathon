# BAC Hackathon: sustainable AI data center site selection

## Project

Multi-criteria site-suitability framework that scores every county in the
contiguous US as a location for a next-generation sustainable AI data center.
Deliverables are a slide deck and a live demo. The rubric weights Technology,
Presentation, Innovation, Execution, and Theme equally.

Working design decisions so far:

- Spatial unit is the county (FIPS). Everything aggregates to one county table.
- Hard gates first (floodplain, protected land, no fiber), weighted scores second.
- Weights are user-adjustable in the demo. Report robustness across weight
  samples, not a single winner.
- Score two horizons: present day and 2050.
- Differentiator is a community-opposition risk layer built from local news
  (GDELT) and Data Center Watch outcomes.
- The demo must not depend on live API calls. Precompute to static files.

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

- The cloud sandbox network policy allows package registries and GitHub only.
  Dataset hosts (gdeltproject.org, epa.gov, census.gov, nrel.gov) are blocked
  from this sandbox. Verify dataset access on a teammate's laptop, not here.
- Repo layout (planned):
  - `research/` notes, data inventory, findings
  - `etl/` scripts that build the county table
  - `data/raw/` (gitignored) and `data/processed/` (small outputs only)
  - `app/` demo UI
