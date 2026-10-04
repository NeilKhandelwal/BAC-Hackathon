# Deck build log

Build log for the editable pitch template in `docs/deck/`. The CURRENT
STATE block is overwritten at every step. History is append-only.

## CURRENT STATE

- **Updated:** 2026-10-04, step 2 (first full deck).
- **Branch:** `deck/template`, created from `main` at
  `23bb71cb622fae2d82ba0cfe415b909888b422aa`.
- **Pull request:** none yet. `gh` is installed but not logged in, so the
  PR step waits for the end.
- **Phase:** first full deck built, rendered, and inspected. Next: a
  structural check script, a final visual pass, and the advisor's review
  before finalizing.
- **Deck:** `docs/deck/pitch_template.pptx`, 9 main slides and 6 appendix
  slides. Rebuild with `.venv/bin/python docs/deck/build_deck.py`, render
  with `.venv/bin/python docs/deck/render_previews.py`.
- **Placeholders left:** none. Every quote on a slide is verified.
- **Numbers to check:** 67 rows in `docs/deck/numbers_to_check.md`.
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

### 2026-10-04, step 2: quotes, builder, first full deck

**Quote and photo research (Opus subagent).** Every quote was opened at
its primary source and matched word for word. Results:

- Used on slides: New York Executive Order 62, WHEREAS clause 9 (slide 1);
  Washington Data Center Workgroup Preliminary Report, Finding 19 (slide
  4); Grant PUD Data Center FAQs, Q6 (slide 7) and Q5 (slide 8).
- Verified and kept in the quote bank in `docs/deck/sources.md`: IEA
  Energy and AI, DOE press release, LBNL report sentences (the slide 1
  chart values), LBNL on cooling-tower water, WA Workgroup Findings 6 and
  18b, WA UTC media advisory, BPA new large single load fact sheet.
- Not used: the "at its water right limits" line. It's a Department of
  Ecology meeting summary of a City of Quincy staff member's remarks, not
  a City statement, and it blames food processing, not data centers.
- No verified source says siting matters "for decades". The slide 1
  headline is the team's claim, not a quote.
- New risk for Q&A: WA Workgroup Finding 19c says new load on hydropower
  competes with Tribal and state fisheries efforts. Added to slide 7
  notes.
- Photos: five public-domain or CC BY-SA images were verified (Wanapum
  Dam, Quincy aerial, NASA US at night, NREL liquid-cooled HPC, Priest
  Rapids spillway). None is on a slide, because every main slide already
  has a chart. They're listed in `sources.md` for a swap.

**Build decisions:**

- `docs/deck/build_deck.py` writes the deck, `numbers_to_check.md`, and
  `sources.md` in one run, reading `facts.json` and the committed SMAA
  output, so a rebuild after tonight's changes keeps all three in sync.
  Numbers from research write-ups are typed in next to their source file.
- Native charts on slides 1, 4, 5, 6, 7, 9, A1, A3, and A6; native
  shapes for the flow (slide 3) and timeline (slide 8); native tables on
  A2, A4, A5, and A6. Only slide 2's map is a PNG.
- Slide 5 uses a native rank chart instead of `pick_story.png`, because
  the PNG's labels were too small to read from the back of a room.
  Berkshire's last point (#1,047) is drawn at the bottom edge and labeled.
- A6 uses a native table from `results/global_balanced.csv` instead of
  `global_table.png`, for the same reason.
- Arial throughout, set in the theme, so previews match PowerPoint on
  Windows. Theme colors are the cockpit palette.
- Theme shape styles are removed from every drawn shape, so no theme
  shadow renders.
- No em dashes in the deck. Quote attributions sit on their own line.
- Speaker scripts are 75 to 90 words (30 to 36 seconds at 150 words a
  minute). The nine main scripts total about 770 words, about 5 minutes.
  "IF ASKED" blocks in the notes carry Q&A material outside the script.

**First render fixes:** two-line headlines crowded content (content now
starts at 2.2 in); slide 1 bullets overflowed into the source line; the
rule line and boxes showed theme shadows; "Research" broke mid-word; chart
titles wrapped; a custom data label on one bar hid the others in
LibreOffice (moved the text into the category name); the rank chart's
category axis sat on top (now crosses at the maximum); quote attributions
overflowed (short slide citations, full ones in `sources.md`).

**Mistake caught and fixed:** a script-trimming pass matched only
f-string notes, so new text for slides 1, 8, and A2 landed on slides 2,
9, and A4. The notes were restored from the original text and the
intended scripts applied by line. Word counts confirm each slide's script.
