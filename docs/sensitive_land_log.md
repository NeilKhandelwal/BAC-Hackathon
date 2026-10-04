# Sensitive and protected land: logbook

This logbook tracks the work to check, and then score, proximity to
protected and sensitive land. It's written so that a new session with no
memory can resume from it alone. Read CURRENT STATE first. The history at
the bottom is append-only.

## CURRENT STATE

Overwritten after every step.

- **Updated:** 2026-10-04 05:27 UTC
- **Branch:** `fix/sensitive-land`, from `main` at `714d231` (PR #35,
  the weighting work, is merged).
- **Phase and step:** Phase 0 done. Phases 1 and 2 starting in parallel.
- **Done:** weighting log closed out; branch created; this log started.
- **In progress:** two Opus research subagents. One is checking protected,
  tribal, and cultural-resource land near Grant WA, Clark WA, and Franklin
  NY. The other is checking PAD-US and Census AIANNH download access. If a
  new session starts and their results are lost, rerun that research.
- **Exact next action:** download Census county and AIANNH boundaries, then
  PAD-US, and write `etl/adapters/pad_us.py`.
- **Decisions so far:**
  1. The frozen county table is updated by appending the new columns and
     leaving every existing column untouched. That follows the documented
     frozen-artifact policy and the queue-semantics precedent (`01fa98b`).
     A full rebuild would need every raw source and would shift small
     documented values elsewhere.
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
