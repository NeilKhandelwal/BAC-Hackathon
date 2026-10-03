# County feature table schema

The contract between the ETL, the engine, and the permitting model. One
row per county in the contiguous US plus DC, about 3,110 rows. Written to `data/processed/county_features.parquet` with a
sidecar `county_features.manifest.json`.

Rules:

- Key is `fips`, a 5-character zero-padded string. Never an integer.
- Every column is a plain number, string, or boolean. No nested values.
- Null means "not available for this county." It never means zero. The
  engine treats null as pillar-neutral (median percentile) and counts it in
  `coverage`. A gate never fails on null; it flags instead.
- Units are in the column name where they matter.
- Columns marked **core** must exist in the first delivery, even if some
  values are null. Columns marked **stretch** may be absent; the engine
  checks for them.
- Add a column by adding a row here first, then to `engine/pillars.yaml` if
  it's scored.

## Identity

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `fips` | str(5) | Census TIGER | core | primary key |
| `county_name` | str | Census TIGER | core | NAME field |
| `state` | str(2) | Census TIGER | core | USPS abbreviation |
| `state_fips` | str(2) | Census TIGER | core | |
| `population` | int | ACS 5-year B01003 | core | |
| `land_area_sqkm` | float | Census TIGER ALAND / 1e6 | core | |
| `pop_density_per_sqkm` | float | derived | core | population / land_area_sqkm |
| `centroid_lat` | float | Census TIGER | core | internal point |
| `centroid_lon` | float | Census TIGER | core | internal point |

## Energy and carbon

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `grid_co2_lb_mwh` | float | eGRID2023 ST sheet, state output emission rate | core | lower is better. State-level until the subregion join lands. |
| `grid_renewable_share` | float 0-1 | eGRID2023 ST sheet, renewable generation share | core | includes hydro. Confirm the exact field in the workbook; names changed between editions. |
| `grid_subregion` | str | eGRID subregion shapefile | stretch | replaces state-level rates when available |
| `queue_active_mw_total` | float | LBNL Queued Up 2026, `q_status == active` | core | sum of `mw_1` |
| `queue_active_mw_clean` | float | LBNL, active and `type_clean` in solar, wind, storage, hybrid | core | decarbonization signal |
| `queue_median_age_years` | float | LBNL, active projects, years since `q_date` | core | congestion proxy. Higher is worse. |
| `queue_withdrawal_rate` | float 0-1 | LBNL, withdrawn / (withdrawn + active + operational), `q_year >= 2019` | core | higher is worse |
| `queue_operational_mw_5y` | float | LBNL, operational with `q_year >= 2019` | core | evidence the queue delivers |
| `solar_ghi_kwh_m2_day` | float | NREL NSRDB annual raster, zonal mean | stretch | |
| `wind_speed_100m_ms` | float | NREL WIND Toolkit 100 m raster, zonal mean | stretch | km/h in source, convert |

## Water

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `drought_share_weeks_d2plus` | float 0-1 | US Drought Monitor 2000-2025, cumulative `D2` | core | area-weighted share of weeks |
| `nri_drought_score` | float 0-100 | FEMA NRI `DRGT_RISKS` | core | |
| `water_stress_bws` | float 0-5 | WRI Aqueduct 4.0 `bws_raw`, area-weighted | stretch | gate input for evaporative cooling |
| `water_stress_2050` | float 0-5 | Aqueduct 4.0 future, 2050 business-as-usual | stretch | |
| `grid_water_gal_mwh` | float | EIA-923 8D + EIA-860, by eGRID subregion | stretch | water embedded in grid power |

## Climate resilience

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `nri_risk_score` | float 0-100 | FEMA NRI `RISK_SCORE` | core | composite |
| `nri_inland_flood_score` | float 0-100 | NRI `IFLD_RISKS` | core | v1.20 name; was RFLD |
| `nri_coastal_flood_score` | float 0-100 | NRI `CFLD_RISKS` | core | |
| `nri_wildfire_score` | float 0-100 | NRI `WFIR_RISKS` | core | |
| `nri_hurricane_score` | float 0-100 | NRI `HRCN_RISKS` | core | |
| `nri_heat_wave_score` | float 0-100 | NRI `HWAV_RISKS` | core | |
| `nri_tornado_score` | float 0-100 | NRI `TRND_RISKS` | core | |
| `nri_winter_score` | float 0-100 | NRI `WNTW_RISKS` | core | |
| `cdd_hist` | float | CMRA `HISTORIC_MEAN_CDD` | core | cooling degree days, base 65F |
| `cdd_2050_rcp45` | float | CMRA `RCP45MID_MEAN_CDD` | core | |
| `cdd_2050_rcp85` | float | CMRA `RCP85MID_MEAN_CDD` | core | |
| `hdd_hist` | float | CMRA `HISTORIC_MEAN_HDD` | core | heating degree days; heat-reuse input |
| `hdd_2050_rcp85` | float | CMRA `RCP85MID_MEAN_HDD` | core | |
| `days_above_95f_hist` | float | CMRA `HISTORIC_MEAN_TMAX95F` | core | |
| `days_above_95f_2050_rcp85` | float | CMRA `RCP85MID_MEAN_TMAX95F` | core | |

NRI hazard scores are the one exception to "null never means zero." Where NRI
rates a hazard "Not Applicable" for a county, such as coastal flooding
inland, the ETL writes 0. "Insufficient Data" stays null.

## Grid and infrastructure

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `fiber_share_locations` | float 0-1 | Esri FCC county layer, `ServedBSLsFiber / TotalBSLs` | core | last-mile proxy |
| `dc_existing_count` | int | FracTracker, status in Operating, Expanding | core | |
| `dc_existing_mw` | float | FracTracker, same filter, sum `mw` | core | nulls in source treated as 0 for the sum |
| `dc_proposed_count` | int | FracTracker, status in Proposed, Approved, Pre-proposal | core | |
| `dc_proposed_mw` | float | FracTracker, same filter | core | |
| `saidi_minutes` | float | EIA-861 reliability, customer-weighted | stretch | |
| `dist_ixp_km` | float | PeeringDB, nearest internet exchange | stretch | backbone proxy |

## Land

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `pct_developed` | float 0-1 | NLCD 2021 via NHGIS, or NLCD 2024 zonal | stretch | classes 21-24 |
| `pct_cropland` | float 0-1 | NLCD | stretch | classes 81-82 |
| `pct_forest_wetland` | float 0-1 | NLCD | stretch | classes 41-43, 90, 95 |
| `pct_protected` | float 0-1 | USGS PAD-US GAP 1-2 | stretch | sensitive-area gate |

Until the stretch columns land, land availability uses `pop_density_per_sqkm`
and `land_area_sqkm` only.

## Community and economics

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `median_household_income` | float | ACS 5-year B19013 | core | also a permitting model feature |
| `heat_sink_score` | float | derived: `hdd_hist * log1p(pop_density_per_sqkm)` | core | v1 heat-reuse proxy |
| `greenhouse_acres` | float | USDA Census of Agriculture 2022 | stretch | real heat-sink input |

## Permitting

Method is in `docs/permitting.md`. Power interconnection is not repeated
here; it's scored in grid and infrastructure.

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `dc_pushback_count` | int | FracTracker, `community_pushback == Yes` | core | label input only; not scored, to avoid double counting with the model |
| `dc_pushback_any` | bool | derived | core | label input only |
| `moratorium_active` | bool | FracTracker moratoria, county level, status active | core | by GEOID; gate |
| `moratorium_pending` | bool | FracTracker moratoria, county level, status pending | core | |
| `moratorium_state_active` | bool | FracTracker moratoria, state level | core | broadcast to all counties in the state |
| `permitting_discretionary_risk` | float 0-1 | permitting model | core | probability a project meets opposition that delays or kills it. Null until the model runs. |
| `permitting_drivers` | str | permitting model | core | top three features by contribution, semicolon list |
| `air_nonattainment_count` | int 0-2 | EPA Green Book, county in nonattainment for 8-hour ozone, PM2.5 | core | constrains diesel backup generation |
| `water_rights_regime` | str | hand-coded state table | core | `prior_appropriation`, `riparian`, or `hybrid` |
| `groundwater_managed_area` | bool | hand-coded: Arizona AMAs and equivalent state designations | core | |
| `water_permit_risk` | int 0-2 | derived: 0 riparian, 1 hybrid or prior appropriation, 2 if also a managed groundwater area | core | |
| `state_dc_bill_pending` | bool | hand-coded from NCSL and FracTracker state layer | core | moratorium or restriction bill filed in the current session |
| `state_sales_tax_exemption` | bool | hand-coded state table | core | data center equipment exemption in force |
| `state_large_load_tariff` | bool | hand-coded state table | core | utility large-load tariff with minimum bills in force |
| `state_policy_risk` | int 0-3 | derived: bill pending + no exemption + tariff | core | |
| `pct_forest_wetland` | float 0-1 | NLCD | stretch | wetland and habitat permit exposure; listed under Land as well |
| `permitting_pathway` | str | derived by the engine, not the ETL | n/a | see `docs/permitting.md` |

## Coverage

| Column | Type | Notes |
| --- | --- | --- |
| `coverage` | float 0-1 | share of core scored columns that are non-null for this county. Computed by the engine, not the ETL. |

## Manifest

`county_features.manifest.json`:

```json
{
  "built_at": "2026-10-03T18:00:00Z",
  "rows": 3109,
  "sources": [
    {"name": "FEMA NRI", "version": "v1.20", "url": "...", "fetched_at": "..."},
    {"name": "LBNL Queued Up", "version": "2026, through 2025", "url": "...", "fetched_at": "..."}
  ],
  "columns_present": ["fips", "..."],
  "columns_missing": ["solar_ghi_kwh_m2_day", "..."]
}
```

The engine reads `columns_missing` and drops those metrics from scoring with
a warning, so a partial table still runs.

## County name normalization

FracTracker and eGRID plants join on county name. One function,
`etl/fips.py:normalize_county(name, state)`, handles: strip "County",
"Parish", "Borough", "city"; "St." to "Saint"; "De Kalb" to "DeKalb";
Virginia independent cities keep the "city" suffix in TIGER; Connecticut
planning regions. Test it against the TIGER name list and log every
unmatched name rather than dropping silently.
