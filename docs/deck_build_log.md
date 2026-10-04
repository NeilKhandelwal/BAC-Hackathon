# Deck build log

Build log for the editable pitch template in `docs/deck/`. The CURRENT
STATE block is overwritten at every step. History is append-only.

## MORNING SUMMARY

Updated after round 2 (main at `c239868`, PR #40 merged into this branch).

**What changed in round 2.** The deck now pitches the tool, with Grant as a
worked example. It picks up the sensitive-land and land cover work from PR
#40, so every number traces to the current `docs/figures/facts.json`,
`results/`, and research files. Slide text is plain language with no kicker
labels, no em dashes, and no colons or semicolons. The build stops if a
string breaks that rule. Every slide fades in, and two slides build on their
own (the screening steps on slide 2 and the timeline on slide 8).
PowerPoint for Mac opened the file without a repair prompt and reports the
transitions and effects.

**Files.** `docs/deck/pitch_template.pptx` (9 main slides, 6 appendix),
`docs/deck/previews/`, `docs/deck/numbers_to_check.md` (70 rows),
`docs/deck/sources.md`, and two Streamlit screenshots in `docs/deck/img/`.

**Rebuild after any change tonight.** From the repo root:

```bash
.venv/bin/python docs/deck/build_deck.py      # deck, numbers_to_check.md, sources.md
.venv/bin/python docs/deck/check_deck.py      # overflow, font size, overlap, footer, notes
.venv/bin/python docs/deck/render_previews.py # PNG previews (needs LibreOffice)
```

A rebuild overwrites hand edits to the .pptx.

### Slides

| # | Headline | Visual |
| --- | --- | --- |
| 1 | Where AI data centers get built locks in their carbon, water, and costs for decades | LBNL share-of-power chart, NY Executive Order 62 quote |
| 2 | Our tool ranks all 3,109 counties for the project you describe | App screenshot, screening steps that build in, eight weighted factors |
| 3 | It now accounts for protected land, farmland, and wetlands | Grant's land and permitting scores before and after land cover |
| 4 | With balanced weights, two counties in eastern Washington tie for first | Team map with Grant and Whitman circled, the hydro condition |
| 5 | Different weights favor different counties, so the tool shows the spread | Top 10 shares across 5,000 random weightings |
| 6 | A dry-cooled campus in Grant would use 87% less water | Water and CO2 charts against Loudoun, WA Data Center Workgroup quote |
| 7 | Power is the biggest risk, so the project has to bring its own | Grant PUD supply and load chart, three rated risks |
| 8 | The campus would grow with new transmission and new clean power | 2027 to 2045 timeline that builds in, Grant PUD quote |
| 9 | Change one assumption and the tool gives a new answer with its reasons | App screenshot of Grant excluded, 1,565 against 826 chart |
| A1 | How our pick changed as we fixed the inputs | Rank chart on a log scale, ending with Grant 77th at BPA's rate |
| A2 | Why we also check the leaders in dollars and tons | Franklin against Grant CO2, energy and carbon share of cost gaps |
| A3 | Clark WA and Franklin NY are the alternatives, each with a condition | Cost, win condition, and land check table |
| A4 | Every county is scored from public data, and proxies are labeled | Sources by factor, now with PAD-US, NLCD, and tribal boundaries |
| A5 | The tool screens counties. Choosing a parcel still takes site work. | Limits and a proxy table |
| A6 | The same engine works for other regions and other questions | Global top 5 table, Boone County jobs chart |

### Placeholders remaining

None. Open items:

- The live demo should use the Streamlit app. The React cockpit's data
  wasn't refreshed for PR #40 (needs `npm run data:engine` in
  `app/cockpit`), so neither the deck nor the demo should use it until then.
- Slide 6's notes say Virginia also sets a 2045 clean target for Dominion.
  That's not verified for this deck.
- A6's Boone County jobs come from `docs/demo_script.md`, not rechecked.
- Five openly licensed photos are verified and listed in `sources.md`, not
  placed.

### Numbers to check first

All 70 are in `docs/deck/numbers_to_check.md`. The ones most likely to move:

- 1,565 pass the limits and 883 clear the floor (slides 2 and 4).
- Grant 63.70 and Whitman 63.69 (slide 4, A5; `results/balanced.csv`).
- Top 10 shares, Whitman 43.9%, Cuyahoga 36.9%, Clark 35.9%, Grant 35.8%,
  Hutchinson 35.2% (slide 5; `facts.json` `weights`).
- Grant in the top 10 near balanced weights, 99.95% (slide 5).
- Grant land 75.0 to 52.8 and permitting 53.2 to 63.2 (slide 3).
- Evaporative cooling, 826 pass, 502 clear the floor, Whitman first
  (slide 9; rerun in step 4).
- Grant 77th with only Washington at $80/MWh (slide 7 notes, A1; rerun in
  step 4, not committed).
- Berkshire 1, 27, 1,164 and Grant 7, 7, 1 (A1; `facts.json` `pick_story`).

### Decisions a human should confirm

1. **Tool-first story.** Main slides are hook, tool, land, example, weights,
   impact, risk, plan, and the switch into the demo. "How the pick changed"
   moved to appendix A1.
2. **The weights-by-method chart is gone.** Its CRITIC, entropy, and revealed
   preference weights predate PR #40. A2 keeps the dollar-model finding
   (energy and carbon carry 67 to 88% of cost differences), which PR #40
   doesn't affect.
3. **Grant stays the worked example** because its site research exists,
   while slides 4, 5, and A5 say it's level with Whitman.
4. **The land row on slide 7 is rated Low**, following `research/risk.md`.
   Its text frames tribal consultation as a process step to start early.

## CURRENT STATE

- **Updated:** 2026-10-04, step 4 (round 2 rebuilt on main `c239868`).
- **Branch:** `deck/template`, with `origin/main` at `c239868` merged in
  (`051b336`, no history rewritten).
- **Pull request:** to open after the advisor's final review, now that
  `gh` is logged in as ValsTRM.
- **Deck:** 15 slides. `check_deck.py` reports no problems. Previews from
  LibreOffice; PowerPoint for Mac opened and exported the file cleanly.
- **Placeholders left:** none.
- **Numbers to check:** 70 rows.

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

### 2026-10-04, step 4: round 2, tool-first deck on main c239868

**Brief from the user.** Pitch the tool, not one answer. Add the PR #40
sensitive land and land cover work and the farmland talking points. Use
natural language with no kicker subheadings or AI-sounding phrasing, no em
dashes, and few colons or semicolons. Add some motion without overdoing it.
`gh` is now logged in. The LSEG connector the user added isn't needed for
this deck (it serves market and financial data).

**Merge.** `git merge origin/main` (`c239868`) into `deck/template` as
`051b336`. Clean, because main never touched `docs/deck/`.

**Checks and reruns** (scratchpad only; nothing in `results/` or the table):

- `facts.json` matches the briefing. 883 clear the floor. Grant 63.70 and
  Whitman 63.69 in `results/balanced.csv`. Top 10 shares across 5,000 random
  weightings put Whitman first (43.9%) and Grant fourth (35.8%), behind
  Cuyahoga OH and Clark WA.
- Evaporative cooling gives 826 pass, 502 clear the floor, and Whitman first,
  matching `docs/demo_script.md`.
- Price rerun with only Washington at BPA's rate. At $80/MWh Grant is 77th
  and Whitman 79th, with Mayes OK first. At $132/MWh they're 1,151st and
  1,152nd.
- Energy and carbon pillar percentiles are unchanged (Grant 93.6th,
  Franklin 98.7th), since PR #40 didn't touch those columns.
- Land shares from the county table. Grant is 12.8% protected, 42.9%
  cropland, and 1.8% forest and wetland. Whitman is 0.2% protected and
  71.1% cropland.
- Farmland in opposition cases. 7 of the 100 rows with stated reasons in
  `data/processed/opposition_seed_labels.csv`, all inferred by keyword. Top
  reasons are zoning process (38), water (31), and grid strain (22).
- Grant and Whitman map positions located from `counties.geojson`
  (EPSG:5070) against the map's drawn extent.

**Screenshots.** Ran `app/app.py` locally and drove it with Playwright
through system Chrome. `docs/deck/img/app_overview.png` is the default view
(1,565 pass, 883 clear the floor). `docs/deck/img/app_cooling_switch.png` is
Grant under evaporative cooling ("Excluded by
max_water_stress_if_evaporative"). Removed the React cockpit screenshot,
because the cockpit's data predates PR #40.

**Rewrite.** New `build_deck.py` slide code on the old helpers. Main slides
are hook, tool, land, example, weights, impact, risk, plan, and switch.
Appendix is how the pick changed, dollars and tons, alternatives, sources,
limits, and extensions. The build rejects slide text with a colon,
semicolon, or em dash, and bullets of 12 words or more. Notes are spoken
scripts, then "If someone asks" paragraphs, then the number list.

**Motion.** A fade transition on every slide. Slide 2's four screening steps
and slide 8's five milestones fade in one after another, without clicks.
Written as PowerPoint timing XML. PowerPoint for Mac opened the file, reported
a fade on each slide, 4 effects on slide 2, and 15 on slide 8, and exported
a PDF that matches the LibreOffice previews.

**Render fixes.** Map title wrapped over the map; several chart titles
wrapped or hyphenated; slide 5's bottom line overflowed; A1 squeezed ranks 27
and 1,164 onto a clipped edge, so it now uses a log-scale rank axis; a
Berkshire label wrapped onto its marker in PowerPoint; four scripts opened
with "Here's", now varied.

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
