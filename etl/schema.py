"""Column list for the county feature table. Mirrors docs/schema.md; change that file first."""

# column -> pandas dtype. Nullable dtypes so that null never has to be written as zero.
CORE = {
    # identity
    "fips": "string", "county_name": "string", "state": "string", "state_fips": "string",
    "population": "Int64", "land_area_sqkm": "float64", "pop_density_per_sqkm": "float64",
    "centroid_lat": "float64", "centroid_lon": "float64",
    # energy and carbon
    "grid_co2_lb_mwh": "float64", "grid_renewable_share": "float64",
    "queue_active_mw_total": "float64", "queue_active_mw_clean": "float64",
    "queue_median_age_years": "float64", "queue_withdrawal_rate": "float64",
    "queue_operational_mw_5y": "float64",
    # water
    "drought_share_weeks_d2plus": "float64", "nri_drought_score": "float64",
    # climate resilience
    "nri_risk_score": "float64", "nri_inland_flood_score": "float64",
    "nri_coastal_flood_score": "float64", "nri_wildfire_score": "float64",
    "nri_hurricane_score": "float64", "nri_heat_wave_score": "float64",
    "nri_tornado_score": "float64", "nri_winter_score": "float64",
    "cdd_hist": "float64", "cdd_2050_rcp45": "float64", "cdd_2050_rcp85": "float64",
    "hdd_hist": "float64", "hdd_2050_rcp85": "float64",
    "days_above_95f_hist": "float64", "days_above_95f_2050_rcp85": "float64",
    # grid and infrastructure
    "fiber_share_locations": "float64", "dc_existing_count": "Int64", "dc_existing_mw": "float64",
    "dc_proposed_count": "Int64", "dc_proposed_mw": "float64",
    # community
    "median_household_income": "float64", "heat_sink_score": "float64",
    # permitting
    "dc_pushback_count": "Int64", "dc_pushback_any": "boolean",
    "moratorium_active": "boolean", "moratorium_pending": "boolean",
    "moratorium_state_active": "boolean",
    "permitting_discretionary_risk": "float64", "permitting_drivers": "string",
    "air_nonattainment_count": "Int64", "water_rights_regime": "string",
    "groundwater_managed_area": "boolean", "water_permit_risk": "Int64",
    "state_dc_bill_pending": "boolean", "state_sales_tax_exemption": "boolean",
    "state_large_load_tariff": "boolean", "state_policy_risk": "Int64",
}

# Carbon-free generation or storage. One definition for queue projects and existing plants.
CLEAN_SOURCES = {"solar", "wind", "offshore wind", "hydro", "nuclear", "geothermal", "battery",
                 "other storage"}

STRETCH = {
    "queue_active_count": "Int64",
    "nri_drought_risks": "float64", "nri_inland_flood_risks": "float64",
    "nri_coastal_flood_risks": "float64", "nri_wildfire_risks": "float64",
    "nri_hurricane_risks": "float64", "nri_heat_wave_risks": "float64",
    "nri_tornado_risks": "float64", "nri_winter_risks": "float64",
    "grid_subregion": "string", "grid_co2_lb_mwh_state": "float64",
    "grid_renewable_share_state": "float64", "solar_ghi_kwh_m2_day": "float64", "wind_speed_100m_ms": "float64",
    "water_stress_bws": "float64", "water_stress_2050": "float64", "grid_water_gal_mwh": "float64",
    "plant_capacity_mw_100km": "float64", "plant_clean_capacity_mw_100km": "float64",
    "industrial_price_cents_kwh": "float64",
    "saidi_minutes": "float64", "dist_ixp_km": "float64",
    "pct_developed": "float64", "pct_cropland": "float64", "pct_forest_wetland": "float64",
    "pct_protected": "float64", "greenhouse_acres": "float64",
    "mfg_emp_share_2001": "float64", "mfg_loss_share_emp_2001": "float64",
    "unemployment_rate_pct_2023": "float64", "pop_change_pct_2010_2024": "float64",
    "coal_retired_mw": "float64",
    "pop_change_pct_since_peak": "float64", "mfg_emp_share_1969": "float64",
    "mfg_emp_share_change_1969_2022": "float64",
    "energy_community_coal_closure": "boolean", "energy_community_ffe": "boolean",
    # Context columns from the ETL v2 port. Only the two queue measures noted below are scored.
    # BLS LAUS
    "unemployment_rate_pct_2024": "float64", "unemployment_rate_pct_3yr_2022_2024": "float64",
    "unemployed_persons_2024": "Int64", "labor_force_2024": "Int64",
    # BLS QCEW private manufacturing
    "mfg_emp_2015": "float64", "mfg_emp_2019": "float64", "mfg_emp_2024": "float64", "mfg_emp_2025": "float64",
    "mfg_estabs_2015": "Int64", "mfg_estabs_2019": "Int64", "mfg_estabs_2024": "Int64", "mfg_estabs_2025": "Int64",
    "mfg_emp_suppressed_2015": "boolean", "mfg_emp_suppressed_2019": "boolean",
    "mfg_emp_suppressed_2024": "boolean", "mfg_emp_suppressed_2025": "boolean",
    "private_emp_2024": "float64", "mfg_emp_share_2024": "float64", "mfg_emp_change_2015_2024": "float64",
    "mfg_emp_pct_change_2015_2024": "float64", "mfg_jobs_lost_2015_2024": "float64",
    "mfg_emp_change_2019_2024": "float64",
    # USDA ERS
    "rucc_2023": "Int64", "rucc_2023_description": "string", "metro_2023": "boolean",
    "ers_high_manufacturing_2025": "boolean", "ers_high_mining_2025": "boolean",
    "ers_low_employment_2025": "boolean", "ers_population_loss_2025": "boolean",
    "ers_industry_dependence_2025": "string",
    # EPA brownfields
    "bf_site_count": "Int64", "bf_known_acres": "float64", "bf_acreage_reporting_share": "float64",
    "bf_sites_50plus_acres": "Int64", "bf_ready_for_reuse_count": "Int64",
    "bf_redevelopment_started_count": "Int64",
    # FEMA NRI context
    "nri_risk_rating": "string", "nri_eal_score": "float64", "nri_sovi_score": "float64",
    "nri_resilience_score": "float64",
    **{f"nri_{h}_{k}": "float64" for h in ("drought", "heat_wave", "wildfire", "hurricane", "coastal_flood",
                                            "inland_flood", "tornado", "winter")
       for k in ("annual_freq", "eal_score")},
    "nri_hurricane_not_applicable": "boolean", "nri_coastal_flood_not_applicable": "boolean",
    # Aqueduct context
    "water_stress_bws_raw_median": "float64", "water_stress_bws_cat": "Int64",
    "water_stress_high_share": "float64", "water_stress_arid_share": "float64",
    "water_stress_area_coverage": "float64", "water_stress_2050_cat": "Int64",
    # CMRA context
    "hdd_2050_rcp45": "float64", "days_above_95f_2050_rcp45": "float64", "days_above_100f_hist": "float64",
    "days_above_100f_2050_rcp45": "float64", "days_above_100f_2050_rcp85": "float64",
    # FCC context
    "broadband_served_share_locations": "float64", "broadband_locations_total": "Int64",
    # FracTracker context
    "moratorium_municipal_count": "Int64", "moratorium_municipal_pending_count": "Int64",
    "moratorium_state_pending": "boolean", "county_dc_restriction_active": "boolean",
    "dc_existing_mw_reported": "float64", "dc_existing_mw_reporting_share": "float64",
    "dc_proposed_mw_reported": "float64", "dc_proposed_mw_reporting_share": "float64",
    "dc_stopped_count": "Int64",
    # LBNL queue measures. queue_active_mw_clean_excl_storage and queue_operational_mw_online_5y are
    # scored in energy_carbon; the legacy queue_active_mw_clean and queue_operational_mw_5y stay in CORE,
    # unscored, for traceability. None is a gate input.
    "queue_active_mw_clean_excl_storage": "float64", "queue_active_mw_storage_standalone": "float64",
    "queue_operational_mw_online_5y": "float64", "queue_operational_projects_online_5y": "Int64",
    "queue_operational_online_date_fallback_share": "float64",
}

# STRETCH columns added by the ETL v2 port; the quality report and tests check them.
# Of these, only SCORED_V2 appear in engine/pillars.yaml.
V2_CONTEXT = list(STRETCH)[list(STRETCH).index("unemployment_rate_pct_2024"):]
SCORED_V2 = ["queue_active_mw_clean_excl_storage", "queue_operational_mw_online_5y"]
