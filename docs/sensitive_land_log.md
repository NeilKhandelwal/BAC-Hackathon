# Sensitive and protected land: logbook

This logbook tracks the work to check, and then score, proximity to
protected and sensitive land. It's written so that a new session with no
memory can resume from it alone. Read CURRENT STATE first. The history at
the bottom is append-only.

## CURRENT STATE

Overwritten after every step.

- **Updated:** 2026-10-04 05:30 UTC
- **Branch:** `fix/sensitive-land`, from `main` at `714d231` (PR #35,
  the weighting work, is merged).
- **Phase and step:** Phase 2 in progress (Phase 1 research running in
  parallel).
- **Done:** Phase 0. Census county and AIANNH boundaries downloaded to
  `data/raw/tiger/`. `etl/adapters/tribal_lands.py` written and tested
  (Grant 0%, Clark 0.04%, Franklin NY 1.2%). `etl/append_columns.py`
  written: it appends adapter columns to the frozen table and rebuilds the
  manifest and quality report.
- **In progress:** two Opus research subagents. One is checking protected,
  tribal, and cultural-resource land near Grant WA, Clark WA, and Franklin
  NY. The other is checking PAD-US and Census AIANNH download access. If a
  new session starts and their results are lost, rerun that research.
- **Exact next action:** get the PAD-US download (waiting on the
  dataset-access subagent), write `etl/adapters/pad_us.py`, and compute
  `pct_protected` (GAP 1-2) and `pct_protected_gap1to3` (context).
- **Decisions so far:**
  1. The frozen county table is updated by appending the new columns and
     leaving every existing column untouched. That follows the documented
     frozen-artifact policy and the queue-semantics precedent (`01fa98b`).
     A full rebuild would need every raw source and would shift small
     documented values elsewhere.
  2. `tribal_land_share` counts federally recognized reservations and
     off-reservation trust land (TIGER 2024 AIANNH classes D2, D3, D5,
     D8). It excludes state reservations (D4), the statistical areas (D0,
     D6, D9, E1; Oklahoma tribal statistical areas would cover most of
     eastern Oklahoma), and Hawaiian home lands (F1). It's area inside
     legal boundaries, not tribal ownership. Context only, not scored.
  3. Shares use the cartographic county polygon area in EPSG:5070 as the
     denominator, as the other spatial adapters do.
  4. New columns go into `etl/schema.py` STRETCH and get registered in
     `etl/build_features.py` only together with the table patch (Phase 3).
     `tests/test_county_table.py` requires the frozen manifest's missing
     list to match STRETCH, so splitting them would break the test.
- **Recreate:** Python env with `python -m venv .venv` and
  `pip install -r requirements.txt`. Raw downloads go in `data/raw/`
  (gitignored).
- **Tooling:** `gh` is at `C:\Program Files\GitHub CLI\gh.exe`. Commits
  pass `-c user.name="Valaya Choudhary" -c
  user.email=35052710+ValsTRM@users.noreply.github.com`. **No AI
  attribution:** no Co-Authored-By trailers, no "Generated with" footer.
- **Stop conditions:** deleting data, rewriting history, or pushing to
  `main`; needing credentials; failing tests that need an uncertain engine
  change; or finding something that undermines Grant WA as the featured
  pick (finish the phase, write it at the top, stop).

## History

### 2026-10-04 05:27 UTC, Phase 0: close out and set up

- The weighting log is closed and pushed on `feat/weighting-methods`
  (`dc98fcc`). PR #35 was already merged into `main` (`714d231`), so
  that close-out commit sits on the feature branch only.
- `main` at `714d23137f16626cf33f15f75e16b73d296395e3`.
- Branch `fix/sensitive-land` created from it.
- The land pillar in `engine/pillars.yaml` already lists `pct_protected`
  (lower is better). `docs/schema.md` lists it as a stretch column from
  PAD-US GAP 1-2. The column was never built, so the engine skips it.
  `research/data_inventory.md` has no PAD-US or AIANNH notes.

### 2026-10-04 05:30 UTC, Phase 2 started: tribal land share

- Downloaded `cb_2024_us_county_500k.zip` and `tl_2024_us_aiannh.zip`
  (Census) to `data/raw/tiger/`.
- `etl/adapters/tribal_lands.py`: 451 of 3,109 counties have some tribal
  land and 55 have more than 25%. Spot checks: Grant WA 0.0%, Clark WA
  0.04% (Cowlitz reservation near La Center), Franklin NY 1.2% (St. Regis
  Mohawk), Okanogan WA 19.8% (Colville), Yakima WA 45.0% (Yakama Nation),
  Big Horn MT 70.6%, Apache AZ 68.3%, Osage OK about 100%. All are
  plausible against the known reservation geography.
- `etl/append_columns.py` added for the Phase 3 table update.
