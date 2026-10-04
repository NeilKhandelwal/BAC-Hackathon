# Data inventory

Scope: contiguous US plus DC, county (FIPS) as the unit of analysis. Every
layer below ends up as one or more columns in a single county table.

Verification status: direct URLs below returned HTTP 200 from the sandbox on
2026-10-03 unless marked otherwise. Sizes are from Content-Length. Three
hosts block this sandbox's IP and still need a laptop check: `www.fema.gov`
(the NRI ZIP), `broadbandmap.fcc.gov`, and `emp.lbl.gov`. Workarounds are
listed for each. No dataset needs payment. Registrations: FCC (if you use
the FCC site rather than the Esri mirror), Global Energy Monitor, IPUMS
NHGIS (optional NLCD county summaries).

## Priority tiers

Tier 1 builds the minimum viable county table. Tier 2 adds the layers that
make the systems-thinking story. Tier 3 is only if time allows.

| Tier | Dataset | Columns it produces |
| --- | --- | --- |
| 1 | Census TIGER county boundaries + population | geometry, population, the join key for everything else |
| 1 | FEMA National Risk Index | flood, wildfire, hurricane, drought, heat wave, tornado, winter weather scores |
| 1 | EPA eGRID | grid carbon intensity (lb CO2/MWh), fuel mix, renewable share |
| 1 | NREL solar and wind annual rasters | mean GHI, mean 100 m wind speed |
| 1 | NOAA Climate Normals | heating and cooling degree days, days above 90F and 100F |
| 1 | WRI Aqueduct 4.0 | baseline water stress, 2050 projected stress |
| 1 | LBNL Queued Up | MW in queue by fuel and status, queue age, withdrawal rate |
| 1 | FracTracker data center tracker | existing and proposed facility count and MW, pushback flag, moratorium flags |
| 1 | CMRA climate projections | 2050 cooling degree days, days above 95F |
| 2 | EIA-861 | SAIDI and SAIFI reliability, utility service territory |
| 2 | EIA-923 Schedule 8D + EIA-860 | grid water withdrawal per MWh by subregion |
| 2 | FCC broadband (Esri county layer) | percent of locations with fiber |
| 2 | US Drought Monitor | percent of weeks in D2 or worse since 2000 |
| 2 | GDELT | local news volume and tone on data centers (see gdelt_feasibility.md) |
| 2 | USGS Annual NLCD | percent developed, cropland, forest, impervious |
| 3 | IBTrACS | hurricane track passes within 100 km |
| 3 | GEM steel and cement trackers | distance to nearest low-carbon mill or plant |
| 3 | FEMA NFHL | percent area in special flood hazard area |
| 3 | USFS Wildfire Risk to Communities | redundant with NRI wildfire |

Dropped from the brief's list: Freight Analysis Framework, Clean Watersheds
Needs Survey, Building Transparency, Bloom Energy. None adds a column worth
the ingestion time. Treat fuel cells as a scenario toggle in the UI.

## Dataset details

### 1. Census TIGER/Line counties and population

- Boundaries: `https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip`
  (11.6 MB, verified). The full-resolution TIGER file is at
  `https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip`.
- Population: ACS 5-year via
  `https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E&for=county:*`.
  No key needed under 500 requests per day.
- Unit: county. GEOID is the 5-digit FIPS.
- Gotchas: filter STATEFP to the 48 states plus DC. Connecticut uses planning
  regions instead of counties since 2022. Pick one convention and apply it to
  every name-based join.

### 2. FEMA National Risk Index (NRI)

- The NRI moved into FEMA's Resilience Analysis and Planning Tool. Old
  `hazards.fema.gov/nri` links redirect there.
- Verified access: ArcGIS feature service, 3,232 county rows in pages of
  2,000.
  `https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=json`
- Official ZIP (blocked from the sandbox, try from a laptop):
  `https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Counties.zip`
- Data dictionary (61 KB CSV, verified):
  `https://fema.maps.arcgis.com/sharing/rest/content/items/4b9db412e99542029b3c37c37ad714bb/data`
- Version: v1.20, December 2025.
- Key: `STCOFIPS`. Scores: `RISK_SCORE`, `DRGT_RISKS`, `HWAV_RISKS`,
  `WFIR_RISKS`, `HRCN_RISKS`, `CFLD_RISKS`, `IFLD_RISKS`, `TRND_RISKS`,
  `WNTW_RISKS`.
- Gotchas: riverine flooding (`RFLD_*`) was replaced by inland flooding
  (`IFLD_*`) in v1.20. Scores are relative percentiles. Expected annual loss
  in dollars scales with what's there to lose, so empty counties look safe.
  Use the hazard frequency and exposure fields, not only the dollar loss.

### 3. EPA eGRID

- Current edition: eGRID2023 Rev 2, June 2025. The page was updated in
  September 2026 and does not mention eGRID2024.
- Data: `https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx`
  (21.2 MB, verified). Sheets: UNT, GEN, PLNT, ST, BA, SRL, NRL, US.
- Subregion shapefile:
  `https://www.epa.gov/system/files/other-files/2025-01/egrid2023_subregions.zip`
  (57.3 MB, verified).
- County mapping: spatial join county centroid to the subregion shapefile
  and pull the SRL emission rate. For plant-level work, PLNT has lat/lon and
  county name.
- Gotchas: eGRID has no water-use fields. Water comes from EIA-923. The
  subregion rate is an annual average, not a marginal rate. Say so in the
  methods slide.

### 4. NREL solar and wind annual rasters

- NREL's web presence moved to `nlr.gov`. The `nrel.gov` hosts fail.
- Solar: `https://www.nlr.gov/docs/libraries/gis/nsrdbv3_ghi.zip` (140 MB,
  verified). Contains `Annual GHI/nsrdb3_ghi.tif` plus 12 monthly TIFs.
  4 km grid, 1998 to 2016 average.
- Wind: `https://www.nlr.gov/docs/libraries/gis/us-wind-data.zip` (185 MB,
  verified). Contains `us-wind-data/wtk_conus_100m_mean_masked.tif` and
  other hub heights from 10 to 200 m. 2 km grid.
- County mapping: zonal mean over county polygons.
- Gotchas: both zips are large. You can pull a single TIF out of a remote
  zip with HTTP range requests; the scratch scripts `ziplist.py` and
  `zipget.py` did this during verification and are worth recreating in
  `etl/`. The ScienceBase items in the brief are metadata only with binned
  quantile data. Don't use them. Avoid the NSRDB API: it needs a key and
  returns hourly point data.

### 5. NOAA U.S. Climate Normals 1991 to 2020

- Annual and seasonal, per station:
  `https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/`
  (about 15,600 CSVs, about 77 KB each, verified).
- Bulk tarball (54.2 MB, verified):
  `https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/archive/us-climate-normals_1991-2020_v1.0.1_annualseasonal_multivariate_by-station_c20230404.tar.gz`
- Hourly, per station: `https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/`.
  Hourly tarball is 232 MB and covers only a few hundred ASOS stations.
- Columns are uppercase: `ANN-HTDD-NORMAL`, `ANN-CLDD-NORMAL`,
  `ANN-TMAX-AVGNDS-GRTH090`, `ANN-TMAX-AVGNDS-GRTH100`. Des Moines reads
  6,178 heating and 1,070 cooling degree days.
- County mapping: spatial join station to county, then average. Many
  counties have no station, so fall back to inverse-distance weighting from
  the nearest three.
- Gotchas: wet-bulb temperature is not provided. Compute it from the hourly
  temperature and dew point if you want a free-cooling-hours metric. That
  number drives the cooling story, so it's worth the effort for finalist
  counties at least.

### 6. WRI Aqueduct 4.0

- Download: `https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip`
  (261.5 MB, verified). Contains baseline annual, monthly, and future CSVs
  plus a file geodatabase `GDB/Aq40_Y2023D07M05.gdb`. No GeoPackage.
- The baseline annual CSV is 202 MB uncompressed and has no geometry. Join
  it to the geodatabase polygons on `pfaf_id` or read the geodatabase
  directly with geopandas.
- Unit: HydroBASINS level 6 sub-basin.
- County mapping: area-weighted overlay of `bws_raw` and `bws_cat` (baseline
  water stress) onto county polygons. The future file gives 2030, 2050, and
  2080 under three scenarios, which covers the 2050 horizon for water.
- Also on Google Earth Engine as `WRI/Aqueduct_Water_Risk/V4`.

### 7. LBNL Queued Up

- 2026 edition, queues through end of 2025 (15.6 MB, verified):
  `https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx`
- 2025 edition (14.1 MB, verified):
  `https://eta-publications.lbl.gov/sites/default/files/2025-08/lbnl_ix_queue_data_file_thru2024_v2.xlsx`
- `emp.lbl.gov` blocks the sandbox. Use the `eta-publications` host.
- Sheet: `03. Complete Queue Data`, 38,201 rows.
- 2026 columns: `state`, `county`, `fips_code` (integer, leading zero
  dropped, so zero-pad to 5), `mw_1` to `mw_3`, `type_clean`, `q_status`
  (withdrawn, active, operational, suspended, unknown), `q_date`, `q_year`,
  `IA_phase_clean`. The 2025 file used different names (`mw1`, `type1`,
  `fips_codes`, `IA_status_clean`).
- County mapping: `fips_code` is present, so no name join is needed for most
  rows. Fall back to state plus county name for blanks.
- Derived metrics: active renewable MW per county, median queue age,
  withdrawal rate.

### 8. FracTracker Alliance US Data Centers Tracker

- Public ArcGIS feature services. Fetch with `etl/fetch_fractracker.py`.
  Details in `opposition_labels.md`.
- Facilities layer: 1,701 rows with county, status, MW, cooling type,
  pushback flag. Moratoria layer: 680 jurisdictions with census GEOID.
- County mapping: facilities by county name plus state, or by lat/lon;
  moratoria by GEOID for the 260 county rows.
- Columns: existing facility count and MW, proposed count and MW, any
  pushback, active or pending moratorium.
- License: non-commercial with credit. Put the credit on the data slide.

### 9. Climate projections for 2050 (CMRA)

- The brief's NEX-GDDP-CMIP6 is 34 TB. Don't download it.
- Verified county-level alternative: the CMRA Climate and Coastal Inundation
  Projections feature service, 3,233 counties.
  `https://services3.arcgis.com/0Fs3HcaFfvzXvm7w/arcgis/rest/services/Climate_Mapping_Resilience_and_Adaptation_(CMRA)_Climate_and_Coastal_Inundation_Projections/FeatureServer/0/query?where=GEOID%3D%2719161%27&outFields=GEOID,CountyName,HISTORIC_MEAN_CDD,RCP85MID_MEAN_CDD,RCP85MID_MEAN_TMAX95F&returnGeometry=false&f=json`
- Field pattern: `{HISTORIC|RCP45|RCP85}{EARLY|MID|LATE}_{MIN|MEAN|MAX}_{CDD|HDD|TMAX90F|TMAX95F|TMAX100F}`.
  MID is mid-century. Sac County, Iowa goes from 820 to 1,519 cooling degree
  days under RCP8.5 mid-century.
- Page through once with `where=1=1` and save a static CSV.
- Alternative: the ACIS grid endpoint that Climate Explorer uses,
  `https://grid2.rcc-acis.org/GridData`, accepts a JSON `params` query and
  returns county means per year. Verified for FIPS 19161.
- Gotchas: both use LOCA-downscaled CMIP5 (RCP4.5 and RCP8.5), not CMIP6.
  State that on the methods slide rather than claiming CMIP6.

### 10. EIA-861

- Download: `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip`
  (4.6 MB, verified).
- Files: `Reliability_2024.xlsx` (SAIDI, SAIFI by utility),
  `Service_Territory_2024.xlsx` (utility ID to state and county name).
- County mapping: reliability by utility ID, territory file maps to county
  name, then customer-weight where several utilities serve one county.
- Gotchas: county names, not FIPS. Pick one SAIDI method and one treatment
  of major event days. Many small utilities don't report. PUDL at
  `data.catalyst.coop` has a cleaned version.

### 11. EIA-923 Schedule 8D and EIA-860

- EIA-923 2024 final: `https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2024.zip`
  (22.8 MB, verified). 2025 final also exists at
  `https://www.eia.gov/electricity/data/eia923/xls/f923_2025.zip`.
- Cooling water: member file `EIA923_Schedule_8_Annual_Envir_Infor_2024_Final.xlsx`,
  sheet `8D Cooling System Information`, monthly withdrawal and consumption
  in million gallons per plant.
- EIA-860 2024: `https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602024.zip`
  (22.1 MB, verified). Plant file `2___Plant_Y2024.xlsx` has lat/lon and
  county. 2025 at `https://www.eia.gov/electricity/data/eia860/xls/eia8602025.zip`.
- County mapping: 923 water by plant ID, join to 860 for location, spatial
  join to county, then aggregate to eGRID subregion for water per MWh of
  grid power.
- Gotchas: 8D covers only thermoelectric plants of 100 MW or more. Hydro and
  renewables report nothing, so a hydro-heavy subregion correctly scores
  near zero.

### 12. FCC broadband

- The FCC site (`broadbandmap.fcc.gov/data-download`) blocks the sandbox
  and requires a free login. Unverified from here.
- Verified alternative: Esri Living Atlas county layer, 3,234 counties keyed
  by `GEOID`, with `TotalBSLs`, `ServedBSLs`, `ServedBSLsFiber`.
  `https://services8.arcgis.com/peDZJliSvYims39Q/arcgis/rest/services/FCC_Broadband_Data_Collection_December_2024_View/FeatureServer/1`
  The service name says December 2024; the item title says December 2025.
  Sac County: 6,600 locations, 6,046 fiber-served.
- Gotchas: this measures last-mile fiber, not long-haul backbone, which is
  what a data center cares about. Treat it as a proxy and say so.

### 13. US Drought Monitor

- REST (verified, 12.1 MB for Iowa, 4 seconds):
  `https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=IA&startdate=1/1/2000&enddate=12/31/2025&statisticsType=1`
- Set the `Accept` header to `text/csv` or `application/json`.
- Columns: `MapDate, FIPS, County, State, None, D0, D1, D2, D3, D4, ValidStart, ValidEnd`.
- Gotchas: `aoi=us` returns an empty body. Loop over the 48 states. A single
  FIPS also works. `statisticsType=1` is cumulative, so D2 already includes
  D3 and D4.

### 14. USGS Annual NLCD

- 2024 CONUS land cover (1.44 GB, verified):
  `https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/data-bundles/Annual_NLCD_LndCov_2024_CU_C1V1.zip`
- The MRLC page renders links with JavaScript, so the URL was confirmed by
  naming pattern. S3 is requester-pays.
- County mapping: zonal histogram of class codes per county. Run once and
  cache.
- Shortcut: IPUMS NHGIS publishes county NLCD summaries for 2001 to 2021
  (free account required):
  `https://secure-assets.ipums.org/nhgis/environmental/nhgis_county2020_tl2020_nlcd_timebycolumn.zip`.
  2021 is close enough for land cover shares.

### 15. GDELT

See `gdelt_feasibility.md`. BigQuery path recommended. The search API
could not be tested from the sandbox because of a shared-IP rate limit.

### 16. NOAA IBTrACS

- `https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NA.list.v04r01.csv`
- CSV with two header rows. Buffer tracks by 100 km, count passes since
  1980, record max `USA_WIND`.
- NRI already has a hurricane score. Use this only for the track map.

### 17. Global Energy Monitor steel and cement trackers

- Request form gates the download at
  `https://globalenergymonitor.org/projects/global-iron-and-steel-tracker/download-data/`
  and the cement equivalent. CC BY 4.0.
- XLSX with plant lat/lon. Distance from county centroid to nearest electric
  arc furnace and nearest cement plant.
- Low priority. The embodied carbon story is weak at county resolution.

### 18. FEMA NFHL and USFS Wildfire Risk to Communities

- NFHL: `https://msc.fema.gov/portal/advanceSearch` by county, or the
  ArcGIS REST service at `https://hazards.fema.gov/arcgis/rest/services/public/NFHL`.
  Use only for finalist sites where a real floodplain check matters.
- Wildfire Risk to Communities: `https://wildfirerisk.org/download/`,
  county spreadsheets. Redundant with NRI wildfire.

## Cross-cutting gotchas

- **County-name joins** (EIA-861 territory, eGRID plants, FracTracker
  facilities) need one shared normalization function. Watch "St." vs
  "Saint", "DeKalb" vs "De Kalb", Virginia independent cities, Louisiana
  parishes, and Connecticut planning regions. Build it once in `etl/fips.py`
  and test it against the TIGER name list.
- **Spatial joins** (Aqueduct, NREL rasters, Normals, NLCD, plant points)
  all need the county polygons in the same projection. Use EPSG:5070 for
  area work and EPSG:4326 for the map.
- **ArcGIS feature services** (NRI, CMRA, FCC, FracTracker) all page at
  1,000 to 2,000 rows. One shared pager function in `etl/arcgis.py` covers
  all four.
- **Hosts that block the sandbox**: `www.fema.gov`, `broadbandmap.fcc.gov`,
  `emp.lbl.gov`, `nrel.gov`, `web.archive.org`. Each has a working
  alternative above.
- **Too big to download casually**: NLCD (1.44 GB), NREL zips (140 and
  185 MB), Aqueduct (262 MB). Assign to one person with good bandwidth and
  cache the county outputs in `data/processed/`.

## Suggested division of the download work

- Person A: TIGER, NRI, eGRID, Queued Up, Drought Monitor, FracTracker,
  CMRA. All direct county joins or paged ArcGIS services. Half a day.
- Person B: NREL rasters, NLCD, Aqueduct, Normals. All spatial. One day
  including the zonal stats run.
- Person C: EIA 861 and 923 via PUDL or the ZIPs, FCC via the Esri layer,
  GDELT via BigQuery, hand-verification of the opposition labels. One day.

## ETL v2 context sources (2026-10-03)

The context columns in `docs/schema.md` come from these sources. Each was
checked from a laptop on 2026-10-03.

- **BLS LAUS:** `https://www.bls.gov/lau/laucntyYY.xlsx`. The host returns
  403 unless the User-Agent carries a contact address, which the adapter
  reads from `BLS_CONTACT_EMAIL`. Read with `skiprows=1`. All years key
  Connecticut by planning region. The 2025 file is an 11-month average.
- **BLS QCEW:** `https://data.bls.gov/cew/data/api/{year}/a/industry/31_33.csv`
  (underscore, not hyphen) and `.../10.csv`. County manufacturing is
  `agglvl_code` 74. Suppressed cells have `disclosure_code` N and employment 0.
  2015 and 2019 use Connecticut's old counties.
- **USDA ERS:** RUCC 2023 at
  `https://www.ers.usda.gov/media/5767/2023-rural-urban-continuum-codes.xlsx`
  and Typology 2025 at
  `https://www.ers.usda.gov/media/6173/ers-county-typology-codes-2025-edition.xlsx`.
  Both are wide in the xlsx and long in the CSV. In Typology, 99 means not
  available.
- **EPA brownfields:** Envirofacts exposes no ACRES tables. Three public
  layers under `services.arcgis.com/cJ9YHowT8TU7DUyn`:
  `Cleanups_in_my_Community_Sites` (47,106 brownfield rows, 47,101
  properties), `RE_Powering_Mapper_Sites_2022` (`Program='Brownfields'`,
  acreage), and `Brownfield_Properties_Over_100_Acres_view` (335 sites).
  RE-Powering acreage includes community-wide records up to 168,000 acres.
- **FracTracker moratoria:** municipal rows use 10-digit county-subdivision
  GEOIDs or 7-digit place GEOIDs. Places need the 2024 place Gazetteer
  to reach a county.
- **LBNL:** `on_date` is the actual online date. It's filled for about 69%
  of operational rows, about 99% in PJM, CAISO, and MISO but 18% in the West
  and 0% in ISO-NE.
