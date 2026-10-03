# Data inventory

Scope: contiguous US plus DC, county (FIPS) as the unit of analysis. Every
layer below ends up as one or more columns in a single county table.

Verification status: compiled 2026-10-02 from official pages and mirrors via
search. The research sandbox could not fetch the source domains directly, so
file sizes and a few vintages are marked unverified. Confirm each download on
a laptop before the ETL person depends on it. No dataset needs payment.
Three need a free registration: FCC, NREL API, Global Energy Monitor.

## Priority tiers

Tier 1 builds the minimum viable county table. Tier 2 adds the layers that
make the systems-thinking story. Tier 3 is only if time allows.

| Tier | Dataset | Columns it produces |
| --- | --- | --- |
| 1 | Census TIGER county boundaries + population | geometry, population, the join key for everything else |
| 1 | FEMA National Risk Index | flood, wildfire, hurricane, drought, heat wave, tornado, winter weather scores |
| 1 | EPA eGRID | grid carbon intensity (lb CO2/MWh), fuel mix, renewable share |
| 1 | NREL solar and wind annual rasters | mean GHI, mean 100 m wind speed |
| 1 | NOAA Climate Normals | heating and cooling degree days, dew point |
| 1 | WRI Aqueduct 4.0 | baseline water stress |
| 1 | LBNL Queued Up | MW in queue by fuel, queue age, congestion proxy |
| 2 | EIA-861 | SAIDI and SAIFI reliability, utility service territory |
| 2 | EIA-923 Schedule 8D + EIA-860 | grid water withdrawal per MWh by subregion |
| 2 | USGS Annual NLCD | percent developed, cropland, forest, impervious |
| 2 | FCC Broadband Map | percent of locations with fiber |
| 2 | US Drought Monitor | percent of weeks in D2 or worse since 2000 |
| 2 | GDELT + Data Center Watch | community opposition risk (see gdelt_feasibility.md) |
| 2 | Climate projections (county extracts) | 2050 cooling degree days, days above 95F |
| 3 | IBTrACS | hurricane track passes within 100 km |
| 3 | GEM steel and cement trackers | distance to nearest low-carbon mill or plant |
| 3 | FEMA NFHL | percent area in special flood hazard area |
| 3 | USFS Wildfire Risk to Communities | redundant with NRI wildfire, use only for detail |

Dropped from the brief's list: Freight Analysis Framework, Clean Watersheds
Needs Survey, Building Transparency, Bloom Energy. None adds a column worth
the ingestion time. Treat fuel cells as a scenario toggle in the UI.

## Dataset details

### 1. Census TIGER/Line counties and population

- Download: `https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip`.
  The 500k cartographic file at `https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip`
  is smaller and fine for the map.
- Population: ACS 5-year via `https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E&for=county:*`.
  No key needed under 500 requests per day.
- Format: shapefile, JSON.
- Unit: county. GEOID is the 5-digit FIPS.
- Gotchas: filter STATEFP to the 48 states plus DC. Connecticut uses planning
  regions instead of counties since 2022. Pick one convention and apply it to
  every name-based join.

### 2. FEMA National Risk Index (NRI)

- Download: `https://hazards.fema.gov/nri/data-resources`. County CSV is
  `NRI_Table_Counties.zip`, shapefile is `NRI_Shapefile_Counties.zip`.
  Mirror on data.gov if the page moved. One source says NRI was folded into
  FEMA's Resilience Analysis and Planning Tool in December 2025. Verify the
  link first.
- Format: CSV, shapefile, geodatabase.
- Unit: county, keyed on `STCOFIPS`. Direct join.
- Vintage: metadata updated July 2025.
- Use: 18 hazards with risk scores, expected annual loss, social
  vulnerability, and community resilience. This one file covers flood,
  wildfire, hurricane, drought, heat, tornado, and winter weather, which
  replaces four separate pulls from the brief.
- Gotchas: scores are relative percentiles. Expected annual loss in dollars
  scales with what's there to lose, so empty counties look safe. Use the
  hazard frequency and exposure fields, not just the dollar loss.

### 3. EPA eGRID

- Download: `https://www.epa.gov/egrid/download-data`. Subregion shapefile at
  `https://www.epa.gov/egrid/egrid-mapping-files`.
- Format: one XLSX workbook with sheets for units, generators, plants (PLNT),
  states, balancing authorities, subregions (SRL), and national.
- Unit: plant with lat/lon and county name; subregion; balancing authority.
- Vintage: eGRID2023 Rev 2, June 2025. eGRID2024 was due January 2026,
  unverified whether released.
- County mapping: spatial join county centroid to subregion shapefile and
  pull the SRL emission rate. Where subregions overlap, use the "multiple
  subregions" file. For plant-level work, use PLNT lat/lon.
- Gotchas: eGRID has no water-use fields. Water comes from EIA-923. The
  subregion rate is an annual average, not a marginal rate. Say so in the
  methods slide.

### 4. NREL solar (NSRDB) and wind (WIND Toolkit) annual rasters

- Solar: multiyear annual GHI and DNI GeoTIFF from
  `https://www.nrel.gov/gis/solar-resource-maps` or ScienceBase item
  `5f63a09682ce38aaa23affcd`. 4 km grid, 1998 to 2016 average.
- Wind: "WIND Toolkit Multi-year Annual Average United States" GeoTIFF from
  ScienceBase item `5f636dda82ce38aaa239d14c`. 2 km grid, 100 m hub height,
  2007 to 2013 average. Units are km/h, convert to m/s.
- Format: GeoTIFF. No key for the static rasters.
- County mapping: zonal mean over county polygons.
- Gotchas: avoid the NSRDB API. It needs a key, allows 2,000 requests per
  day, and returns hourly point data you'd have to aggregate yourself. The
  NREL developer domain reportedly moved in 2026, unverified. A 120 m wind
  raster was not found pre-aggregated, 100 m is fine.

### 5. NOAA U.S. Climate Normals 1991 to 2020

- Download: `https://www.ncei.noaa.gov/data/normals-annual/1991-2020/access/`
  for annual and seasonal normals, `https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/`
  for hourly.
- Format: one CSV per station.
- Unit: station with lat/lon.
- Fields: annual product gives heating and cooling degree days
  (`ann-htdd-normal`, `ann-cldd-normal`). Hourly product gives dew point and
  heat index but covers only a few hundred ASOS stations.
- County mapping: spatial join station to county, then average. Many counties
  have no station, so fall back to inverse-distance weighting from the
  nearest three.
- Gotchas: wet-bulb temperature is not provided. Compute it from temperature
  and dew point if you want a free-cooling-hours metric. That's the number
  that drives the cooling story, so it's worth the effort.

### 6. WRI Aqueduct 4.0

- Download: `https://www.wri.org/data/aqueduct-global-maps-40-data`. Docs at
  `https://github.com/wri/Aqueduct40`.
- Format: GeoPackage or geodatabase plus CSV. The GeoPackage is several GB,
  unverified.
- Unit: HydroBASINS level 6 sub-basin, about 68,000 polygons globally.
- Vintage: 2023 release. Includes future scenarios for 2030, 2050, 2080.
- County mapping: area-weighted overlay of `bws_raw` and `bws_cat` (baseline
  water stress) onto county polygons. Population weighting is better if you
  have time.
- Gotchas: there is no county-level version. Also available on Google Earth
  Engine as `WRI/Aqueduct_Water_Risk/V4` if someone has GEE set up, which
  makes the overlay trivial.

### 7. LBNL Queued Up

- Download: `https://emp.lbl.gov/queues`, data file linked from
  `https://energyanalysis.lbl.gov/publications/us-interconnection-queue-data`.
- Format: XLSX with a project-level sheet, a codebook, and summary tabs.
- Unit: project with state and county name. No lat/lon.
- Vintage: 2025 edition covering queues through end of 2024.
- County mapping: normalize county name and join to FIPS. Sum MW by status
  (active, withdrawn, operational) and by fuel.
- Derived metrics: active renewable MW per county (decarbonization
  potential), median queue age (congestion), withdrawal rate (failure rate).
- Gotchas: county is free text with blanks and multi-county entries. Expect
  to lose 10 to 20 percent of rows to the join.

### 8. EIA-861

- Download: `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip`.
- Format: ZIP of about 20 XLSX files. Use `Reliability_2024.xlsx` for SAIDI
  and SAIFI and `Service_Territory_2024.xlsx` for utility-to-county mapping.
- Unit: utility.
- County mapping: reliability by utility ID, territory file maps utility ID
  to state and county name, then customer-weight where several utilities
  serve one county.
- Gotchas: county names, not FIPS. Pick one SAIDI method (IEEE vs other) and
  one treatment of major event days, and use it consistently. Many small
  utilities don't report. PUDL at `data.catalyst.coop` has a cleaned Parquet
  version of this and of 860 and 923, which may save a day.

### 9. EIA-923 Schedule 8D and EIA-860

- Download: `https://www.eia.gov/electricity/data/eia923/` and
  `https://www.eia.gov/electricity/data/eia860/`. The 860 plant file is
  `2___Plant_Y2024.xlsx` with lat/lon and county.
- Format: ZIP of XLSX.
- Unit: plant and cooling system.
- Vintage: 2024 final.
- County mapping: 923 cooling water by plant ID, join to 860 for lat/lon,
  spatial join to county, then aggregate to eGRID subregion to get water
  withdrawal and consumption per MWh of grid power. That's the "water used
  in generation of grid power" the brief asks for.
- Gotchas: 8D is only in the final annual release and only for thermoelectric
  plants of 100 MW or more. Units mix gallons per minute and million gallons.
  Hydro and renewables report nothing, so a hydro-heavy subregion correctly
  scores near zero.

### 10. USGS Annual NLCD

- Download: `https://www.mrlc.gov/data` mosaic download, or tiles via
  EarthExplorer. Also on AWS S3.
- Format: GeoTIFF, 30 m, Albers projection. CONUS mosaic is several GB.
- Vintage: 2024.
- County mapping: zonal histogram of land cover classes per county. Percent
  developed, percent cropland, percent forest and wetland, and mean
  fractional impervious surface.
- Gotchas: this is the heaviest raster. Run it once, cache the county table.
  Google Earth Engine has it in the community catalog if that's easier.

### 11. FCC National Broadband Map

- Download: `https://broadbandmap.fcc.gov/data-download`. Free FCC account
  required. Public API needs a username and token.
- Format: CSV of fixed availability by provider and technology, nationwide or
  per state. Nationwide is multi-GB.
- Unit: serviceable location with census block GEOID.
- County mapping: filter technology code 50 (fiber), group by block, county
  is the first five characters of the block GEOID. Compute percent of
  locations with fiber.
- Gotchas: registration is mandatory. Download per state, not nationwide. The
  latest snapshot date often has no files posted yet, so take the one
  before it. This measures last-mile fiber, not long-haul backbone, which is
  what a data center cares about. Treat it as a proxy and say so.

### 12. US Drought Monitor

- REST: `https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=us&startdate=1/1/2000&enddate=12/31/2025&statisticsType=1`.
  Web form at `https://droughtmonitor.unl.edu/DmData/DataDownload/ComprehensiveStatistics.aspx`.
- Format: CSV or JSON.
- Unit: county, weekly.
- County mapping: already FIPS. Compute percent of weeks in D2 or worse.
- Gotchas: the national pull is large. Pull per state if it times out. No
  key, no documented rate limit.

### 13. Climate projections for 2050

- The brief's NEX-GDDP-CMIP6 is 34 TB of NetCDF across 35 models. Do not
  download it.
- Use county extracts instead: NOAA Climate Explorer at
  `https://crt-climate-explorer.nemac.org` gives per-county CSV of cooling
  degree days, heating degree days, and days above 95F under two scenarios.
  The CMRA Assessment Tool at `https://resilience.climate.gov` exposes similar
  county data with CSV and GeoJSON export.
- Gotchas: neither documents a bulk download. Scripting the Climate Explorer
  endpoint per county is likely but unverified. If it fails, pull a few
  dozen candidate counties by hand for the finalist comparison and show the
  2050 shift only for those.

### 14. NOAA IBTrACS

- Download: `https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NA.list.v04r01.csv`.
- Format: CSV, two header rows.
- Unit: 3-hourly track points.
- County mapping: buffer tracks by 100 km, count passes since 1980 per county,
  record max `USA_WIND`.
- Gotchas: NRI already has a hurricane score. Use this only if you want the
  map of tracks for the deck.

### 15. Global Energy Monitor steel and cement trackers

- Download: request form at
  `https://globalenergymonitor.org/projects/global-iron-and-steel-tracker/download-data/`
  and the equivalent cement page. Name, email, and organization gate the
  link. CC BY 4.0.
- Format: XLSX with plant lat/lon.
- County mapping: distance from county centroid to nearest electric arc
  furnace steel plant and nearest cement plant.
- Gotchas: US coverage is only steel plants of 0.5 Mtpa or more. The
  embodied carbon story is weak at county resolution anyway. Low priority.

### 16. USFS Wildfire Risk to Communities

- Download: `https://wildfirerisk.org/download/`, archived at
  `https://doi.org/10.2737/RDS-2024-0030`.
- Format: ZIP of spreadsheets by county plus 30 m rasters.
- Unit: county tabular. Direct FIPS join.
- Gotchas: two summary sets on different census boundaries. NRI wildfire
  covers the same ground. Skip unless you want the raster for a detail map.

### 17. FEMA National Flood Hazard Layer

- Download: `https://msc.fema.gov/portal/advanceSearch` by state or county,
  or the ArcGIS REST service at
  `https://hazards.fema.gov/arcgis/rest/services/public/NFHL`.
- Format: file geodatabase or shapefile. State files run hundreds of MB.
- County mapping: intersect zones A and V with county, compute percent area.
- Gotchas: large and incomplete. Some counties are unmapped. NRI's inland
  and coastal flood scores are enough for the gate. Use NFHL only for the
  finalist sites, where a real floodplain check matters.

### 18. GDELT and Data Center Watch

See `gdelt_feasibility.md`. Summary: GKG 2.1 tags US city mentions with a
county code. Use BigQuery for geolocation and tone, the DOC API for
full-text URL search. The DOC API supports date-ranged search up to a year
back per a later GDELT update, and often further. Data Center Watch
project list must be hand-coded from the quarterly reports.

## Cross-cutting gotchas

- **County-name joins** (EIA-861 territory, Queued Up, eGRID plants) need
  one shared normalization function. Watch "St." vs "Saint", "DeKalb" vs
  "De Kalb", Virginia independent cities, Louisiana parishes, and
  Connecticut planning regions. Build this once in `etl/fips.py` and test it
  against the TIGER name list.
- **Spatial joins** (Aqueduct, NREL rasters, Normals, NLCD, IBTrACS, plant
  points) all need the TIGER polygons in the same projection. Use EPSG:5070
  (CONUS Albers) for area work and EPSG:4326 for the map.
- **Registration** is needed for FCC, GEM, and the NREL API. Start those
  signups on day one. FCC approval is not instant.
- **Too big to download in a hackathon**: NEX-GDDP-CMIP6, FCC nationwide
  CSV, NLCD CONUS mosaic. Use county extracts, per-state files, and a
  one-time zonal stats run respectively.
- **Mirrors worth knowing**: PUDL (`data.catalyst.coop`) for cleaned EIA
  860, 861, 923. Google Earth Engine for Aqueduct and NLCD. data.gov for
  NRI if the FEMA page has moved.
- **Unverified from the sandbox**: file sizes nearly everywhere, whether
  eGRID2024 has shipped, whether NRI's download URL survived the RAPT
  migration, the NREL developer domain, and bulk access to Climate Explorer.

## Suggested division of the download work

- Person A: TIGER, NRI, eGRID, Queued Up, Drought Monitor. All direct
  county or name joins. Should take half a day.
- Person B: NREL rasters, NLCD, Aqueduct, Normals. All spatial. One day
  including the zonal stats run.
- Person C: FCC signup, EIA 861 and 923 via PUDL, GDELT via BigQuery, Data
  Center Watch hand-coding. One day.
