# ETL semantics audit: queue and FracTracker definitions

This is a compact record of the audit behind the queue-semantics
correction. The full audit lives on branch `claude/etl-semantics-audit`.

- **Reproduce it:** run `python research/etl_semantics_audit/run_audit.py`.
  It takes about 15 seconds.
  - The compact results land in `research/etl_semantics_audit/audit_summary.json`.
  - The full CSV tables land in `research/etl_semantics_audit/outputs/`,
    which is gitignored.
- **Tests:** `tests/test_queue_semantics.py`.
- **Harness checks:** these run before any experiment counts.
  - The production (corrected) mapping must reproduce `results/` byte for
    byte.
  - The legacy mapping, run on the same table, must reproduce the
    pre-correction `results/` at `c4c41b7` byte for byte.

  Both checks pass, so every ranking change below comes from the mapping
  alone.

## Status

| Field | Finding | Decision | Status |
| --- | --- | --- | --- |
| `queue_active_mw_clean` | 391 GW of standalone storage and 45 GW of storage-labeled hybrid capacity were counted as clean, 31% of 1,420 GW | Score `queue_active_mw_clean_excl_storage`; keep the legacy column | **Implemented** |
| `queue_operational_mw_5y` | Measures the 2019+ queue-entry cohort, not delivery; misses 88 GW delivered in 2021-2025 by earlier entrants | Score `queue_operational_mw_online_5y`; keep the legacy column | **Implemented** |
| `moratorium_active` | 174 vs 152 is all definition: 22 county moratoria listed active past their end date | Keep main's gate; add a flag for the 22; verify by hand | Follow-up |
| `dc_existing_count`, `dc_proposed_count` | Name-first matching misplaces St. Louis and Baltimore city facilities; point-first is right in 11 of 13 cases | Point-first matching and FracTracker's `delete_dup` flag | Follow-up (scored) |
| Facility deduplication heuristic | The 1 km same-name rule may merge real campus buildings | Insufficient evidence | Follow-up |
| `dc_pushback_count`, `dc_pushback_any` | Same rule, same 332 total | Keep main's definition | none |
| `dc_existing_mw`, `dc_proposed_mw` | 106 ranges or comma values parse to 0 (121 GW lost); unknown MW written as 0 | Fix parsing, null unknown | Follow-up (not scored) |

No source data changed between the two fetches compared: 0 of 260 county
moratorium rows and 0 of 1,701 facility records differ.

## Queue: clean generation

The legacy rule counts `mw_1` of every active project whose components all
fall in `CLEAN_SOURCES`, which includes battery and other storage. The scored
rule sums each clean-generation component's separately reported MW once.
Storage is excluded: it can help integrate renewables, but its emissions
depend on what charges it, so it isn't clean generation.

| Measure | National GW |
| --- | ---: |
| Legacy clean, including storage | 1,420.0 |
| Clean generation excluding storage (scored) | 993.2 |
| Standalone storage, including Other Storage | 391.4 |

- **Battery standalone:** 384.7 GW from 2,065 projects, all counted as clean
  by the legacy rule.
- **Other Storage standalone:** 6.1 GW from 15 projects.
- **Storage-first hybrids:** 243 active hybrids list storage as `type_1`.
  233 of them are Solar+Battery rows with `type_1 = type_2 = Battery` and no
  solar MW. The legacy rule counted their 45.0 GW. The scored rule counts 0,
  which is conservative.
- **Hybrids with a non-clean component:** 24 hybrids carry gas or "Other",
  with 6.2 GW of clean generation that the legacy rule dropped. The scored
  rule counts it when the MW is reported.
- **Double counting:** neither rule double-counts.
- **Affected counties:** 824 differ. In 199 of them, the whole legacy clean
  pipeline was storage.

## Queue: delivered capacity

The legacy rule keeps operational projects whose `q_year`, the year they
entered the queue, is 2019 or later. The scored rule dates operational
projects to 2021-2025 by `on_date`, or by `prop_date` only when `on_date` is
blank.

| Set | Projects | GW |
| --- | ---: | ---: |
| In both | 612 | 64.3 |
| Legacy only: online before 2021 | 65 | 1.2 |
| Legacy only: no online or proposed date | 42 | 6.4 |
| Scored only: entered the queue before 2019, online 2021-2025 | 612 | 88.0 |
| **Legacy total** | **719** | **72.0** |
| **Scored total** | **1,224** | **152.3** |

- **Proposed-date fallback:** 214 of the 1,224 projects (22.9 GW) are dated
  this way. The share without `on_date` varies sharply by region:

  | Region | Without `on_date` |
  | --- | ---: |
  | ISO-NE | 100% |
  | West | 82% |
  | NYISO | 61% |
  | Southeast | 42% |
  | CAISO, MISO, SPP, PJM, ERCOT | 4% or less |

- **Uncertainty indicator:** `queue_operational_online_date_fallback_share`
  reports the fallback share per county.
- **What it shows:** this is evidence the queue delivers, not capacity
  available to a new data center.

## Ranking effect

All variants run the unchanged engine and presets on the same committed
table. "Corrected" is production.

| Preset | Variant | Floor OK | Winner | Spearman vs legacy | Max composite change |
| --- | --- | ---: | --- | ---: | ---: |
| balanced | legacy | 915 | Grant, WA 63.74 | 1 | |
| balanced | clean only | 911 | Grant, WA 63.75 | 0.992 | 1.71 |
| balanced | delivered only | 917 | Grant, WA 63.67 | 0.992 | 1.47 |
| balanced | **corrected** | **912** | **Grant, WA 63.68** | 0.988 | 2.75 |
| speed_to_power | legacy | 489 | Wayne, TN 67.03 | 1 | |
| speed_to_power | **corrected** | **487** | **Wayne, TN 67.04** | 0.986 | 1.18 |
| sustainability_first | legacy | 73 | Whitman, WA 65.25 | 1 | |
| sustainability_first | **corrected** | **73** | **Whitman, WA 65.39** | 0.996 | 3.38 |

Gates and gate-passing counts are identical in every variant. The full
variant table is in `audit_summary.json`.

## FracTracker follow-ups

These are recorded here and left unchanged in production:

- **Moratoria:** 22 countywide moratoria are listed as active, but their
  recorded end dates passed between 2025-06-16 and 2026-09-17. Main's gate
  skips them. 18 of these counties rank in `balanced`, and Buncombe, NC
  ranks 30th in `sustainability_first`.
- **Municipal restrictions:** they never set `moratorium_active`.
- **Facility totals:** main counts 601 existing, 947 proposed, 150 stopped,
  and 332 pushback. The prior local rule counts 596, 942, 150, and 332.
  - Deduplication: 10 rows.
  - Geographic matching: 13 rows.
- **Reported MW:** 106 values with ranges or thousands separators parse to 0
  under main's rule, losing 120.9 GW.
