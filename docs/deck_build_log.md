# Deck build log

Build log for the editable pitch template in `docs/deck/`. The CURRENT
STATE block is overwritten at every step. History is append-only.

## MORNING SUMMARY

**What's done.** An editable 16:9 pitch template is at
`docs/deck/pitch_template.pptx`: 9 main slides for about 5 minutes and 6
appendix slides for Q&A. Every number is a real text box, native chart,
or native table. The only images are the team map on slide 2 and a cockpit
screenshot on slide 9. Every slide has a source line and a 30 to 36 second
speaker script that names the repo file behind each number. PNG previews
are in `docs/deck/previews/`. Quotes and image credits are in
`docs/deck/sources.md`. All 68 changeable numbers are in
`docs/deck/numbers_to_check.md`.

**Rebuild after tonight's changes.** From the repo root:

```bash
.venv/bin/python docs/deck/build_deck.py      # deck, numbers_to_check.md, sources.md
.venv/bin/python docs/deck/check_deck.py      # overflow, font size, overlap, footer checks
.venv/bin/python docs/deck/render_previews.py # PNG previews (needs LibreOffice)
```

Numbers from `docs/figures/facts.json` and the SMAA output refresh on a
rebuild. Numbers from research write-ups are typed into `build_deck.py`
next to their file. A rebuild overwrites hand edits to the .pptx, so make
wording changes in the script, or switch to hand edits once numbers are
final.

**Pull request: not opened.** `gh` is installed but not logged in, and
opening one needs credentials. Run `gh auth login`, then use the command
and text under "Pull request text" at the end of this log.

### Slides

| # | Headline | Visual |
| --- | --- | --- |
| 1 | Where AI campuses go now locks in decades of carbon, water, and cost. | LBNL share-of-electricity chart; NY Executive Order 62 quote |
| 2 | Grant County, Washington, if the campus funds its own clean power. | Team map with Grant circled; the condition box |
| 3 | Gates cut 3,109 counties to 1,565. Eight pillars rank the rest. | Flow diagram; eight weighted pillar chips |
| 4 | Dry cooling cuts water 87%. Carbon depends on the supply we fund. | Water and CO2 charts vs Loudoun; WA Data Center Workgroup quote |
| 5 | Corrections moved our pick. The price check cuts against Grant. | Rank chart: Berkshire 1 to 1,047; Grant 7, 9, 1, then 79th if WA pays $80/MWh |
| 6 | Grant makes the top 10 under more weightings than any county. | SMAA top-10 chart; "We didn't tune the weights..." line |
| 7 | Grant's case rests on power: full load by 2029, near today's price. | Grant PUD supply vs load chart; risk rows; win condition |
| 8 | Phase in behind new transmission, fund new clean supply, use no evaporative water. | 2027 to 2045 timeline; power, cooling, heat cards; Grant PUD quote |
| 9 | Change one condition and the engine gives a new, explained answer. | Cockpit screenshot; 1,565 vs 826 chart; hand-off to the live demo |
| A1 | Percentile pillars squeeze a 2.7x carbon gap into 10 points. | Pillar score vs CO2 charts |
| A2 | At today's prices, three counties tie within 1.1% over 25 years. | Win-condition table |
| A3 | Five ways to weight the pillars disagree. That's why we test, not tune. | Weights-by-method chart |
| A4 | Every county is scored from public data. Proxies are labeled as proxies. | Sources-by-pillar table |
| A5 | The engine screens on what's installed and average. Feasibility decides. | Proxy table |
| A6 | Same engine, new region or new question: countries, and industrial reuse. | Global top 5 table; Boone County, IL jobs chart |

### Placeholders remaining

None on any slide. Every quote on a slide was verified word for word at its
primary source. Open items that aren't placeholders:

- **Photos:** five openly licensed photos were verified but not placed,
  because every main slide already has a chart. They're in `sources.md`.
- **Virginia Clean Economy Act:** slide 4's notes say Virginia also sets
  2045 for Dominion. That's from memory, not verified for this deck. It's
  why the headline no longer claims the 2045 target as an edge.
- **Sensitive land and tribal rows:** slide 7 cites `research/risk.md` on
  the unmerged branch `fix/sensitive-land` at `12a8127`. Rechecked at the
  end of this session: the protected-land row is unchanged, and the tribal
  row only dropped an unsourced distance the deck doesn't use.
- **Boone County, IL jobs (A6):** taken from `docs/demo_script.md`, not
  rechecked against the county table.

### Numbers to check first

All 68 are in `docs/deck/numbers_to_check.md`. These move if the county
table, presets, or weighting outputs change tonight:

- Gate and floor counts: 3,109 / 1,565 / 912 (slides 2, 3, 9; `facts.json`
  `balanced`).
- Grant #1, composite 63.7, lead 0.5 points (slide 2, A5; `facts.json`).
- SMAA top 10: Grant 50.5%, Whitman 45.8%, Wayne 42.4%; rank-1 shares
  11 to 13% (slides 2, 6; `scratch/weighting/out/smaa_acceptability.csv`).
- Robustness near balanced weights 99.9% (slide 6; `facts.json`
  `featured.robustness`).
- Evaporative cooling: 826 pass, Wayne TN first (slide 9; rerun in step 1).
- Grant 79th at $80/MWh and 1,146th at $132/MWh with only Washington
  repriced (slides 5 and 7; scratchpad rerun in step 1, not committed).
- Three-county tie within 1.1%, $4.405B / $4.452B / $4.454B (slides 2, 7,
  A2; `docs/weighting.md`).
- Water 210.2 / 27.8 / 322.8 million gallons; CO2 235,547 / 700,390 /
  675,455 t (slide 4; `facts.json` `impact`, `grant_ranges`).
- Energy and carbon pillar: Grant 70.4 (93.6th pctl), Franklin 80.4
  (98.7th) (A1; engine on main `23bb71c`).

### Decisions a human should confirm

1. **Slide 5 shows the price result.** With only Washington repriced at
   BPA's $80/MWh, Grant falls to 79th. The advisor argued that hiding it
   is riskier than showing it. The slide and notes say the comparison is
   lopsided, because no other state's new-load rate is sourced.
2. **Story order changed from the brief.** "Why dollars" (Franklin vs
   Grant) moved to appendix A1, and risk and plan are split into slides 7
   and 8. Reason: the 2.7x figure uses the regional grid average that
   slide 4 calls an overstatement, and the brief's "3 percentile points"
   is stale (it's 5 points on current main).
3. **Monte Carlo charts aren't in the main deck.** With sales tax, they put
   Chesterfield SC first and a Washington county first in 0 to 2% of
   draws. SMAA carries robustness. A2's notes cover the Monte Carlo.
4. **Tribal consultation shows as "act early", not "Low"**, because WA
   Workgroup Finding 19c ties hydro load to tribal fisheries.
5. **No dollar-model ranking claim.** Slide 3 says the dollar model prices
   the leaders. With tax, Grant is 78th of 162 in the dollar shortlist.

### Found in other docs, not changed here

- `docs/weighting.md` says Franklin's and Grant's energy_carbon pillars
  sit at the 97th and 94th percentiles. On current main they're the 98.7th
  and 93.6th.
- `docs/demo_script.md` gives community weight 10%; the preset is 8.5%.
  It also calls 2,000 small weight perturbations "random weight draws."
- Franklin NY is 986th in the demo script and 952nd in `docs/weighting.md`.
- Whitman's composite is 63.0 in `research/risk.md` and 63.1 in
  `facts.json`.

## CURRENT STATE

- **Updated:** 2026-10-04, step 3 (final pass done).
- **Branch:** `deck/template`, created from `main` at
  `23bb71cb622fae2d82ba0cfe415b909888b422aa`. Never touched
  `fix/sensitive-land`.
- **Pull request:** not opened; `gh` isn't logged in. Text and command are
  at the end of this log.
- **Phase:** done, pending a human read and the PR.
- **Deck:** 15 slides. `check_deck.py` reports no problems. Previews
  rendered with LibreOffice 26 and inspected slide by slide.
- **Placeholders left:** none on slides. See the morning summary for open
  items.
- **Numbers to check:** 68 rows in `docs/deck/numbers_to_check.md`.
- **Sensitive-land check:** final fetch shows `origin/fix/sensitive-land`
  at `12a8127`. Slide 7 cites it.

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

### 2026-10-04, step 3: structural checks, cockpit screenshot, advisor review

**Structural checker.** `docs/deck/check_deck.py` flags text under 14 pt
(other than the footer), shapes off the slide or into the footer, likely
text overflow, overlapping content, more than three bullets, main slides
without a visual, and missing scripts. First run found 13 pt section tags,
a map and two bullet boxes reaching the footer, and tight quote boxes. All
fixed. A later footer check found two bands and a chart touching the rule.
Also fixed.

**Cockpit screenshot.** Built `app/cockpit` locally (`npm ci`,
`vite build`; `node_modules/` and `dist/` are gitignored) and captured it
with headless Chrome at 2x at
`?preset=balanced&cool=evaporative&c=53025`. Slide 9 shows two contiguous
pieces of the county panel stacked: Grant's header ("Excluded by a gate")
and the hard-gates list with the failed water-stress gate. The screenshot
also showed the app rounds community's 8.5% weight to 9%, so slide 3's
chips now round half up to match the app.

**Advisor review of the built deck (Opus subagent).** Adopted:

- Qualify the 1.1% tie as "at today's prices" on slides 2, 7, and A2. The
  dollar model's base case uses state-average power prices.
- Slide 7 headline now says power timing and price: "full load by 2029,
  near today's price." The win condition says "later or pricier, the
  three-way tie breaks against Grant." The $25M a month delay cost moved
  to the notes as an assumption.
- Show the price result on slide 5 (a fourth step on the rank chart and
  the third bullet), and add "robust to weights, not to price" to slide 6's
  script. Slide 5's headline now reads "The price check cuts against
  Grant."
- Slide 4 headline no longer claims the 2045 target, since Virginia sets
  one too. Added to the notes.
- Tribal consultation shown as "act early", not "Low". The Grant PUD speed
  quote moved from slide 7 to its notes to cut density.
- Slide 2 uses 50.5%, matching slide 6. Slide 3 says "Cost" instead of
  "$ and t". A2 says "of 162". A4's table no longer reaches the footer.
- Slide 2's map gets editable overlays: a larger title, a ring on Grant,
  and a larger legend line.

Not adopted: cropping the map to the Northwest. The national map shows how
selective the gates are; the ring and larger labels fix readability.

**Final fetch.** `origin/fix/sensitive-land` moved from `d2ed911` to
`12a8127`. Its `research/risk.md` change removes an unsourced Wanapum
distance, which the deck doesn't use. Slide 7 now cites `12a8127`, and its
notes add the consultation triggers from that branch. `origin/main` is
unchanged at `23bb71c`.

## Pull request text

Command, after `gh auth login`:

```bash
gh pr create --base main --head deck/template \
  --title "Add an editable pitch deck template with sources and numbers to check" \
  --body-file <file with the text below>
```

Text:

> **What this adds**
>
> - `docs/deck/pitch_template.pptx`: 16:9, 9 main slides (about 5
>   minutes) and 6 appendix slides. Native charts, tables, and text
>   boxes, so every number is editable. Source line and speaker script on
>   every slide.
> - `docs/deck/build_deck.py`: rebuilds the deck, `numbers_to_check.md`,
>   and `sources.md` from `docs/figures/facts.json` and the committed
>   weighting outputs.
> - `docs/deck/check_deck.py`: structural checks (overflow, font size,
>   overlap, footer).
> - `docs/deck/render_previews.py` and `docs/deck/previews/`: PNG renders
>   through LibreOffice.
> - `docs/deck/img/cockpit_cooling_switch.png`: cockpit screenshot for
>   slide 9.
> - `docs/deck_build_log.md`: decisions, advisor reviews, and a morning
>   summary.
>
> **Structure**
>
> 1 hook, 2 the answer, 3 how it decides, 4 sustainability impact, 5 how
> the pick changed (including the price check), 6 robustness (SMAA), 7 risk
> and win condition, 8 the 30-year plan, 9 the engine and demo hand-off.
> Appendix: A1 why tonnes, not percentiles; A2 three-county tie; A3 weights
> by method; A4 data sources; A5 limitations; A6 global run and Stage 2
> reuse.
>
> **Placeholders**
>
> None on slides. Quotes on slides are verified at primary sources
> (`sources.md`). Open items: Virginia's 2045 target in slide 4's notes is
> unverified; slide 7 cites `research/risk.md` from the unmerged
> `fix/sensitive-land` branch (`12a8127`); A6's Boone County numbers come
> from `docs/demo_script.md`.
>
> **Numbers to check**
>
> All 68 are in `docs/deck/numbers_to_check.md`, also marked `[[CHECK]]`
> in the speaker notes. The ones most likely to move tonight: 1,565 / 912
> gate and floor counts, Grant 63.7 and its 0.5-point lead, SMAA 50.5%,
> robustness 99.9%, 826 under evaporative cooling, Grant 79th with
> Washington at $80/MWh, and the 1.1% three-county tie.
>
> **Needs a decision**
>
> Slide 5 shows that Grant falls to 79th when only Washington is repriced
> at BPA's new-load rate. The story order differs from the brief ("why
> dollars" moved to A1). Details in the morning summary of
> `docs/deck_build_log.md`.
