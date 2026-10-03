# County feature table schema

The contract between the ETL, the engine, and the permitting model. One
row per county in the contiguous US plus DC, about 3,110 rows. Written to `data/processed/county_features.parquet` with a
sidecar `county_features.manifest.json`.

Rules:

- Key is `fips`, a 5-character zero-padded string. Never an integer.
- Every column is a plain number, string, or boolean. No nested values.
- Null means "not available for this county." It never means zero. The
  engine leaves null columns out of the pillar mean and counts them against
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
| `grid_co2_lb_mwh` | float | eGRID2023 SRL sheet `SRCO2RTA`, subregion output emission rate | core | lower is better. Falls back to the state rate if a county has no subregion. |
| `grid_renewable_share` | float 0-1 | eGRID2023 SRL sheet `SRTRPR`, subregion renewable generation share | core | includes hydro |
| `grid_subregion` | str | eGRID2023 subregion shapefile, county internal point | stretch | nearest subregion when the point falls outside every polygon |
| `grid_co2_lb_mwh_state` | float | eGRID2023 ST sheet `STCO2RTA` | stretch | for comparison only; not scored |
| `grid_renewable_share_state` | float 0-1 | eGRID2023 ST sheet `STTRPR` | stretch | for comparison only; not scored |
| `queue_active_mw_total` | float | LBNL Queued Up 2026, `q_status == active` | core | sum of `mw_1` |
| `queue_active_count` | int | LBNL, number of projects with `q_status == active` | stretch | sample size behind the queue statistics |
| `queue_active_mw_clean` | float | LBNL, active and every component of `type_clean` is clean | core | decarbonization signal. Clean means carbon-free generation or storage: solar, wind, hydro, nuclear, geothermal, battery, other storage. |
| `queue_median_age_years` | float | LBNL, active projects, years since `q_date` | core | congestion proxy. Higher is worse. Null when fewer than 3 active projects have a queue date. |
| `queue_withdrawal_rate` | float 0-1 | LBNL, withdrawn / (withdrawn + active + operational), `q_year >= 2019` | core | higher is worse. Null when the denominator is under 3. |
| `queue_operational_mw_5y` | float | LBNL, operational with `q_year >= 2019`, or with no `q_year` and `on_date` in 2021 or later | core | evidence the queue delivers |
| `solar_ghi_kwh_m2_day` | float | NREL NSRDB annual raster, zonal mean | stretch | |
| `wind_speed_100m_ms` | float | NREL WIND Toolkit 100 m raster, zonal mean | stretch | source is already m/s |

## Water

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `drought_share_weeks_d2plus` | float 0-1 | US Drought Monitor 2000-2025, cumulative `D2` | core | area-weighted share of weeks |
| `nri_drought_score` | float 0-100 | FEMA NRI `DRGT_ALR_NPCTL` | core | loss-rate percentile; see the note under climate resilience |
| `water_stress_bws` | float 0-5 | WRI Aqueduct 4.0 `bws_score`, area-weighted in EPSG:5070 | stretch | gate input for evaporative cooling. The 0-5 category scale, not `bws_raw`, which is a withdrawal ratio: 0-1 low, 1-2 low-medium, 2-3 medium-high, 3-4 high, 4-5 extremely high. Arid, low-water-use basins score 5. |
| `water_stress_2050` | float 0-5 | Aqueduct 4.0 future `bau50_ws_x_s`, 2050 business as usual, area-weighted | stretch | same scale as `water_stress_bws` |
| `grid_water_gal_mwh` | float | EIA-923 8D + EIA-860, by eGRID subregion | stretch | water embedded in grid power |

## Climate resilience

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `nri_risk_score` | float 0-100 | FEMA NRI `RISK_SCORE` | core | composite, dollar-loss based. Not scored. |
| `nri_inland_flood_score` | float 0-100 | NRI `IFLD_ALR_NPCTL` | core | v1.20 name; was RFLD |
| `nri_coastal_flood_score` | float 0-100 | NRI `CFLD_ALR_NPCTL` | core | |
| `nri_wildfire_score` | float 0-100 | NRI `WFIR_ALR_NPCTL` | core | |
| `nri_hurricane_score` | float 0-100 | NRI `HRCN_ALR_NPCTL` | core | |
| `nri_heat_wave_score` | float 0-100 | NRI `HWAV_ALR_NPCTL` | core | |
| `nri_tornado_score` | float 0-100 | NRI `TRND_ALR_NPCTL` | core | |
| `nri_winter_score` | float 0-100 | NRI `WNTW_ALR_NPCTL` | core | |
| `nri_<hazard>_risks` | float 0-100 | NRI `<HAZARD>_RISKS` | stretch | the eight hazard columns as dollar-loss risk scores, such as `nri_inland_flood_risks`. For comparison only; not scored. |
| `cdd_hist` | float | CMRA `HISTORIC_MEAN_CDD` | core | cooling degree days, base 65F |
| `cdd_2050_rcp45` | float | CMRA `RCP45MID_MEAN_CDD` | core | |
| `cdd_2050_rcp85` | float | CMRA `RCP85MID_MEAN_CDD` | core | |
| `hdd_hist` | float | CMRA `HISTORIC_MEAN_HDD` | core | heating degree days; heat-reuse input |
| `hdd_2050_rcp85` | float | CMRA `RCP85MID_MEAN_HDD` | core | |
| `days_above_95f_hist` | float | CMRA `HISTORIC_MEAN_TMAX95F` | core | |
| `days_above_95f_2050_rcp85` | float | CMRA `RCP85MID_MEAN_TMAX95F` | core | |

The `nri_*_score` hazard columns are national percentiles of the expected
annual loss rate, which is loss divided by exposure. The NRI risk scores
(`*_RISKS`) track dollar losses, so they rate populous counties as hazardous
because there is more to lose.

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
| `plant_capacity_mw_100km` | float | eGRID2023 PLNT sheet `NAMEPCAP`, `LAT`, `LON` | stretch | nameplate MW of power plants within 100 km (great circle) of the county internal point. A naive check that the nearby grid can carry the facility. |
| `plant_clean_capacity_mw_100km` | float | eGRID2023 PLNT sheet, `PLFUELCT` is clean | stretch | same radius, by plant primary fuel category. Same definition of clean as `queue_active_mw_clean`; eGRID has no storage category. |
| `industrial_price_cents_kwh` | float | EIA-861 state historical tables, 2024, industrial sector, total electric industry | stretch | state average retail price, the same for every county in a state. Lower is better. |
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
| `mfg_emp_share_2001` | float 0-1 | Census CBP 2001, NAICS 31-33 / all industries | stretch | industrial legacy. Permitting model candidate feature. |
| `mfg_loss_share_emp_2001` | float | Census CBP 2001 and 2022 | stretch | (manufacturing jobs 2001 - 2022) / all jobs 2001. Positive means jobs lost. Model candidate. |
| `unemployment_rate_pct_2023` | float 0-100 | BLS LAUS 2023 via USDA ERS | stretch | scored in community, higher better; a stated value choice, not a prediction |
| `pop_change_pct_2010_2024` | float | Census population estimates, Vintage 2020 and 2024 | stretch | scored in community, lower better; a stated value choice, not a prediction |
| `coal_retired_mw` | float | EIA-860 2025, retired coal generators, nameplate MW | stretch | 0 where none. Reusable grid connection proxy, scored in grid and infrastructure. |
| `pop_change_pct_since_peak` | float, <= 0 | Census decennial counts 1950-2020 (Forstall table via NBER mirror, 2000 and 2020 estimates bases) and Vintage 2024 | stretch | July 2024 population against the highest census count since 1950. 0 at peak. Long-run decline. |
| `mfg_emp_share_1969` | float 0-1 | BEA CAEMP25S 1969, SIC manufacturing / total employment | stretch | industrial legacy before the Rust Belt collapse |
| `mfg_emp_share_change_1969_2022` | float | BEA CAEMP25S 1969 and CAEMP25N 2022 | stretch | 2022 share minus 1969 share. Negative means manufacturing shrank. Null where BEA withholds either year. |
| `energy_community_coal_closure` | bool | DOE/NETL IRA energy communities 2024, coal closure tracts | stretch | a tract in the county had a coal mine closure or coal generator retirement. Adjoining-only tracts excluded. |
| `energy_community_ffe` | bool | DOE/NETL IRA energy communities 2024, MSA and non-MSA layer | stretch | county's MSA or non-MSA meets the fossil fuel employment and unemployment tests |

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
| `permitting_discretionary_risk` | float 0-1 | permitting model | core | null: model tested and dropped, see `research/permitting_model.md` |
| `permitting_drivers` | str | permitting model | core | null: model tested and dropped, see `research/permitting_model.md` |
| `air_nonattainment_count` | int 0-2 | EPA Green Book, county in nonattainment for 8-hour ozone, PM2.5 | core | constrains diesel backup generation |
| `water_rights_regime` | str | hand-coded state table | core | `prior_appropriation`, `riparian`, or `hybrid` |
| `groundwater_managed_area` | bool | hand-coded: Arizona AMAs and equivalent state designations | core | researched for AZ, TX, CO. Null in other prior-appropriation and hybrid states. |
| `water_permit_risk` | int 0-2 | derived: 0 riparian, 1 hybrid or prior appropriation, 2 if also a managed groundwater area | core | |
| `state_dc_bill_pending` | bool | hand-coded from NCSL and FracTracker state layer | core | moratorium or restriction bill filed in the current session |
| `state_sales_tax_exemption` | bool | hand-coded state table | core | data center equipment exemption in force. States with no general sales tax (DE, MT, NH, OR) count as exempt. |
| `state_large_load_tariff` | bool | hand-coded state table | core | utility large-load tariff with minimum bills in force |
| `state_policy_risk` | int 0-3 | derived: bill pending + no exemption + tariff | core | |
| `pct_forest_wetland` | float 0-1 | NLCD | stretch | wetland and habitat permit exposure; listed under Land as well |
| `permitting_pathway` | str | derived by the engine, not the ETL | n/a | see `docs/permitting.md` |

## Coverage

| Column | Type | Notes |
| --- | --- | --- |
| `coverage` | float 0-1 | share of all columns mapped in `engine/pillars.yaml` that are non-null for this county, counting columns absent from the table as null. Computed by the engine, not the ETL. |

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
