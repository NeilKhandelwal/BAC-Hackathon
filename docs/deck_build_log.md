# Deck build log

Build log for the editable pitch template in `docs/deck/`. The CURRENT
STATE block is overwritten at every step. History is append-only.

## CURRENT STATE

- **Updated:** 2026-10-04, step 0 (setup).
- **Branch:** `deck/template`, created from `main` at
  `23bb71cb622fae2d82ba0cfe415b909888b422aa`.
- **Pull request:** none yet. `gh` is installed but not logged in, so the
  PR step waits for the end.
- **Phase:** setup done. Next: story review with the advisor, quote
  research, then the builder script.
- **Rendering:** LibreOffice is installing with Homebrew. If it fails,
  previews fall back to structural checks.
- **Placeholders left:** not started.
- **Numbers to check:** not started.

## Rules for this build

- Work only on `deck/template`. Never check out, commit to, or push
  `fix/sensitive-land`. Read it only with `git show`.
- Don't touch the county table, `results/`, or engine code.
- No AI attribution anywhere: commits, PR body, or the deck.
- Every quote must be verified at a primary or reputable source, or it
  becomes a `[[QUOTE NEEDED: topic]]` placeholder.
- Every number that could change tonight gets `[[CHECK]]` in the speaker
  notes and a row in `docs/deck/numbers_to_check.md`.
- Wording: "sited next to hydro, powered by new clean supply the project
  funds." Never "runs on hydro."

## History

### 2026-10-04, step 0: setup

- `git fetch origin`, `git checkout main`, `git pull`: main at `23bb71c`
  (merge of PR #39, cockpit UI).
- Created `deck/template` from that commit.
- `gh` wasn't installed. Installed it with Homebrew (2.102.0). `gh auth
  status` reports no login, so the PR step is deferred.
- LibreOffice wasn't installed. Started `brew install --cask libreoffice`.
- Created `.venv` (gitignored) and started installing `requirements.txt`
  plus `python-pptx`.
- Read the source material: `docs/deck.md`, `docs/weighting.md`,
  `docs/weighting_log.md`, `research/risk.md`,
  `research/implementation.md`, `research/impact.md`,
  `docs/demo_script.md`, `docs/figures/facts.json`, every PNG in
  `docs/figures/` and `docs/img/`, and `DESIGN.md`.
- Decision: the deck reuses the cockpit palette from `DESIGN.md` (light
  ground, ink text, navy and blue for rank stability, ember for 2050 and
  risk) so slides and the live demo look like one product.
- Decision: no "advisor" tool exists in this session. An Opus subagent acts
  as the advisor, and each consultation is logged here.
