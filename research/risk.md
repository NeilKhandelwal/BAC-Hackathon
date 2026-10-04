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
| Power availability | `queue_active_count` 19 projects, 4,550 MW, of which 3,550 MW is clean generation (`queue_active_mw_clean_excl_storage`) and 600 MW standalone storage. `queue_median_age_years` 3.5, worse than 66%. Delivered 2021-2025 (`queue_operational_mw_online_5y`): 0 MW, as under the legacy `queue_operational_mw_5y`. Grant PUD reports about 800 MW of large-load requests waiting and says large users fund the generation and transmission they need. | The campus averages 279 MW. The PUD's eight data center customers drew about 280 average MW in 2025, so this doubles that load. The PUD's share of its two dams averages about 633 MW, below its 2025 system load of 757 average MW. No hydro is spare. | Apply to the PUD queue before buying land. Fund or contract new clean generation. Energize in phases. | High |
| Heat | `nri_heat_wave_score` 97.3, worse than 97%. `days_above_95f_hist` 14.5, rising to 35.9 by 2050. | Hot days cut cooling efficiency and load the grid at the same hours. PUE rises from 1.163 to 1.196 by 2050. | Size cooling for 2050 design days. Liquid cooling for dense racks. | Medium |
| Wildfire | `nri_wildfire_score` 86.9, worse than 87%. The balanced gate excludes above the 95th percentile. | Smoke forces air-side economizers to close. Fire threatens transmission lines. | Closed-loop cooling that doesn't draw outside air. Defensible space. Two transmission paths. | Medium |
| Water stress | `water_stress_bws` 3.62 (high), worse than 84%, flat to 2050. `water_permit_risk` 1. Managed groundwater status was not researched for Washington. | Evaporative cooling would use 210 million gallons a year, 333 by 2050. The engine's own gate excludes evaporative cooling above a score of 2. | Dry cooling: 28 million gallons a year, for 2% more energy. | Low with dry cooling |
| Grid carbon | `grid_co2_lb_mwh` 632 is the Northwest average. The PUD's own generation is 100% hydro at 0 lb/MWh (eGRID balancing authority sheet). | The carbon claim depends on which power serves the new load: 0 tons a year at the PUD's rate, 236,000 at BPA's, 700,000 at the regional average. Loudoun: 675,455. | Contract new clean supply and report hourly matching. Don't claim the existing hydro. | Medium |
| Tax and state policy | `state_policy_risk` 0. The sales tax exemption is open to a new project in a rural county. A 2026 law ended it for replacement servers. A state proceeding on large loads is open. | Servers are replaced every few years, so most of the exemption's value over 30 years is gone. | Model the project with the exemption on the first build only. | Medium |
| Power price | `industrial_price_cents_kwh` 6.61, a state average, worse than 21%. | The $162M annual cost assumes that price, so it is a floor. At BPA's rate for a new large load, about $80 to $132 per MWh, the same energy costs $196M to $323M. Above about $92 per MWh, Grant costs more than Loudoun's $226M. PUD staff have proposed data center rate classes for 2027. | Negotiate the rate with the service agreement. Fund dedicated generation if it beats the BPA rate. | Medium |
| Cluster record | `dc_existing_count` 3 and `dc_existing_mw` 82 in FracTracker, which undercounts the Quincy cluster. `dc_pushback_count` 0. `fiber_share_locations` 0.99. | An existing cluster means fiber, contractors, and a utility that knows the load. No recorded opposition. | None needed. | Low |
| Flood, hurricane, tornado | `nri_inland_flood_score` 23.3. `nri_hurricane_score` 0. `nri_tornado_score` 8.7. | Low exposure. | Site above the mapped floodplain. | Low |
| Protected and sensitive land | Not in the table: the engine doesn't score it. Checked by hand (`research/sensitive_land.md`). PAD-US 4.1 puts 12.8% of the county in GAP 1-2 protected status, the 89th percentile nationally, but none of it within 5 km of Quincy. Nearest: WDFW Columbia Basin Wildlife Area parcels 5.8 km W and the Quincy Lakes Unit 8.6 km S. No national wildlife refuge, NPS unit, wilderness, or national forest within 30 km. Columbia NWR is 41 km S and Hanford Reach 54 km SE. No tribal land in the county; the nearest is 74.7 km N. | The brief asks about proximity to sensitive areas. Grant passes this check by hand, not because the model checked. | Site on farmland or already disturbed land near the existing cluster. Keep lighting and stormwater away from the wildlife area parcels. | Low |
| Tribal consultation and cultural resources | Quincy appears to sit inside the Yakama Nation's 1855 ceded area (a reading of the treaty text, not checked against an official map). Grant PUD has a long relationship with the Wanapum, whose heritage center is near Priest Rapids Dam about 50 km S. The Confederated Tribes of the Colville Reservation are an expected consulting party for the mid-Columbia. | A federal connection triggers Section 106 consultation with affected tribes: an Army Corps permit, a BPA interconnection, federal funding, or work on FERC-licensed hydro project lands. State funding triggers Executive Order 21-02 review. Ceded land gives no land-use authority over a private parcel. | Engage the tribes and Washington's Department of Archaeology and Historic Preservation early. Run a cultural resource survey before site selection. Prefer irrigated upland farmland, which carries less archaeological risk than land near the river and coulees. Unverified: consultation may matter more for the utility's transmission work near the Priest Rapids Project than for the campus parcel; see the power availability row. | Low |

## Comparison

The two counties that follow Grant once electricity cost is its own
pillar. PR #28 gives the order: Grant 63.7, Wayne 63.2, Whitman 63.0.

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

**Sensitive land and tribal consultation in the alternatives.** Neither
reference site has a conflict (`research/sensitive_land.md`):
- **Clark County, WA:** the Columbia River Gorge National Scenic Area
  covers about 31 km² at the county's east end, and its rules would
  constrain an industrial campus there. A site also needs to avoid the
  Ridgefield and Shillapoo lowlands and the Cowlitz Reservation near La
  Center, 23 km north of Vancouver. The Cowlitz Indian Tribe is the main
  consulting party, and the county requires an archaeological
  predetermination for many parcels.
- **Franklin County, NY:** about 68% of the county is inside the Adirondack
  Park, where a site needs an Adirondack Park Agency permit. Malone is
  6.1 km outside the Blue Line. The Saint Regis Mohawk Reservation is
  24.8 km northwest. A land claim settlement that could add reservation
  land 20 to 30 km northwest is pending in Congress.

**New York.** Executive Order 62 (2026-07-14) holds incomplete state
permit applications for data centers of 50 MW or more until a statewide
environmental review is done. It has no end date. The upstate grid is the
cleanest of any candidate at 242 lb/MWh, so those counties come back into
play if the order lifts.

## Limits

- County scores are not parcel scores. Wildfire, flood, and fiber need a
  site-level check.
- The engine doesn't score proximity to protected or tribal land. It was
  checked by hand for Grant, Clark, and Franklin
  (`research/sensitive_land.md`). A county protected-land share was built
  and measured but isn't in the table; a county share is a screen, not a
  siting check.
- eGRID understates the PUD's generation. It credits the PUD's balancing
  authority with 4.13 TWh and assigns Priest Rapids dam to BPA's. The PUD
  lists both Priest Rapids and Wanapum as its own, averaging about 1,000
  MW together, and holds rights to 63.31% of the output.
- The energy cost uses the state average industrial price. A 300 MW
  customer negotiates its own rate.
- The 2027 rate classes are a staff proposal, not adopted rates. The PUD
  adopted limits on data center load growth in March 2025. Both come from
  news reports.
- The Washington Department of Revenue's own page on the exemption could
  not be opened. The statute could.

## Sources

Primary:

- eGRID2023, BA23 sheet: Grant PUD balancing authority (GCPD), 4,131,457
  MWh, 100% hydro, 0 lb CO2/MWh. BPA: 212 lb/MWh.
  https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx
- Grant PUD data center FAQ, 2026-08-28: queue, 2025 load, data center
  load, dam output and the PUD's share.
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

- BPA rule for new large single loads (primary):
  https://www.bpa.gov/-/media/Aep/about/publications/fact-sheets/fs-202011-New-Large-Single-Load.pdf
- BPA's rate range of about $80 to $132 per MWh: BP-26 power rate
  schedules, as cited in `research/implementation.md`. Not opened for this
  document.
- Grant PUD's 2024 queue, 2,897 MW across 75 applicants:
  https://www.publicpower.org/periodical/article/grant-county-pud-details-queue-power-service-requests-large-load-customers
- Grant PUD load-growth limits for data centers, March 2025:
  https://columbiabasinherald.com/news/2025/mar/31/grant-pud-places-limits-on-electrical-demand-from-data-centers/
- Grant PUD proposed data center rate classes, 2026-09-25:
  https://www.publicpower.org/periodical/article/grant-pud-commissioners-considering-proposal-create-new-electric-rate-classes-data-centers
- Massachusetts application pause:
  https://www.wbur.org/news/2026/06/26/governor-healey-data-center-tax-incentives
