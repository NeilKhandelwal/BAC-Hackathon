# Deck build log

Build log for the editable pitch template in `docs/deck/`. The CURRENT
STATE block is overwritten at every step. History is append-only.

## CURRENT STATE

- **Updated:** 2026-10-04, step 1 (story decided).
- **Branch:** `deck/template`, created from `main` at
  `23bb71cb622fae2d82ba0cfe415b909888b422aa`.
- **Pull request:** none yet. `gh` is installed but not logged in, so the
  PR step waits for the end.
- **Phase:** story structure decided with the advisor. Quote and photo
  research is running in a subagent. Next: write `docs/deck/build_deck.py`.
- **Rendering:** LibreOffice 26 and PyMuPDF are installed, so PNG previews
  are possible.
- **Placeholders left:** not started.
- **Numbers to check:** not started.
- **Sensitive-land check:** `origin/fix/sensitive-land` at `d2ed911` has
  both rows in `research/risk.md`. Slide 7 uses them.

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

### 2026-10-04, step 1: advisor review and story decision

**Checks run before the advisor answered** (scratchpad only; nothing in
`results/` or the county table changed):

- Top 10, counts, and robustness in `docs/figures/facts.json` match
  `results/balanced.csv` on main `23bb71c`.
- Cooling switch (balanced with `cooling: evaporative`): 826 counties pass
  the gates, 542 pass the floor, Grant is excluded, and Wayne TN is first.
  This matches `docs/demo_script.md`.
- **Stale number:** `docs/weighting.md` says Franklin NY's and Grant's
  energy_carbon pillars sit at the 97th and 94th national percentiles.
  On current main they sit at the 98.7th and 93.6th (pillar scores 80.4
  and 70.4). The 97th predates the queue-semantics merge. The deck uses
  current values.
- **Dollar model:** with sales tax, the Monte Carlo puts Chesterfield SC
  first in 21.8% of draws, and Grant, Clark, and Franklin are first in
  under 1%. "A dollar model ranks the finalists" would overclaim.
- **Price sensitivity:** with every Washington county at BPA's new-load
  rate and every other state at its average, Grant ranks 79th at
  $80/MWh and 1,146th at $132/MWh. The comparison is lopsided, because no
  other state's new-load rate is sourced, but Grant's #1 rests on today's
  average price.

**Advisor (Opus subagent), summary of the ruling:**

- Drop "a dollar model ranks the finalists." Say the dollar model prices
  the leaders and states what must be true. Grant is 78th of the
  162-county shortlist with tax.
- Cut slide 4 ("why dollars") to the appendix. It casts Grant as dirty
  using the regional average that the impact slide calls an overstatement,
  and the app shows pillar scores 80.4 and 70.4, not 97 and 94.
- Lead robustness with SMAA: top 10 in 50.5% of all weightings, more than
  any county. Show 99.9% only as "near our weights (about ±0.03)". Say no
  county wins most weightings. Drop both Monte Carlo winner charts from
  the main deck.
- New order: hook, answer, framework, impact, how the pick changed,
  robustness, risk and win condition, 30-year plan, engine.
- Compare Grant dry (28M gal) with Grant evaporative (210M gal), not
  only with Loudoun. Say 236k t is BPA's mix before funded supply.
- Say "1 GW of solar for annual matching," not hourly.
- Never say "strongest site." Say "leads 1,565 counties."
- Found mismatches in other docs (not fixed here; out of scope):
  community weight 10% (demo script) vs 8.5% (preset); Franklin 986th
  (demo script) vs 952nd (weighting.md); Whitman 63.0 (risk.md) vs 63.1
  (facts.json); the demo script calls 2,000 small weight perturbations
  "random weight draws."

**Decisions:**

1. Adopt the advisor's order. Main slides: 1 hook, 2 answer, 3 framework,
   4 impact, 5 how the pick changed, 6 robustness, 7 risk and win
   condition, 8 the 30-year plan, 9 the engine and demo hand-off. This
   splits the brief's slide 8 into 7 and 8 and moves "why dollars" out.
2. Keep the brief's robustness line: "We didn't tune the weights to get
   our answer. We tested whether our answer depends on them." It's
   accurate for SMAA.
3. Slide 2 says Grant leads "at today's average power prices." The BPA
   rerun goes in slide 7's notes and the numbers-to-check list.
4. Appendix, six slides: A1 why tonnes, not percentiles (the cut slide 4,
   with the BPA footnote); A2 the three-county tie and win conditions,
   with the tax-flag caveat and the Monte Carlo result; A3 weights by
   method; A4 data sources by pillar; A5 limitations; A6 the engine
   extends (global run and Stage 2 reuse on one slide). Merging global
   and Stage 2 keeps the appendix at six.
5. Slide 7 uses the sensitive-land and tribal rows from
   `origin/fix/sensitive-land` (`d2ed911`, `research/risk.md`), cited as
   unmerged.
