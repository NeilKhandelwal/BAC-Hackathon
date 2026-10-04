# Design

> **Provisional.** This file was written before the build, from the approved
> Assessment Report direction. After the vertical slice ships, it's rewritten
> from the built cockpit. Where the build and this file disagree, the build
> is the evidence and this file gets corrected.

Scope: the site-selection cockpit in `app/cockpit/`. Product truth lives in
`PRODUCT.md`. The Streamlit app in `app/app.py` isn't governed by this file.

## Direction: Assessment Report

The cockpit borrows the figure language of climate assessment reports:
findings stated plainly, evidence set in ruled rows, and one signature graphic
that turns a distribution into stripes. It's a working tool first. The world
contributes type, palette, density, and one signature move. It never supplies
the layout, the navigation model, or the controls, which stay standard web
controls.

What it refuses: the dark mission-control dashboard with a neon choropleth,
KPI tiles, and cards. Also the cream editorial broadsheet.

Light ground. The use scene is a 1080p screen recording played in a pitch
room, stills pasted onto slides, and judges at a laptop in a lit hall. Dark
grounds lose contrast in all three.

## Four kinds of number

Every number belongs to exactly one kind, and its kind is visible without
hover. Mixing them is the failure this system exists to prevent.

| Kind | What it is | Visual marker | Wording |
| --- | --- | --- | --- |
| Observed | A source value from the county table | Ink numerals with unit and source name | "Water stress 3.6 of 5 · Aqueduct 4.0" |
| Derived | Percentiles, pillar scores, composite, rank | Graphite ramp and pillar hues | "Score 63.7", "84th percentile nationally" |
| Rank stability | Share of sampled weight scenarios in which a county ranks top 10 | Navy and blue stripes | "Top 10 in 91% of sampled weight scenarios" |
| Projected | 2050 climate and water values | Ember scale, always labeled with scenario | "2050 · RCP8.5 · projected" |

Rank stability is never called confidence, likelihood, or probability. It
describes how sensitive a rank is to decision priorities. Supporting copy may
say a rank is "stable" or "sensitive to weights."

Missing values say **No data** in place of the number and lower the coverage
figure. Any statement about how the engine scores a missing value comes from
adapter metadata, never from hard-coded UI copy.

## Color

Tokens are CSS custom properties in `app/cockpit/src/styles/tokens.css`.
Contrast is measured against white panels and the ground.

### Neutrals

| Token | Value | Use | Contrast on white |
| --- | --- | --- | --- |
| `--ground` | `#F3F5F4` | app background | |
| `--panel` | `#FFFFFF` | work areas | |
| `--ink` | `#111518` | primary text, rules at 100% | 18.4 |
| `--ink-2` | `#46505A` | secondary text | 8.2 |
| `--ink-3` | `#5F6A74` | tertiary text, axis labels; floor for any text | 5.5 |
| `--rule` | `#D3D8D6` | hairlines between rows and areas | |
| `--rule-strong` | `#A9B0AD` | area borders, slider tracks | |

### Pillar hues

One fixed hue per pillar, used everywhere that pillar appears: weight
sliders, contribution bars, evidence row markers, and the stacked bar in the
shortlist. All are at least 4:1 on white, so they also work as filled marks
next to text. Every pillar mark also carries its pillar name or short label,
so color is never the only cue.

| Pillar | Token | Value |
| --- | --- | --- |
| Energy and carbon | `--p-energy` | `#B86200` |
| Water | `--p-water` | `#14758F` |
| Climate resilience | `--p-climate` | `#B0303F` |
| Grid and infrastructure | `--p-grid` | `#5B4BA0` |
| Land | `--p-land` | `#5E6E12` |
| Community | `--p-community` | `#23804F` |
| Permitting | `--p-permitting` | `#86523A` |
| Cost | `--p-cost` | `#9A3A8C` |

The pillar set comes from adapter metadata. A pillar without a mapped hue
falls back to `--ink-2` and logs a warning.

### Composite choropleth (derived)

A seven-step graphite ramp, light to dark for low to high score, applied to
gate-passing counties only. Breaks are quantiles of the eligible set and the
legend prints them. Graphite keeps hue free for pillars, stability, and
projections.

`#ECEBE6 #D3D2CB #B3B3AC #8E8F8A #696C6A #454A4B #22272A`

Counties that pass the gates but fail the pillar floor take the ramp at 45%
opacity and sit below every floor-passing county in rank.

### Excluded counties: hatching

Gate-excluded counties are hatched, never only faded: 45-degree lines in
`--hatch` (`#9AA19C`), 1px wide at a 5px pitch, over `--ground`. The legend
shows the swatch with the label "Excluded by a gate." The finding panel names
the gate.

### Rank stability (signature)

| Token | Value | Meaning |
| --- | --- | --- |
| `--stab-top3` | `#0B3C6F` | sampled scenario where the county ranks top 3 |
| `--stab-top10` | `#4F82BD` | ranks 4 to 10 |
| `--stab-out` | `#DCE3EA` | outside the top 10 |

### Projected (ember scale)

Used only for 2050 values, always with a scenario label.

`#FBE7A1 #F2B33D #D9532B #8E1B3E #4A1748`, from low to high projected stress
or heat.

### Selection and focus

- Selected county: a 2.5px `--ink` outline with a white halo on the map,
  and a 2px inset `--ink` outline around its shortlist row.
- Comparison county: a 2px dashed `--ink-2` outline on the map, and "Compare"
  printed on its row.
- Keyboard focus: a 2px `--ink` outline at 2px offset on every control.
  Never removed.
- Text selection uses `--stab-out` with `--ink` text. Scrollbars are thin,
  `--rule-strong` thumb on `--ground`.

## Typography

**Public Sans**, the U.S. Web Design System face, self-hosted through
`@fontsource-variable/public-sans`. It's a government public-data voice with
sturdy numerals, which suits public-data evidence. All numerals in tables,
scores, and counts use `font-variant-numeric: tabular-nums`. There's no
monospace: numbers are data, not code.

The root size is `clamp(14px, 0.8333vw, 16px)`, which gives 16px at 1920 wide
and 14px at 1280. Sizes are in rem.

| Role | Size | Weight | Notes |
| --- | --- | --- | --- |
| Rank numeral | 1.75rem | 700 | tabular |
| Finding headline | 1.375rem | 650 | county name and rank |
| Section title | 1rem | 650 | sentence case, no eyebrow labels |
| Body and row text | 1rem | 400 | line height 1.4 in rows, 1.5 in prose |
| Label | 0.875rem | 500 | control labels, column heads |
| Fine print | `--fs-fine`: max(13px, 0.8125rem) | 400 | source names, legend breaks |
| Micro | `--fs-xs`: max(12px, 0.75rem) | 600 | rank-change tags, column heads; nothing smaller ships |

Headings are sentence case. Labels never use letter-spaced uppercase as
decoration.

## Layout

### 1920×1080, the recording target

One screen, no page scroll.

| Area | Width | Contents |
| --- | --- | --- |
| Top bar | full, 64px | working title, preset tabs, facility facts, Today/2050 switch with scenario, Synthetic data badge, Reset Demo |
| Left rail | 304px | pillar weight sliders, then the gate funnel |
| Center | flexible | map on top; finding panel in the lower 400px once a county is selected, a one-line hint strip before that |
| Right | 480px | top-10 shortlist, then "Left the top 10" |

The finding panel splits into three columns: summary with gates and
coverage, pillar contributions, and evidence with Today vs 2050.

### Below 1600 wide or 900 tall (1280×720 included)

The finding panel becomes a bottom drawer over the map. It opens when a
county is selected and collapses to a 48px header strip with the county name
and rank. The left rail narrows to 264px and the shortlist to 400px. Text
never drops below 13px and controls never clip. The map takes the space the
panel gives up.

### Below 1100 wide

Not a target. Areas stack in one column, in reading order: top bar, shortlist,
map, finding, controls.

## Components

- **Preset tabs:** a standard tab list (`role="tablist"`). The active tab has
  an ink underline 3px thick. Editing any value after picking a preset shows
  "Edited" beside the active tab.
- **Today / 2050:** a two-option segmented control. 2050 shows the scenario
  select beside it (RCP4.5 or RCP8.5).
- **Weight slider:** a native range input styled with the pillar hue fill. It
  shows the pillar name, the stated weight as a percent, and the normalized
  weight when the weights don't sum to 100.
- **Gate row:** gate name, the threshold control (a range or a checkbox), and
  the live count of counties this gate excludes. The funnel total
  ("1,565 of 3,109 counties pass") heads the list.
- **Shortlist row:** rank numeral, rank change, county and state, score,
  and the rank stability outcome bar with its share. The row is a button;
  the outcome bar is a separate button laid over its lower line.
- **Evidence row:** pillar marker, metric label, observed value with unit,
  national percentile, source. A missing value prints "No data."
- **Badge:** "Synthetic data" in `--p-energy` text on a white panel with a
  1px border. It's always visible while fixture data is active.

No cards inside cards. Areas are separated by rules and whitespace, not
shadows. The only shadow is the drawer at narrow widths: `0 -6px 20px
rgb(17 21 24 / 0.12)`.

## Signature: the rank stability outcome bar

Each shortlist row carries one full-width stacked bar built from every
sampled weight scenario, 2,000 in the presets.

- Three segments: `--stab-top3` for ranks 1 to 3, `--stab-top10` for ranks
  4 to 10, `--stab-out` for outside the top 10. Segment widths are the draw
  counts, so they always fill 100% of the bar.
- The bar is 14px tall in the shortlist and 20px in the finding panel, with a
  1px `--rule-strong` outline so the pale segment still reads.
- A visible label beside it, "Top 10 in 98%", is authoritative. It never
  rounds a partial share to 100% or 0%; it prints ">99%" or "<1%".
- One persistent legend under the shortlist header names the three
  categories and the scenario count.
- The whole bar is one button. Hover, keyboard focus, or a tap opens a
  tooltip with counts and percentages for each category. Percentages use
  largest-remainder rounding so they total exactly 100.0%. A tap also selects
  the county, as a row click does. Escape or a tap elsewhere closes it.
- No width animation. While stability recomputes, the bar and label fade to
  45% opacity. Before the first result they show a neutral empty track and
  "Computing"; when stability can't be computed, a dashed track, "Not
  computed", and the reason in the legend slot.
- Shortlist rows no longer carry the pillar strip; pillar detail lives in the
  finding panel.

## Map

- Projection: conic equal-area fitted to the contiguous US.
- County boundaries: 0.5px `--panel` strokes. State boundaries: 1px
  `--ink-3` at 60% opacity.
- **Rings:** each top-10 county carries a white disc, 26px across, with a
  2px `--ink` stroke and its rank numeral in ink. Rings sit at the county's
  internal point and never scale with zoom.
- Selecting a county zooms to its region, about eight times the county's
  bounds. A national inset, 160px wide, appears in the corner with the view
  box drawn on it. Reset view returns to the nation.
- Zoom and pan: the scroll wheel or a trackpad pinch zooms around the
  pointer, from 1x to 12x. Dragging pans once zoomed in, and a press that
  doesn't move is still a click. Two 32px buttons, + and −, sit in the
  bottom-right corner of the frame, above the drawer when it's open. Input
  follows the pointer directly, with no easing; selection zooms keep the
  480ms transition. "Show all counties" and Reset demo return to the full
  view.
- The legend sits inside the map frame: graphite ramp with breaks, the hatch
  swatch, the floor-fail swatch, and the ring sample.

## Motion

Motion explains a state change. There's no ambient or decorative motion.

| Change | Motion | Duration |
| --- | --- | --- |
| Shortlist reorder | FLIP: rows travel from old to new position | 420ms, `cubic-bezier(0.2, 0, 0, 1)` |
| New entry | slides in from below; "New" label stays | 420ms |
| Dropped entry | moves to "Left the top 10" with its reason; stays until the next change | 420ms |
| Rank change badge | appears with the move, stays until the next change | |
| Map rings | move with the rows, same duration and easing | 420ms |
| County fill | color crossfade | 240ms |
| Map zoom | view box transition | 480ms |
| Drawer | slides up | 240ms |

With `prefers-reduced-motion: reduce`, every change is instant. Badges,
"New" labels, and the dropped list still carry the change.

## Density

The evidence panel is dense: 28px rows with hairline rules, every value with
its percentile and source. The shortlist rows are 56px so they read in a
recording. Spacing follows a 4px base: 4, 8, 12, 16, 24, 32.

## Accessibility

- WCAG 2.2 AA contrast for text, and 3:1 for meaningful marks.
- Every control is reachable by keyboard, in the order top bar, weights,
  gates, map, shortlist, finding panel. Arrow keys move sliders.
- The map has a keyboard path: the shortlist and a county search select
  counties. Map paths aren't individual tab stops, since there are 3,109.
- Color is never the only cue. Pillars carry names, excluded counties are
  hatched and labeled, and stability prints its share.
- No information is available only on hover. Hover only highlights.
- Live regions announce the result of a change: "Speed to power. 9 of the
  top 10 changed. 1,102 counties pass the gates."
