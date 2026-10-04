# Stage 2: industrial reuse and community transition

The "Industrial reuse and community transition" section of the app adds
context to a county the national model has already ranked. It explains and
screens. It doesn't score, and it doesn't change the ranking. No pillar,
weight, gate, preset, or result reads it. The logic is in `engine/reuse.py`
and the display is `show_reuse()` in `app/app.py`.

> Economic need is not evidence of community support. Local engagement and
> project-level validation are still required.

The app shows that statement at the top of the section. The screening brief
repeats it at the start and the end. Nothing in Stage 2 measures, infers, or
reports community sentiment.

## What the section shows

The section opens for any county, including ones that rank low or fail a
gate. Its caption says it is unscored, post-ranking screening, meant for
counties the national model has already shortlisted.

Each numeric measure appears with the national median and the county's
national percentile. The percentile is mid-rank: the share of counties below
the value, with ties counted as half. That matters because many of these
columns are 0 in most counties. A percentile ranks the raw value, so it
isn't a score. On a decline measure, the 1st percentile is one of the
steepest losses in the country, not a favorable result. A "How to read"
column says so for the decline and unemployment rows.

- **Economic transition:**
  - Unemployment: 2024 and pooled 2022-2024 (BLS LAUS).
  - Manufacturing jobs in 2015 and 2024, with the change in jobs and in
    percent (BLS QCEW, private).
  - The 1969 manufacturing share and its change through 2022 (BEA).
  - Population change from the historical peak.
  - USDA low-employment and population-loss flags.
  - Rural-urban classification (RUCC 2023) and industry dependence.
- **Industrial reuse:**
  - EPA brownfield properties: how many, how many report acreage, total
    reported acreage, reporting coverage, properties of 50 or more acres, and
    properties ready for reuse.
  - Retired coal capacity.
  - IRA energy-community flags.
- **Infrastructure context:**
  - Generation within 100 km, all fuels and clean only.
  - Last-mile fiber.
  - FracTracker data-center counts and reported MW, each with its reporting
    share.
  - The scored queue measures. Standalone storage appears separately from
    clean generation.
- **Brownfield properties:** the selected county's EPA brownfield properties,
  largest reported acreage first. The list shows reported acreage,
  ready-for-reuse status, planned future use, substation, transmission, and
  rail distances, and an EPA profile link. You can download it as CSV.
- **Why this community could benefit:** evidence statements drawn only from
  the data above, such as jobs lost, long-run manufacturing decline, high
  unemployment, retired coal, and brownfield properties. They describe need
  and assets. They don't describe what residents want.
- **What still requires local verification:**
  - utility capacity
  - site ownership and availability
  - cleanup status
  - zoning
  - water and air permits
  - transmission upgrades
  - local engagement
  - tax and community-benefit agreements

  County-specific data gaps are added to the list.
- **Screening brief:** a downloadable Markdown file. It covers rank and
  pillar scores, the three evidence tables, benefits, key risks (gate
  failures, warnings, and pillars below the 25th national percentile),
  missing data, and the verification steps.

The map's "Color the map by" control also offers manufacturing jobs lost,
unemployment, brownfield properties, and brownfields ready for reuse.
Composite stays the default.

## Data limitations

- **Brownfields aren't available land.** EPA ACRES records mark a cleanup or
  assessment history. They aren't confirmed available land and aren't
  confirmed data-center sites.
  - Acreage comes from the 2022 RE-Powering snapshot or EPA's 100+ acre layer.
    About a quarter of properties report none.
  - No national field carries cleanup completion. Redevelopment start dates
    were empty at retrieval, so "no redevelopment reported" never means vacant.
- **The site list is generated, not committed.**
  `data/processed/brownfield_sites.parquet` comes from
  `python -m etl.build_features`. When the file is absent, the section says
  so and still shows the county totals from the committed feature table. Set
  `BAC_SITES` to point at another copy.
- **Manufacturing:** QCEW suppresses small cells, which show as "not
  available", never as 0. Connecticut planning regions have no 2015 QCEW or
  USDA economic typology codes.
- **Data-center MW:** FracTracker MW is reported for about 40% of facilities.
  The reporting share shows how complete each county's total is.
- **Delivered queue capacity** relies on proposed online dates where LBNL
  lacks actual dates, which covers all of ISO-NE and most of the West. The
  fallback share is shown as an uncertainty indicator.
- **The benefits are evidence, not a forecast.** A county can show economic
  need and still oppose a project. Data-center pushback and moratoria are in
  the permitting pillar and the gates, not here.
