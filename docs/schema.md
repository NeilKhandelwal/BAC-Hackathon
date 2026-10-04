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
| `queue_active_mw_clean` | float | LBNL, active and every component of `type_clean` is clean | core | **legacy, not scored** since the queue-semantics correction. Clean here means carbon-free generation or storage: solar, wind, hydro, nuclear, geothermal, battery, other storage. Kept for traceability and as a permitting-model input (`etl/permitting.py`). Scoring uses `queue_active_mw_clean_excl_storage`. |
| `queue_active_mw_clean_excl_storage` | float | LBNL, active, clean-generation components only | stretch, **scored** | clean generation in the queue excluding storage. See "Queue measures" below. |
| `queue_median_age_years` | float | LBNL, active projects, years since `q_date` | core | congestion proxy. Higher is worse. Null when fewer than 3 active projects have a queue date. |
| `queue_withdrawal_rate` | float 0-1 | LBNL, withdrawn / (withdrawn + active + operational), `q_year >= 2019` | core | higher is worse. Null when the denominator is under 3. |
| `queue_operational_mw_5y` | float | LBNL, operational with `q_year >= 2019`, or with no `q_year` and `on_date` in 2021 or later | core | **legacy, not scored**. `q_year` is the year a project entered the queue, so this measures queue entry, not delivery. Scoring uses `queue_operational_mw_online_5y`. |
| `queue_operational_mw_online_5y` | float | LBNL, operational and dated to 2021-2025 by `on_date`, else `prop_date` | stretch, **scored** | delivered or estimated-online capacity. See "Queue measures" below. |
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
| `plant_clean_capacity_mw_100km` | float | eGRID2023 PLNT sheet, `PLFUELCT` is clean | stretch | same radius, by plant primary fuel category. eGRID has no storage category, so this is clean generation only, consistent with the scored queue measure. |
| `industrial_price_cents_kwh` | float | EIA-861 state historical tables, 2024, industrial sector, total electric industry | stretch | state average retail price, the same for every county in a state. Lower is better. Scored as the cost pillar. |
| `saidi_minutes` | float | EIA-861 reliability, customer-weighted | stretch | |
| `dist_ixp_km` | float | PeeringDB, nearest internet exchange | stretch | backbone proxy |

## Land

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `pct_developed` | float 0-1 | NLCD 2021 via IPUMS NHGIS county summaries (`etl/adapters/nlcd_landcover.py`) | stretch | classes 21-24. Built and measured on `fix/sensitive-land`; not in the frozen table. |
| `pct_cropland` | float 0-1 | NLCD 2021 via IPUMS NHGIS | stretch | classes 81 (pasture/hay) and 82 (cultivated crops). Land cover, not soil quality: not the same as prime farmland. Built and measured; not in the frozen table. |
| `pct_cultivated_crops` | float 0-1 | NLCD 2021 via IPUMS NHGIS | stretch | class 82 only; context, not scored |
| `pct_forest_wetland` | float 0-1 | NLCD 2021 via IPUMS NHGIS | stretch | classes 41-43, 90, 95. Scored in the permitting pillar when present. Built and measured; not in the frozen table. |
| `pct_protected` | float 0-1 | USGS PAD-US 4.1 Summary Statistics, county table, GAP 1-2 acres over total county acres (`etl/adapters/pad_us.py`) | stretch | Scored in the land pillar when present (lower is better). Total area includes water, so lake and coastal counties read lower than a land-only share. Built and measured on `fix/sensitive-land`; not in the frozen table (see `docs/sensitive_land_log.md`). |
| `pct_protected_gap1to3` | float 0-1 | same table, GAP 1-3 | stretch | context, not scored. GAP 3 is multiple-use land (most national forest and BLM land). |
| `tribal_land_share` | float 0-1 | Census TIGER/Line 2024 AIANNH, classes D2, D3, D5, D8, unioned and intersected with county polygons in EPSG:5070 (`etl/adapters/tribal_lands.py`) | stretch | context, not scored. Area inside federally recognized reservations and off-reservation trust land; not tribal ownership. Excludes statistical areas such as Oklahoma tribal statistical areas. |

Until the stretch columns land, land availability uses `pop_density_per_sqkm`
and `land_area_sqkm` only. County protected and tribal shares are a screen,
not a siting check: a 150-acre campus can avoid protected land inside a
county, so a parcel-level check belongs in feasibility.

## Community and economics

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `median_household_income` | float | ACS 5-year B19013 | core | also a permitting model feature |
| `heat_sink_score` | float | derived: `hdd_hist * log1p(pop_density_per_sqkm)` | core | v1 heat-reuse proxy |
| `greenhouse_acres` | float | USDA Census of Agriculture 2022 | stretch | real heat-sink input |
| `mfg_emp_share_2001` | float 0-1 | Census CBP 2001, NAICS 31-33 / all industries | stretch | industrial legacy. Permitting model candidate feature. |
| `mfg_loss_share_emp_2001` | float | Census CBP 2001 and 2022 | stretch | (manufacturing jobs 2001 - 2022) / all jobs 2001. Positive means jobs lost. Model candidate. |
| `unemployment_rate_pct_2023` | float 0-100 | BLS LAUS 2023 via USDA ERS | stretch | scored in community, higher better; a stated value choice, not a prediction |
| `pop_change_pct_2010_2024` | float | Census population estimates, Vintage 2020 and 2024 | stretch | unscored; replaced in community by `pop_change_pct_since_peak` |
| `coal_retired_mw` | float | EIA-860 2025, retired coal generators, nameplate MW | stretch | 0 where none. Reusable grid connection proxy, scored in grid and infrastructure. |
| `pop_change_pct_since_peak` | float, <= 0 | Census decennial counts 1950-2020 (Forstall table via NBER mirror, 2000 and 2020 estimates bases) and Vintage 2024 | stretch | July 2024 population against the highest census count since 1950. 0 at peak. Long-run decline. Scored in community, lower better; a stated value choice. |
| `mfg_emp_share_1969` | float 0-1 | BEA CAEMP25S 1969, SIC manufacturing / total employment | stretch | industrial legacy before the Rust Belt collapse. Scored in community, higher better; a stated value choice. |
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

## Context columns (ETL v2)

Context columns ported from the ETL v2 branch. All are **stretch**. Two
are scored since the queue-semantics correction:
`queue_active_mw_clean_excl_storage` and `queue_operational_mw_online_5y`.
The rest aren't mapped in `engine/pillars.yaml` and don't change scores,
gates, or results. Each comes from a separate adapter that reads its own
raw file or main's, and never rewrites a column above. Shares are 0-1;
columns ending `_pct` are 0-100.

### Labor market: BLS LAUS (`etl/adapters/bls_laus.py`)

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `unemployment_rate_pct_2024` | float 0-100 | BLS LAUS `laucnty24.xlsx` | stretch | latest complete year. LAUS 2025 is an 11-month average (October 2025 wasn't collected). `unemployment_rate_pct_2023` stays the scored field. |
| `unemployment_rate_pct_3yr_2022_2024` | float 0-100 | LAUS 2022-2024 | stretch | pooled: 100 x sum(unemployed) / sum(labor force); null unless all three years exist |
| `unemployed_persons_2024` | int | LAUS | stretch | |
| `labor_force_2024` | int | LAUS | stretch | |

### Industrial decline: BLS QCEW (`etl/adapters/bls_qcew.py`)

Private manufacturing: NAICS 31-33, `own_code` 5, county by sector
(`agglvl_code` 74). The share denominator is county private total
employment (`own_code` 5, `agglvl_code` 71). These sit beside the CBP and
BEA manufacturing columns, which stay as they are.

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `mfg_emp_2015`, `mfg_emp_2019`, `mfg_emp_2024`, `mfg_emp_2025` | float | QCEW annual average employment | stretch | **null when suppressed**, never 0. 0 only for a published county with no manufacturing row. 2025 is a first release with about twice the suppression; 2024 is the current year. |
| `mfg_estabs_<year>` | int | QCEW establishments | stretch | published even when employment is suppressed |
| `mfg_emp_suppressed_<year>` | bool | QCEW `disclosure_code == N` | stretch | separates suppressed from unknown |
| `private_emp_2024` | float | QCEW private total | stretch | denominator |
| `mfg_emp_share_2024` | float 0-1 | derived | stretch | |
| `mfg_emp_change_2015_2024`, `mfg_emp_change_2019_2024` | float | derived | stretch | signed jobs |
| `mfg_emp_pct_change_2015_2024` | float, fraction | derived | stretch | null when 2015 employment is 0 or unknown |
| `mfg_jobs_lost_2015_2024` | float | derived | stretch | max(0, 2015 - 2024) |

QCEW 2015 and 2019 use Connecticut's old counties. Job counts aren't split
across planning regions, so CT 2015 and 2019 levels and every change column
are null for CT. Shannon County, SD (46113) is recoded to 46102.

### Rurality and economic structure: USDA ERS (`etl/adapters/usda_ers.py`)

Categorical context, not suitability scores. Economic need, industrial
decline, and community support are different things; none of these says a
community welcomes a data center.

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `rucc_2023` | int 1-9 | Rural-Urban Continuum Codes 2023 | stretch | 1-3 metro, 4-9 nonmetro. OMB July 2023 delineation, 2020 Census population. |
| `rucc_2023_description` | str | same | stretch | |
| `metro_2023` | bool | `rucc_2023 <= 3` | stretch | |
| `ers_high_manufacturing_2025` | bool | County Typology Codes 2025 | stretch | manufacturing at least 25% of earnings or 17% of jobs, BEA 2019/2021/2022 average. Null for CT regions. |
| `ers_high_mining_2025` | bool | same | stretch | mining at least 11% of earnings or 7% of jobs. Null for CT regions. |
| `ers_industry_dependence_2025` | str | same | stretch | nonspecialized, farming, mining, manufacturing, government, recreation. Null for CT regions. |
| `ers_low_employment_2025` | bool | same | stretch | under 63% of residents 25-54 employed, ACS 2018-2022 |
| `ers_population_loss_2025` | bool | same | stretch | population fell 2000-2010 and 2010-2020. Null for CT regions. |

### Brownfields: EPA ACRES (`etl/adapters/epa_brownfields.py`)

Potential reuse sites. Not confirmed available land, not confirmed
data-center suitability.

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `bf_site_count` | int | EPA Cleanups in My Community, brownfield properties deduplicated on ACRES ID | stretch | 0 when the county has none |
| `bf_known_acres` | float | RE-Powering Mapper 2022 or Brownfield Properties Over 100 Acres | stretch | sum of reported acreage. 0 only without sites; **null when sites exist but none report acreage**. |
| `bf_acreage_reporting_share` | float 0-1 | derived | stretch | |
| `bf_sites_50plus_acres` | int | derived | stretch | |
| `bf_ready_for_reuse_count` | int | CIMC `BF_READY_FOR_REUSE_IND == Y` | stretch | |
| `bf_redevelopment_started_count` | int | 100+ acre layer `Redevelopment_Start_Date` | stretch | 0 everywhere: the field was empty at retrieval. "None reported" never means vacant. |

The build also writes `data/processed/brownfield_sites.parquet`, one row per
property with ID, name, coordinates, county, reported acreage and its
source, an `acreage_implausible` flag (over 10,000 acres or over the
county's land area; nulled), funding flags, ready-for-reuse, RE-Powering
grid and rail distances, and `redevelopment_status` (`none_reported` or
`redevelopment_started_reported`). The file is gitignored; rebuild it.

### Hazard, water, climate, and broadband context

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `nri_risk_rating` | str | NRI `RISK_RATNG` | stretch | |
| `nri_eal_score`, `nri_sovi_score`, `nri_resilience_score` | float 0-100 | NRI `EAL_SCORE`, `SOVI_SCORE`, `RESL_SCORE` | stretch | social vulnerability and resilience aren't hazards |
| `nri_<hazard>_annual_freq` | float | NRI `<H>_AFREQ` | stretch | physical frequency: events per year, drought days per year, wildfire annual probability. 0 where NRI rates the hazard Not Applicable. |
| `nri_<hazard>_eal_score` | float 0-100 | NRI `<H>_EALS` | stretch | expected-annual-loss percentile; scales with exposed value |
| `nri_hurricane_not_applicable`, `nri_coastal_flood_not_applicable` | bool | NRI `<H>_RISKR == "Not Applicable"` | stretch | the rule `nri.py` already uses to write 0 |
| `water_stress_bws_cat`, `water_stress_2050_cat` | int -1..4 | Aqueduct `bws_cat`, `bau50_ws_x_c`, category covering most county area | stretch | -1 arid and low water use, 0 low ... 4 extremely high |
| `water_stress_bws_raw_median` | float | Aqueduct `bws_raw`, area-weighted median | stretch | withdrawals / supply; null where the median basin is the 9999 near-zero-supply sentinel |
| `water_stress_high_share`, `water_stress_arid_share` | float 0-1 | Aqueduct | stretch | county area in category 3-4, and in -1 |
| `water_stress_area_coverage` | float 0-1 | Aqueduct | stretch | county area with baseline data |
| `hdd_2050_rcp45`, `days_above_95f_2050_rcp45` | float | CMRA `RCP45MID_MEAN_*` | stretch | same layer and CT rule as `cmra.py` |
| `days_above_100f_hist`, `days_above_100f_2050_rcp45`, `days_above_100f_2050_rcp85` | float | CMRA `*_MEAN_TMAX100F` | stretch | |
| `broadband_served_share_locations` | float 0-1 | Esri FCC layer, `ServedBSLs / TotalBSLs` | stretch | any technology at 100/20 Mbps; last-mile, not backbone |
| `broadband_locations_total` | int | `TotalBSLs` | stretch | null for CT (a count isn't copied onto regions) |

### FracTracker context (`etl/adapters/fractracker_context.py`)

Same raw files and the same facility-to-county matching as
`fractracker.py`, so the facility set equals the one behind
`dc_existing_count`. Main doesn't deduplicate facilities, and neither does
this.

| Column | Type | Source | Tier | Notes |
| --- | --- | --- | --- | --- |
| `dc_existing_mw_reported`, `dc_proposed_mw_reported` | float | FracTracker `mw` | stretch | sum of reported MW only ("10,000" is 10000, "100-200" its midpoint). 0 without facilities; null when none report MW. `dc_existing_mw` keeps main's rule that missing MW counts as 0. |
| `dc_existing_mw_reporting_share`, `dc_proposed_mw_reporting_share` | float 0-1 | derived | stretch | share of facilities reporting MW |
| `dc_stopped_count` | int | status Cancelled or Suspended | stretch | |
| `moratorium_municipal_count`, `moratorium_municipal_pending_count` | int | municipal rows, active or pending, any category | stretch | county subdivisions via GEOID, places via their 2024 internal point. **Never set `moratorium_active`.** |
| `moratorium_state_pending` | bool | state rows, pending, moratorium or ban | stretch | |
| `county_dc_restriction_active` | bool | county rows, active, category other than moratorium or ban | stretch | zoning restriction, curative amendment |

### Queue measures (`etl/adapters/lbnl_queue_alt.py`)

Two of these are the scored queue columns in `energy_carbon`. They replaced
`queue_active_mw_clean` and `queue_operational_mw_5y`, which stay in the
table, unscored, for traceability. None is a gate input. County placement
is the same as `lbnl_queue.py`. The evidence is in
`research/etl_semantics_audit.md`.

| Column | Type | Scored | Notes |
| --- | --- | --- | --- |
| `queue_active_mw_clean_excl_storage` | float | yes | Clean generation in the queue, excluding storage. Sums each clean-generation component's separately reported MW (solar, wind, offshore wind, hydro, geothermal, nuclear) once per project: `mw_1` for `type_1`, `mw_2` for `type_2`, `mw_3` for `type_3`. A component with no reported MW adds 0, so the measure is conservative (233 Solar+Battery rows list only battery capacity). A clean component of a gas or other hybrid counts when its MW is reported. Storage is excluded: it can help integrate renewables, but it isn't clean generation, because its emissions depend on what charges it. National total: 993.2 GW, against 1,420.0 GW for the legacy measure. |
| `queue_active_mw_storage_standalone` | float | no | `mw_1` of active projects whose every component is storage: Battery, Pumped Storage, Storage, or Other Storage. National total: 391.4 GW. |
| `queue_operational_mw_online_5y` | float | yes | Delivered or estimated-online capacity: operational projects dated to 2021-2025 by their actual online date (`on_date`), or by their proposed online date (`prop_date`) only when `on_date` is blank. National total: 152.3 GW from 1,224 projects, against 72.0 GW for the legacy measure. Evidence the queue delivers, not proof of capacity available to a new data center. |
| `queue_operational_projects_online_5y` | int | no | project count behind it |
| `queue_operational_online_date_fallback_share` | float 0-1 | no | uncertainty indicator: share of the county's counted projects dated by `prop_date`. The fallback is substantial where LBNL lacks `on_date`: every operational ISO-NE project and 82% in the West, against under 1% in PJM and ERCOT. Nationally, 214 of the 1,224 projects (22.9 GW) use it. |

## Frozen artifacts and reproducibility

`data/processed/county_features.parquet` and the committed files in
`results/` are the canonical frozen hackathon artifacts. The committed table
keeps main's original 83 columns exactly as they were at `1575003` and
appends 85 context columns. Two of them are scored queue measures (see
"Queue measures"); no gate uses any of them. The queue-semantics
correction updated only `queue_active_mw_clean_excl_storage` and
`queue_active_mw_storage_standalone` in the frozen table, and every other
column kept its frozen value.

A fresh build, online or `--no-fetch`, is semantically reproducible but may
not be byte-identical to the frozen table. Spatial calculations depend on
library versions (geopandas, shapely, rasterio). A rebuild can differ from
the frozen table by less than `1e-12` in `water_stress_bws` and
`water_stress_2050`, and by 0.0005 m/s in `wind_speed_100m_ms` for one county
(18083). Main's own build shows the same differences with or without the
context columns.

Many counties tie exactly on water stress, at 0 or 5. Differences that small
can break those ties, which changes percentile ranks and swaps adjacent
counties outside the leading results. In validation with the corrected
queue measures, a fresh build kept every gate, gate count, winner, top-ten
list, pillar ordering, and core conclusion. It moved 60 counties into
adjacent swaps in `balanced` (best affected rank 273) and swapped one pair
in `speed_to_power` (rank 747), and moved some water pillar scores by up to
0.43 points. Two displayed top-25 values changed by 0.01: Overton County,
TN's water pillar in `speed_to_power` and Monroe County, PA's 2050 shift in
`sustainability_first`.

To reproduce the exact committed rankings, run the engine on the committed
table, not on a rebuilt one:

```bash
python -m engine rank --conditions engine/conditions/balanced.yaml \
  --features data/processed/county_features.parquet --out results/balanced.csv
```

`brownfield_sites.parquet` is a generated artifact and isn't committed.
Running the ETL produces it.

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

Each `sources` entry also carries `adapter`, and the v2 adapters add
`observation_period`, `license`, and `resolution`. `artifacts` lists extra
files adapters wrote (`brownfield_sites.parquet`). `quality_report` points to
`county_features_quality_report.json`, which holds validation checks
(`checks`, `checks_failed`), adapter errors, joins, a profile of every column
(dtype, nulls, min, median, max, zeros), and Connecticut crosswalk limits.

## County name normalization

FracTracker and eGRID plants join on county name. One function,
`etl/fips.py:normalize_county(name, state)`, handles: strip "County",
"Parish", "Borough", "city"; "St." to "Saint"; "De Kalb" to "DeKalb";
Virginia independent cities keep the "city" suffix in TIGER; Connecticut
planning regions. Test it against the TIGER name list and log every
unmatched name rather than dropping silently.
