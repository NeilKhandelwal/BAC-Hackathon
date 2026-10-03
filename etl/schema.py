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
}
