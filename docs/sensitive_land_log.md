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

### 2026-10-04 05:39 UTC, PAD-US source found and first measurement

**Source.** USGS PAD-US 4.1 Summary Statistics, county table
`PADUS4_1VectorAnalysis_Uni_Counties_Clip_CENSUS2022.csv` (ScienceBase
item 6759b69fd34edfeb8710a3ea, 4 MB zip, direct URL). USGS built it from
the flattened Vector Analysis layer, with overlaps removed. The full 1.52 GB
national geodatabase and the state files are S3-hosted and download only in
a browser. They aren't needed.

**First numbers** (GAP 1-2 share of total county area; GAP 1-3 in
parentheses):
- Grant WA 12.8% (23.4%): WDFW wildlife areas 127k acres, USFWS 91k acres
  (Columbia National Wildlife Refuge).
- Clark WA 2.8% (18.4%).
- Franklin NY 32.0% (50.1%): Adirondack Forest Preserve, GAP 1, 265k acres.
- Berkshire MA 18.0%.
- National median 1.85%. Grant sits at the 89th percentile.

**Scratch run** (balanced, `pct_protected` scored in the land pillar as
`engine/pillars.yaml` already specifies):
- New top 10: Whitman WA 63.09, Scott IA, Mayes OK, Grant WA 62.22, Clark
  WA, Wayne TN, Payne OK, Washington AR, Grady OK, Benton WA.
- Grant falls from 1 to 4, and its land pillar from 75.0 to 53.6. Clark
  moves from 7 to 5. Franklin goes from 952 to 1,011, Berkshire from 1,047
  to 1,102.
- The top five sit within 0.9 points of each other.

**Advisor consulted on the data source, definition, and the flip.**
- **Approved:** the PAD-US 4.1 county CSV; GAP 1-2 for `pct_protected`;
  GAP 1-3 as context.
- **Added checks in the adapter:** keys unique, exactly 3,109 matched, and
  CSV total acres within 2% of Census land plus water for every county.
- **Denominator:** total area, from the same clip. State that it dilutes
  coastal and lake counties, and show land-only shares as a sensitivity.
- **Overlap:** American Indian lands are GAP 4 in this file, so
  `pct_protected` and `tribal_land_share` don't double count.
- **Decision rule for Phase 3.**
  - If Phase 1 finds a real conflict near Quincy, that's the stop condition.
  - If Grant's 12.8% comes from holdings that don't constrain the Quincy
    area, the county screen disagrees with the site check. Shipping would
    then change the deck's #1, which is more than a numbers update. Record
    Phase 3 as measured but not shipped, and put the decision at the top
    of the morning summary.
  - Keep `pct_protected` out of the frozen table unless shipping.
    Appending it is shipping, because the pillar map already scores it.
- **Compute first:** tribal and protected shares of the new top 10; Grant's
  SMAA top-10 share with the column scored; and three options with their
  effects: (a) score it, (b) use it as a gate, as `docs/schema.md`
  describes, (c) context only.

### 2026-10-04 05:42 UTC, Phase 2 adapters done; Phase 3 measured

**Phase 2.**
- `etl/adapters/pad_us.py` builds `pct_protected` (GAP 1-2) and
  `pct_protected_gap1to3` from the USGS county table.
- Checks built in: keys unique, all 3,109 counties matched, and USGS total
  area within 5% of Census 2024 land plus water. Every county is within 2%
  except Emporia city, VA, at 4.4%. That's a boundary-vintage difference;
  its neighbor Greensville County is within 0.1%.
- The download URL responds (HTTP 200, 4,086,817 bytes).
- Both new columns' schema rows are in `docs/schema.md`, along with the
  "screen, not a siting check" note.

**Phase 3 measurement** (`scratch/sensitive_land/measure.py`, output in
`scratch/sensitive_land/out/`):

| | Committed (c: context only) | a: scored in the land pillar |
| --- | --- | --- |
| #1 | Grant WA | Whitman WA (Grant 0.87 behind) |
| Grant, Clark, Franklin, Berkshire | 1, 7, 952, 1,047 | 4, 5, 1,011, 1,102 |
| Grant SMAA rank-1 / top-10 (floor on) | 11.5% / 50.5% | 0.2% / 14.0% |
| Clark SMAA rank-1 / top-10 | 6.9% / 30.6% | 8.3% / 31.9% |

- **New top 10 under (a):** Whitman WA, Scott IA, Mayes OK, Grant WA, Clark
  WA, Wayne TN, Payne OK, Washington AR, Grady OK, Benton WA.
- **None of them has much protected or tribal land.** The highest GAP 1-2
  shares are Grant 12.8% and Benton WA 9.9%. Every tribal share is 0;
  Oklahoma statistical areas are excluded by definition.
- **Land-only shares** barely differ from the total-area shares for these
  counties. Grant is 13.4% land-only.
- **Option b, a gate.** A 50% cap excludes 4 gate-passing counties (14
  nationally); a 25% cap excludes 30 (124 nationally). Grant passes both,
  and the top 10 is unchanged.
- **Option a also cuts Grant's robustness hard.** SMAA top-10 falls from
  50.5% to 14.0%. Grant is no longer among the most robust counties under
  this scoring.

The ship decision waits on Phase 1, per the decision rule.
