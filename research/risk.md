# Risk assessment

Environmental and operational risks for a 300 MW campus that runs 20 to 30
years. The featured county is not final, so this covers both candidates:
Grant County, WA (53025) and Berkshire County, MA (25003).

Reproduce the numbers: `python -m etl.risk 53025 25003`. The code is
`etl/risk.py`. It reads the committed county table, so a new county is a
rerun.

How to read the tables:

- Values come from `data/processed/county_features.parquet`. The column is
  named in each row.
- "Worse than N%" is the share of the 3,109 counties with a better value.
- Energy, CO2, and water figures come from `etl/impact.py` at 300 MW.
- Anything from outside the table is listed under Sources and marked
  primary or secondary.

## Verdict

| | Grant, WA | Berkshire, MA |
| --- | --- | --- |
| Energy cost per year | $162M, $64M under Loudoun | $435M, $209M over Loudoun |
| CO2 per year, dry cooling | 236,000 to 700,000 t, depending on supply | 584,653 t, 13% under Loudoun |
| Sales tax exemption for a new project | available, narrowed in 2026 | on the books, applications paused |
| Worst risks | power availability, heat, wildfire, water stress | power cost, state policy, inland flooding |
| Risks rated high | 1 | 2 |

Berkshire ranks first under the balanced preset, but two things undercut
it. Its rank leans on a tax exemption that a new project can't get today,
and its power costs almost twice Loudoun's for a 13 percent CO2 saving.
Grant is the stronger site if the utility can serve the load. That is its
one high risk.

## Grant County, WA

| Risk | What the data says | Why it matters | Mitigation | Residual |
| --- | --- | --- | --- | --- |
| Power availability | `queue_active_count` 19 projects, 4,550 MW. `queue_median_age_years` 3.5, worse than 66%. `queue_operational_mw_5y` 0. Grant PUD reports about 800 MW of large-load requests waiting and says new large users pay for new generation and transmission. | 300 MW is 59% of everything the PUD generates in a year (4.13 TWh, eGRID). The existing hydro is spoken for. | Apply to the PUD queue before buying land. Fund or contract new clean generation. Energize in phases. | High |
| Heat | `nri_heat_wave_score` 97.3, worse than 97%. `days_above_95f_hist` 14.5, rising to 35.9 by 2050. | Hot days cut cooling efficiency and stress the grid at the same hours. | Size cooling for 2050 design days. Liquid cooling for dense racks. | Medium |
| Wildfire | `nri_wildfire_score` 86.9, worse than 87%. The balanced gate excludes above 95. | Smoke forces air-side economizers to close. Fire threatens transmission lines. | Closed-loop cooling that doesn't draw outside air. Defensible space. Two transmission paths. | Medium |
| Water stress | `water_stress_bws` 3.62 (high), worse than 84%. Flat to 2050. `water_permit_risk` 1. Managed groundwater status not researched. | Evaporative cooling would use 210 million gallons a year, 333 by 2050. | Dry cooling: 28 million gallons a year, for 2% more energy. | Low with dry cooling |
| Grid carbon | `grid_co2_lb_mwh` 632 is the Northwest average. The PUD's own generation is 100% hydro at 0 (eGRID balancing authority sheet). | The carbon claim depends on which power serves the new load. At 0, 212 (BPA), and 632 lb/MWh, the campus emits 0, 236,000, and 700,000 tons a year. Loudoun: 675,455. | Contract new clean supply and report hourly matching. Don't claim the existing hydro. | Medium |
| Tax and state policy | `state_policy_risk` 0. The exemption stands for original equipment in a rural county. A 2026 law ended it for replacement servers. | Servers are replaced every few years, so most of the exemption's 30-year value is gone. A state proceeding on large loads is open. | Model the project without the exemption after the first build. | Medium |
| Power price | `industrial_price_cents_kwh` 6.61, a state average. The PUD is considering a data center rate class for 2027. | A new rate class would raise the $162M annual cost. No number exists yet. | Negotiate the rate with the service agreement. | Medium |
| Cluster record | `dc_existing_count` 3 and `dc_existing_mw` 82 in FracTracker, which undercounts the Quincy cluster. `dc_pushback_count` 0. `fiber_share_locations` 0.99. | An existing cluster means fiber, contractors, and a utility that knows the load. | None needed. | Low |
| Flood, hurricane, tornado | `nri_inland_flood_score` 23.3. `nri_hurricane_score` 0. `nri_tornado_score` 8.7. | Low exposure. | Standard siting above the floodplain. | Low |

## Berkshire County, MA

| Risk | What the data says | Why it matters | Mitigation | Residual |
| --- | --- | --- | --- | --- |
| Power cost | `industrial_price_cents_kwh` 18.19, worse than 97.5%. Energy costs $435M a year against $226M in Loudoun. | $209M a year more than Loudoun to avoid 90,800 tons of CO2. That is about $2,300 per ton. | A negotiated large-load contract or on-site generation. The state average is not the contract rate, but the gap is large. | High |
| State policy | `state_policy_risk` 0 rests on `state_sales_tax_exemption` true. The exemption is law, but the governor paused new applications on 2026-06-25 with no end date. An executive order of 2026-09-08 requires a community benefits agreement before state permits for projects over 25 MW. | With the exemption coded as unavailable, Berkshire falls to rank 2 behind Franklin County, NY. Holyoke banned data centers and Westfield moved toward a moratorium in 2026. | Leave the exemption out of the business case. Start the community benefits agreement first. | High |
| Inland flooding | `nri_inland_flood_score` 90.0, worse than 89.8%. The balanced gate excludes above the 90th percentile. Six counties sit between Berkshire and exclusion. | The county's worst hazard. River valleys hold the flat, serviced land. | Site outside the mapped floodplain, checked parcel by parcel against FEMA flood maps. Raise substations. | Medium |
| Hurricane remnants | `nri_hurricane_score` 76.3, worse than 84%. | Inland wind and rain take down lines and flood rivers. | Two transmission feeds. On-site backup for 48 hours or more. | Medium |
| Fiber and ecosystem | `fiber_share_locations` 0.30, worse than 83%. `dc_existing_count` 0. | No data center has been built here. Long-haul fiber and contractors are unproven. | Commission a fiber route study. Build diverse paths to Albany and Boston. | Medium |
| Grid interconnection | `queue_withdrawal_rate` 0.68, worse than 64%. `queue_median_age_years` 1.7. `plant_capacity_mw_100km` 10,884 MW, 36 times the load. | Two of three queue requests are withdrawn, which points to costly upgrades. | Load study with the utility before land purchase. | Medium |
| Grid carbon | `grid_co2_lb_mwh` 539 is the New England average, not Berkshire's supply. CO2 is 584,653 t a year, 13% under Loudoun. | The saving is small, and the 30-year total assumes today's rate. | Contract clean supply. 3,424 MW of clean capacity sits within 100 km. | Medium |
| Heat and 2050 climate | `nri_heat_wave_score` 70.9, but `days_above_95f_hist` is 0.03, rising to 3.2. `cdd_hist` 259 to 679. `water_stress_bws` 0.44 to 0.62. | Still cooler in 2050 than 92% of counties are today. | Size cooling for 2050. | Low |
| Winter weather | `nri_winter_score` 61.4, worse than 61%. | Ice storms cause outages. | Backup generation and fuel on site. | Low |

## The other ranked counties

- **Worcester, MA (25027).** Worst three: power price (18.19 cents, worse
  than 97.5%), queue withdrawal rate (0.92, worse than 88%), hurricane
  (80.7, worse than 87%). It shares Berkshire's two high risks. With the
  exemption coded as unavailable it falls from rank 6 to 35.
- **New York, ranks 2 to 5.** Executive Order 62 (2026-07-14) tells the
  state environmental agency to hold incomplete permit applications for
  data centers of 50 MW or more until a statewide environmental review is
  done. It has no end date. A 300 MW project can't get a state permit
  until then. The grid is the cleanest of any candidate (242 lb/MWh), so
  these counties are the pick if the order lifts.

## Limits

- County scores are not parcel scores. Flood, wildfire, and fiber need a
  site-level check.
- The policy findings for Massachusetts come from news reports of the
  governor's statement. The state's own pages could not be opened.
- The energy cost uses state average industrial prices. A 300 MW customer
  negotiates its own rate.
- The what-if rank for Massachusetts was run on a copy. The committed table
  still codes the exemption as true.
- Grant PUD's contract commitments for its hydro were not checked.

## Sources

Primary:

- eGRID2023, BA23 sheet: Grant PUD balancing authority (GCPD), 4,131,457
  MWh, 100% hydro, 0 lb CO2/MWh. BPA: 212 lb/MWh.
- RCW 82.08.986 and Chapter 266, Laws of 2026 (ESSB 6231):
  https://app.leg.wa.gov/RCW/default.aspx?cite=82.08.986
- Grant PUD data center FAQ, 2026-08-28:
  https://www.grantpud.org/blog/data-center-faqs
- Massachusetts Chapter 238 of the Acts of 2024:
  https://malegislature.gov/Laws/SessionLaws/Acts/2024/Chapter238
- New York Executive Order 62:
  https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops

Secondary:

- Massachusetts application pause:
  https://www.wbur.org/news/2026/06/26/governor-healey-data-center-tax-incentives
- Massachusetts Executive Order 658:
  https://www.pierceatwood.com/alerts/governor-healey-issues-executive-order-establishing-new-requirements-data-centers
- Holyoke and Westfield: local news, read from search results only.
