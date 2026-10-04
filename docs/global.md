# Global country-level run

This run shows that the siting engine works on a second region. It ranks 196 countries with the same
gates, percentile pillars, weighted composite, floor rule, and robustness draws that rank US counties.
It is a screen for where to look next. It doesn't pick sites.

Run it:

```
python -m engine rank --conditions engine/conditions_global/global_balanced.yaml \
  --pillars engine/pillars_global.yaml \
  --features data/processed/global_country_features.parquet \
  --out results/global_balanced.csv
python -m engine explain --conditions engine/conditions_global/global_balanced.yaml \
  --pillars engine/pillars_global.yaml \
  --features data/processed/global_country_features.parquet --id USA
```

Rebuild the table with `python -m etl.global_countries.build`. Raw files go to `data/raw/global/`.

The preset lives in `engine/conditions_global/`, not `engine/conditions/`. The demo app and the preset
tests treat every file in `engine/conditions/` as a US preset and run it on the county table.

## What changed in the engine

The scoring was already region-agnostic. Only the row identity was hard-coded to counties.

| File | Change |
|---|---|
| `engine/rank.py` | +17 -6. An optional `unit` block in the conditions file names the key, name, and group columns. It defaults to `fips`, `county_name`, `state`. Only a `fips` key is zero-padded. `states_include` and `states_exclude` act on the group column. One new simple gate, `min_electricity_generation_twh`. |
| `engine/explain.py` | +13 -11. Looks rows up by the unit key and labels output with the unit columns. |
| `engine/__main__.py` | +10 -7. Passes the unit key to `load_features`. `explain` accepts `--id` as an alias for `--fips`. |

Nothing else in the engine changed: gates, percentiles, pillar means, null handling, weights,
the floor rule, horizon swaps, top reasons, and robustness are the same code. With no `unit` block,
all three US presets reproduce their committed results byte for byte.

The CLI summary line and the report JSON still say "counties" (`counties`, `hazard_gate_nonzero_counties`).
Read them as rows. Renaming them would change the US output, so they stay.

## Sources

Every source is open and needs no key. Each was downloaded and checked before use.

| Columns | Source | Year used |
|---|---|---|
| `grid_co2_g_kwh`, `renewable_share_elec_pct`, `low_carbon_share_elec_pct`, `electricity_generation_twh` | Our World in Data energy dataset, which republishes Ember and the Energy Institute | Latest year with a carbon intensity value: 2025 for 89 countries, 2024 for 91, 2022 or 2023 for 7. `energy_data_year` records it per row. |
| `water_stress_bws`, `water_stress_2050` | WRI Aqueduct 4.0 country rankings, industrial weighting, 0-5 score | Baseline, and 2050 business as usual. Release of 2023-07-05. |
| `inform_earthquake`, `inform_river_flood`, `inform_coastal_flood`, `inform_tropical_cyclone`, `inform_tsunami`, `inform_drought` | EU JRC INFORM Risk Index, hazard and exposure components, 0-10 | INFORM Risk 2026 v0.7.2, released 2026-03-31 |
| `cdd65_*`, `hd35_*` | World Bank Climate Change Knowledge Portal, CMIP6 ensemble median | 1995-2014, and 2040-2059 under SSP2-4.5 and SSP5-8.5 |
| `peeringdb_facility_count`, `peeringdb_ixp_count` | PeeringDB API, status ok | Live, fetched 2026-10-04 |
| `population`, `gdp_per_capita_usd`, `unemployment_rate_pct`, `broadband_per_100` | World Bank API | Most recent value: population 2025, unemployment 2021-2025, broadband 2021-2025, GDP 2011-2025 |
| `wgi_political_stability`, `wgi_regulatory_quality`, `wgi_rule_of_law` | World Bank Worldwide Governance Indicators | 2025 |

Rows are the World Bank's 217 economies, minus 22 territories and special administrative regions, plus
Taiwan. Dropped territories include Hong Kong, Macao, Puerto Rico, and Greenland. Taiwan has null World
Bank columns, except governance. The governance API labels Taiwan's row with the ISO3 code SYR and an
empty country id, so the build takes that row by its name.

## Columns that couldn't be filled

- **Electricity price.** No open, current, global industrial electricity price exists. The IEA's
  series is paywalled. Eurostat covers Europe only. There's no cost pillar.
- **Power reliability.** The World Bank Enterprise Survey outage series `IC.ELC.OUTG` returns
  "indicator not found" from the API. Doing Business stopped in 2020. There's no reliability column.
- **Land.** Every country has land somewhere, so there's no land pillar.
- `gdp_per_capita_usd` is in the table but isn't scored. The US community pillar treats economic need
  as a reason to rank higher. At country scale that rule would favor the poorest countries, and the
  opposite rule contradicts the US choice. Neither is defensible without a decision, so it's left out.

Notable nulls: Singapore and small island states have no Aqueduct score. Andorra, Monaco, San Marino,
Taiwan, and Kosovo have no INFORM row. Kosovo and eight microstates have no generation data.

## Gates and the floor

A 300 MW facility at a 0.8 load factor draws about 2.1 TWh a year. Below 20 TWh of national generation,
that is more than a tenth of the system. `min_electricity_generation_twh: 20` excludes 105 countries.
Iceland, at 19.05 TWh, fails by a hair even though it hosts data centers. The threshold is a judgment.

The engine treats a null as unknown, not as a failure. Eight microstates with no generation data would
pass. `min_population: 1000000` removes them and nothing else, since every country above 20 TWh has over
1.5 million people. Kosovo has 1.6 million people and no generation data, so it passes as unknown.

Result: 83 of 196 countries pass the gates. 55 of them pass the floor of 10. The floor compares each
pillar against all 196 countries.

## Top 15

Composite and pillar scores are 0-100. Robustness is the share of 2000 weight draws in which the
country lands in the top 10.

| Rank | Country | Composite | Robustness | Energy | Water | Climate | Grid | Community | Governance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Sweden | 81.6 | 1.00 | 88.1 | 82.6 | 61.4 | 89.5 | 64.4 | 90.1 |
| 2 | Switzerland | 81.1 | 1.00 | 87.0 | 83.0 | 66.2 | 88.5 | 47.8 | 94.0 |
| 3 | Norway | 80.8 | 1.00 | 94.7 | 84.1 | 58.2 | 88.5 | 41.8 | 93.4 |
| 4 | Finland | 78.8 | 1.00 | 83.4 | 77.1 | 62.6 | 83.1 | 60.5 | 92.5 |
| 5 | Denmark | 77.8 | 1.00 | 87.9 | 71.5 | 69.1 | 80.2 | 49.5 | 90.8 |
| 6 | New Zealand | 76.9 | 1.00 | 87.3 | 83.8 | 45.8 | 83.8 | 43.6 | 94.4 |
| 7 | Austria | 75.8 | 1.00 | 84.0 | 79.4 | 60.6 | 80.2 | 53.9 | 82.7 |
| 8 | United Kingdom | 75.1 | 1.00 | 68.1 | 77.6 | 55.5 | 94.1 | 66.4 | 80.4 |
| 9 | Canada | 74.7 | 0.99 | 74.3 | 73.0 | 34.1 | 95.0 | 74.0 | 86.7 |
| 10 | France | 72.9 | 0.70 | 75.8 | 66.8 | 42.2 | 96.6 | 79.6 | 70.4 |
| 11 | Netherlands | 72.1 | 0.20 | 64.3 | 76.6 | 49.4 | 91.7 | 50.2 | 84.9 |
| 12 | Germany | 71.7 | 0.00 | 63.8 | 67.9 | 46.4 | 97.3 | 62.4 | 80.4 |
| 13 | Ireland | 71.1 | 0.10 | 62.6 | 85.9 | 62.3 | 74.1 | 40.7 | 87.4 |
| 14 | Portugal | 68.4 | 0.00 | 82.7 | 49.6 | 49.2 | 78.9 | 57.9 | 77.2 |
| 15 | Spain | 68.3 | 0.00 | 73.3 | 46.0 | 42.8 | 90.7 | 82.8 | 69.6 |

The top nine hold in almost every weight draw. Ranks 10 to 15 trade places.

## Where the United States lands

The United States ranks 58 of 83, with a composite of 59.5 and robustness 0. On composite alone it would
be 34th. It fails the floor on climate resilience: its pillar score of 16.2 is in the bottom tenth of
countries, because INFORM scores national exposure to earthquakes, tropical cyclones, and coastal floods,
and the US has all three somewhere. Japan, Korea, China, and India fail the floor on the same pillar.
Its best pillars are grid and infrastructure (96.8, the most PeeringDB facilities and exchanges of any
country) and community (68.5).

## What a country ranking can't tell you

A country isn't a site. In the US county table, grid carbon, water stress, and every hazard column
range across the full scale from one county to the next. A national mean hides that, and for a country
the size of the US the variation inside it likely matters more than its national score. The US fails the floor here because hurricanes hit
the Gulf Coast and earthquakes hit California, which says nothing about a site in Ohio. Large countries
are penalized on national hazard exposure and rewarded on national counts of facilities and generation,
and those two effects partly cancel by accident, not by design. Local grid constraints,
such as an operator pausing new large connections in one region, don't appear in any column here.
Use this table to choose which country's sub-national data to build next, not to choose a site.
