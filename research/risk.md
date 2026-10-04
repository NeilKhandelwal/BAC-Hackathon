# Risk assessment: Grant County, WA

Environmental and operational risks for a 300 MW campus in Grant County
(53025) that runs 20 to 30 years.

Reproduce the numbers: `python -m etl.risk 53025`. The code is
`etl/risk.py`. It reads the committed county table, so a different county
is a rerun, not a rewrite.

How to read the table:

- Values come from `data/processed/county_features.parquet`. Each row names
  its columns.
- "Worse than N%" is the share of the 3,109 counties with a better value.
- Energy, CO2, and water figures come from `etl/impact.py` at 300 MW.
- Anything from outside the table is listed under Sources and marked
  primary or secondary.

## Summary

One risk is high: whether the utility can serve the load. Heat, wildfire,
and the carbon claim are medium and have known mitigations. Water stress
forces dry cooling, which the site can afford. Energy costs $162M a year,
$64M less than in Loudoun County, VA.

## Risk table

| Risk | What the data says | Why it matters | Mitigation | Residual |
| --- | --- | --- | --- | --- |
| Power availability | `queue_active_count` 19 projects, 4,550 MW. `queue_median_age_years` 3.5, worse than 66%. `queue_operational_mw_5y` 0. Grant PUD reports about 800 MW of large-load requests waiting and says new large users pay for new generation and transmission. | The campus draws 2.44 TWh a year. That is 59% of the 4.13 TWh the PUD generates (eGRID). Existing data centers in Quincy already draw on that hydro. Nothing published says 300 MW is available. | Apply to the PUD queue before buying land. Fund or contract new clean generation. Energize in phases. | High |
| Heat | `nri_heat_wave_score` 97.3, worse than 97%. `days_above_95f_hist` 14.5, rising to 35.9 by 2050. | Hot days cut cooling efficiency and load the grid at the same hours. PUE rises from 1.163 to 1.196 by 2050. | Size cooling for 2050 design days. Liquid cooling for dense racks. | Medium |
| Wildfire | `nri_wildfire_score` 86.9, worse than 87%. The balanced gate excludes above the 95th percentile. | Smoke forces air-side economizers to close. Fire threatens transmission lines. | Closed-loop cooling that doesn't draw outside air. Defensible space. Two transmission paths. | Medium |
| Water stress | `water_stress_bws` 3.62 (high), worse than 84%, flat to 2050. `water_permit_risk` 1. Managed groundwater status was not researched for Washington. | Evaporative cooling would use 210 million gallons a year, 333 by 2050. The engine's own gate excludes evaporative cooling above a score of 2. | Dry cooling: 28 million gallons a year, for 2% more energy. | Low with dry cooling |
| Grid carbon | `grid_co2_lb_mwh` 632 is the Northwest average. The PUD's own generation is 100% hydro at 0 lb/MWh (eGRID balancing authority sheet). | The carbon claim depends on which power serves the new load: 0 tons a year at the PUD's rate, 236,000 at BPA's, 700,000 at the regional average. Loudoun: 675,455. | Contract new clean supply and report hourly matching. Don't claim the existing hydro. | Medium |
| Tax and state policy | `state_policy_risk` 0. The sales tax exemption is open to a new project in a rural county. A 2026 law ended it for replacement servers. A state proceeding on large loads is open. | Servers are replaced every few years, so most of the exemption's value over 30 years is gone. | Model the project with the exemption on the first build only. | Medium |
| Power price | `industrial_price_cents_kwh` 6.61, a state average, worse than 21%. | The $162M annual cost assumes that price. A new large-load rate would be higher, and no figure exists yet. | Negotiate the rate with the service agreement. | Medium |
| Cluster record | `dc_existing_count` 3 and `dc_existing_mw` 82 in FracTracker, which undercounts the Quincy cluster. `dc_pushback_count` 0. `fiber_share_locations` 0.99. | An existing cluster means fiber, contractors, and a utility that knows the load. No recorded opposition. | None needed. | Low |
| Flood, hurricane, tornado | `nri_inland_flood_score` 23.3. `nri_hurricane_score` 0. `nri_tornado_score` 8.7. | Low exposure. | Site above the mapped floodplain. | Low |

## Comparison

The two counties that follow Grant once electricity cost is its own
pillar. The order is provisional until that change merges.

- **Wayne County, TN (47181).** Worst three: inland flooding (83.1, worse
  than 83%), hurricane (57.7, worse than 69%), workforce (population
  16,251, worse than 65%). Energy costs $158M a year. The grid is the
  problem: no hydro next door, and a small county to hire from.
- **Whitman County, WA (53075).** Worst three: heat wave (92.2, worse than
  92%), wildfire (69.1, worse than 69%), inland flooding (69.0, worse than
  68%). Energy costs $159M a year. It shares Grant's heat and fire profile
  without Grant's existing cluster.

**Why Berkshire County, MA was dropped.** It ranked first under the
balanced preset. Its power costs $435M a year, $209M more than Loudoun,
to avoid 90,800 tons of CO2. That is about $2,300 per ton. Its inland
flood score sits at the edge of the gate: six counties separate it from
exclusion. And its rank leaned on a state tax exemption that has been
closed to new applications since June 2026. The state policy table now
codes that exemption as unavailable.

**New York.** Executive Order 62 (2026-07-14) holds incomplete state
permit applications for data centers of 50 MW or more until a statewide
environmental review is done. It has no end date. The upstate grid is the
cleanest of any candidate at 242 lb/MWh, so those counties come back into
play if the order lifts.

## Limits

- County scores are not parcel scores. Wildfire, flood, and fiber need a
  site-level check.
- The PUD's contract commitments for its hydro were not checked. eGRID
  assigns Priest Rapids dam (950 MW, in Grant County) to BPA's balancing
  authority. Whether the PUD owns it was not verified.
- The energy cost uses the state average industrial price. A 300 MW
  customer negotiates its own rate.
- A reported 2027 data center rate class at the PUD could not be
  confirmed.
- The Washington Department of Revenue's own page on the exemption could
  not be opened. The statute could.

## Sources

Primary:

- eGRID2023, BA23 sheet: Grant PUD balancing authority (GCPD), 4,131,457
  MWh, 100% hydro, 0 lb CO2/MWh. BPA: 212 lb/MWh.
  https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx
- Grant PUD data center FAQ, 2026-08-28:
  https://www.grantpud.org/blog/data-center-faqs
- RCW 82.08.986: https://app.leg.wa.gov/RCW/default.aspx?cite=82.08.986
- ESSB 6231, Chapter 266, Laws of 2026:
  https://app.leg.wa.gov/billsummary?BillNumber=6231&Year=2026
- Washington UTC large-load workshop, docket UE-260162:
  https://www.utc.wa.gov/news/2026/media-advisory-public-invited-join-utc-workshop-emerging-large-electric-loads
- New York Executive Order 62:
  https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops
- Massachusetts Chapter 238 of the Acts of 2024:
  https://malegislature.gov/Laws/SessionLaws/Acts/2024/Chapter238

Secondary:

- Grant PUD's 2024 queue, 2,897 MW across 75 applicants:
  https://www.publicpower.org/periodical/article/grant-county-pud-details-queue-power-service-requests-large-load-customers
- Massachusetts application pause:
  https://www.wbur.org/news/2026/06/26/governor-healey-data-center-tax-incentives
