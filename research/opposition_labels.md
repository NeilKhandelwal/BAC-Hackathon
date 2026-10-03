# Community opposition labels

Date: 2026-10-03. Purpose: a labeled table of US data center projects that
met local opposition, with outcome and stated reasons, to train and
validate the community-risk layer. Data Center Watch sells this data, so
the table is built from free sources.

## Primary source: FracTracker Alliance US Data Centers Tracker

Public ArcGIS feature services linked from
`https://www.fractracker.org/data-centers`. Free for non-commercial use with
credit. Fetch with `etl/fetch_fractracker.py`. Three layers:

| Layer | Rows | What it gives |
| --- | --- | --- |
| Facilities (`data_centers_v4_agol_all`) | 1,701 | name, operator, tenant, city, county, state, lat/lon, status, MW, cooling type, `community_pushback` (Yes or Unknown), `resistance_status`, `nda`, advocacy notes, source URLs |
| Victories (`data_centers_wins_v2`) | 54 | curated wins with `type_of_success` (withdrawn, denied, delayed, ordinance) and a narrative that names reasons |
| Moratoria (`DataCenterMoratoriums`, 4 sublayers) | 680 | jurisdiction with census GEOID, level (state, county, municipal, tribal), status (active, pending, defeated), category, effective and end dates |

Facility status counts: Proposed 759, Operating 534, Approved or under
construction 178, Cancelled 78, Suspended 72, Expanding 69. Pushback is
flagged Yes on 332.

This layer does two jobs. It is the label source for the risk model, and it
is a feature in its own right: existing and proposed data center density per
county is one of the strongest structural predictors of opposition
(Loudoun's backlash is a saturation effect).

The moratoria layer has 260 county rows keyed by GEOID, so it joins to FIPS
directly. Use it as a county feature (`moratorium_active`, `moratorium_pending`),
not as a project label.

## Secondary sources

| Source | Use |
| --- | --- |
| Wikipedia, "Opposition to AI data centers" (CC BY-SA) | about 12 US cases with reasons; used for hand rows |
| Data Center Watch free 2025 report (`/report`) | 16 named projects with dollar values; a Flourish map embed holds the points |
| Carbon Direct and Relae, "Community Opposition to AI Data Centers" (June 2026 PDF) | 7 detailed case studies; the 46-project table is not published |
| Heatmap News 2025 cancellations piece | totals and 3 to 4 named cases; its map CSV has 26 unnamed points |
| Piedmont Environmental Council Virginia map (ArcGIS) | 460 Virginia sites, proposed and existing; a site pool, not labels |
| Local news (WRDW, WFAE, The Real Deal, PGJ, 13WMAZ, ABC15) | outcome dates for hand rows |

## The seed table

`data/processed/opposition_seed_labels.csv`, built by
`etl/build_seed_labels.py`. 246 rows.

Columns: `project_name, developer, state, county, city, announced_date,
outcome_date, status, reasons, source_url, label_source`.

| Status | Rows |
| --- | --- |
| approved | 83 |
| cancelled | 69 |
| delayed | 59 |
| withdrawn | 26 |
| moratorium (6 flagged `?`) | 8 |

Label source: FracTracker facilities 195, FracTracker victories 31,
hand-coded 20. Hand rows override matching FracTracker rows.

Fill rates: county 242, developer 133, reasons 100, outcome date 71.

Reason vocabulary: water, noise, grid_strain, electricity_rates, farmland,
rural_character, secrecy, tax_abatement, air_quality, property_values,
traffic, light, wetlands_wildlife, historic, zoning_process, height_visual,
proximity_to_homes, health.

A trailing `?` on any value means it was inferred by keyword or regex from
FracTracker's free text, not confirmed by a person.

## Known problems

1. **The approved class is noisy.** 79 of 83 approved rows are FracTracker
   facilities with pushback Yes that are approved or operating. The flag
   doesn't say whether opposition came before approval, and some fights are
   ongoing. Only 4 approved rows are hand-verified.
2. **No true negatives.** Every row had opposition. A model trained on this
   learns which fights succeed, not where fights start. For the second
   question, use FracTracker's 524 operating and 115 approved facilities with
   pushback Unknown as the comparison pool, and say in the deck that Unknown
   is not None.
3. **Dates are sparse.** Outcome date is filled on 29 percent of rows. No
   time-aware split is possible without more coding.
4. **Reasons are sparse and keyword-coded.** 59 percent of rows have none.
5. **Geographic bias.** Texas, Virginia, Pennsylvania, Indiana, and Ohio
   dominate. The Mountain West and Plains are thin, which matches the media
   coverage bias in GDELT. Don't read a low count there as low risk.
6. **FracTracker data quality.** One facility name is a change.org URL.
   Prince William Digital Gateway is Cancelled in one layer and Suspended in
   another. Record dates are edit dates, not outcome dates.

## Recommended use in the model

- **Structural risk model** (county level): target is "any project in this
  county was cancelled, withdrawn, or delayed after opposition" versus "has
  operating or approved facilities and no recorded pushback." Features come
  from the county table: farmland share, existing facility count, rurality,
  water stress, moratorium flags, state bill activity.
- **Reason profile** (county level): share of local coverage by reason
  type, from GDELT article classification. Validate against the 100 rows
  with coded reasons.
- Cheapest improvement: two hours hand-verifying the 63 approved-with-
  pushback rows and adding outcome dates.
