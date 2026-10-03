# GDELT feasibility for a county-level community-opposition layer

Date: 2026-10-02. Probed from the cloud sandbox, which blocks gdeltproject.org.
Findings about the data format come from a real GKG 2.1 sample file shipped
inside the `gdelt` PyPI package (50 records from 2017-07-01) and from the
GDELT codebooks bundled with it. Findings about the APIs come from the
`gdeltdoc` client README and GDELT blog posts surfaced through search.
Nothing here has been tested against the live API yet. Do that on a laptop.

## Bottom line

County resolution is achievable, but not through the search API alone.

- The Global Knowledge Graph (GKG) 2.1 tags every US city mention with an
  ADM2 code that is the state abbreviation plus the 3-digit county code,
  for example `IA161` for Sac County, Iowa (FIPS 19161). It also gives the
  city centroid lat/lon and a GNIS feature ID.
- In the 50-record sample, 84 of 84 US city mentions carried an ADM2 code.
  Expect lower but still high coverage on recent data.
- The DOC 2.0 search API returns only `url`, `title`, `domain`, `seendate`,
  `language`, `sourcecountry`. No locations. So full-text search and
  geolocation live in two different places and have to be joined.

## The two access paths

### Path A: BigQuery public dataset (recommended)

Table: `gdelt-bq.gdeltv2.gkg_partitioned`, partitioned by day via
`_PARTITIONTIME`. The full GKG is about 3.6 TB, so always filter on the
partition column. A one-year, location-focused query is on the order of tens
of GB.

BigQuery sandbox needs no credit card and gives 1 TB of query volume per
month. One teammate creates a Google Cloud project, enables the sandbox, and
runs the SQL in `etl/gdelt_gkg_county.sql`.

The weak point is topic filtering. GKG does not store article text. Options,
in order of precision:

1. Join on URLs returned by the DOC API (see Path B). Most precise.
2. Filter `DocumentIdentifier` (the URL) for `data-center` or `datacenter`
   in the slug. Zero cost, surprisingly good recall for local news, misses
   articles with generic slugs.
3. Filter `V2Themes` for infrastructure and protest themes. Noisy.

Use 1 if the DOC API cooperates, otherwise 2. The SQL supports both.

### Path B: DOC 2.0 search API

Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`. Full-text search.
The `gdeltdoc` client README says 3 months officially, but a later GDELT
blog post ("DOC/GEO 2.0 API updates: full year searching") extended it to
about a year via `startdatetime` and `enddatetime`. Older ranges often still
work but are not guaranteed. Max 250 records per
call. No key. Unofficial rate limit; the client community uses about one
request every 5 seconds.

Use it to collect article URLs matching queries like
`"data center" (rezoning OR moratorium OR "town hall" OR residents OR opposition) sourcecountry:US`,
sliced into week-long windows. Then join those URLs to GKG in BigQuery to get
tone and county.

`etl/gdelt_probe.py` does the collection step and writes a CSV of URLs.

### Path C: GEO 2.0 API

Returns lat/lon points for a keyword, but only over the last 7 days. Fine
for a live demo widget, useless for building the training table.

## What the layer looks like

Per county and quarter:

- `article_count`: data center articles geolocated to the county
- `mean_tone`, `share_negative`: from `V2Tone`
- `opposition_type_*`: shares from LLM or embedding classification of the
  article title and first paragraph (water, noise, bills, farmland, secrecy,
  tax). Needs article text, which GDELT does not store. Fetch the URLs or
  use the title alone.
- `coverage_flag`: zero articles means no data, not no opposition. Fill
  with the state-level rate and carry a confidence column.

## Risks

- Coverage bias toward counties with a newspaper that GDELT crawls.
- A city mention is not a project location. "Loudoun County" in an article
  about Arizona still tags Virginia. Weight by the first-mentioned location
  or by mention count.
- GDELT tone is a dictionary score, not a model. Use it as a feature, not
  as the headline number.
- The sample is from 2017. Confirm ADM2 coverage on 2025 data with one
  BigQuery query before building on it.

## Data Center Watch (labels)

Quarterly reports from 10a Labs. Headline figures as of the latest coverage:

| Period | Projects blocked or delayed | Value |
| --- | --- | --- |
| 2023 to Q1 2025 | not stated | $64B |
| 2025 full year | 48 (31 cancelled, 17 delayed) | $156B |
| Q1 2026 | 75 | $130B |
| Q2 2026 | 45 | $68B |

Opposition groups: 833 across 49 states as of March 2026.

The project-level list (name, location, status, reason) appears in the
reports but a structured download was not confirmed from the sandbox. Plan
to hand-code it from the report PDFs and press coverage. Budget two to three
hours for one person.
