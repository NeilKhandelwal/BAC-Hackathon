-- GDELT GKG 2.1 -> county-level article counts and tone for data center coverage.
-- Run in BigQuery (sandbox tier is enough). Always keep the _PARTITIONTIME filter
-- or the query scans the full 3.6 TB table.
--
-- Two topic filters are provided. Prefer the URL list from etl/gdelt_probe.py
-- (upload it as a table named `urls` with one column `url`). Fall back to the
-- URL slug filter when that table does not exist.
--
-- Output columns: fips (5-digit), quarter, article_count, mean_tone, share_negative

DECLARE start_date DATE DEFAULT DATE '2024-01-01';
DECLARE end_date   DATE DEFAULT DATE '2026-09-30';

WITH articles AS (
  SELECT
    DocumentIdentifier AS url,
    DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(`DATE` AS STRING))) AS pub_date,
    SAFE_CAST(SPLIT(V2Tone, ',')[OFFSET(0)] AS FLOAT64) AS tone,
    V2Locations
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE DATE(_PARTITIONTIME) BETWEEN start_date AND end_date
    AND V2Locations IS NOT NULL
    AND (
      -- Filter 2: URL slug. Cheap, decent recall for local news.
      REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'data-?cent(er|re)')
      -- Filter 1: uncomment to restrict to URLs collected by gdelt_probe.py
      -- OR DocumentIdentifier IN (SELECT url FROM `your_project.your_dataset.urls`)
    )
),
locs AS (
  SELECT
    a.url, a.pub_date, a.tone,
    SPLIT(loc, '#') AS p
  FROM articles a, UNNEST(SPLIT(a.V2Locations, ';')) AS loc
),
us_city AS (
  -- V2Locations block layout:
  -- 0 type, 1 fullname, 2 countrycode, 3 adm1, 4 adm2, 5 lat, 6 lon, 7 featureid, 8 charoffset
  SELECT
    url, pub_date, tone,
    p[OFFSET(4)] AS adm2,            -- e.g. 'IA161'
    SAFE_CAST(p[OFFSET(8)] AS INT64) AS char_offset
  FROM locs
  WHERE ARRAY_LENGTH(p) >= 9
    AND p[OFFSET(0)] = '3'            -- 3 = US city or landmark
    AND p[OFFSET(2)] = 'US'
    AND REGEXP_CONTAINS(p[OFFSET(4)], r'^[A-Z]{2}[0-9]{3}$')
),
-- One county per article: the earliest-mentioned US city. Avoids counting
-- every town named in a round-up piece.
first_mention AS (
  SELECT url, pub_date, tone, adm2
  FROM us_city
  QUALIFY ROW_NUMBER() OVER (PARTITION BY url ORDER BY char_offset) = 1
),
state_fips AS (
  SELECT * FROM UNNEST([
    STRUCT('AL' AS abbr, '01' AS fips), ('AK','02'), ('AZ','04'), ('AR','05'), ('CA','06'),
    ('CO','08'), ('CT','09'), ('DE','10'), ('DC','11'), ('FL','12'), ('GA','13'), ('HI','15'),
    ('ID','16'), ('IL','17'), ('IN','18'), ('IA','19'), ('KS','20'), ('KY','21'), ('LA','22'),
    ('ME','23'), ('MD','24'), ('MA','25'), ('MI','26'), ('MN','27'), ('MS','28'), ('MO','29'),
    ('MT','30'), ('NE','31'), ('NV','32'), ('NH','33'), ('NJ','34'), ('NM','35'), ('NY','36'),
    ('NC','37'), ('ND','38'), ('OH','39'), ('OK','40'), ('OR','41'), ('PA','42'), ('RI','44'),
    ('SC','45'), ('SD','46'), ('TN','47'), ('TX','48'), ('UT','49'), ('VT','50'), ('VA','51'),
    ('WA','53'), ('WV','54'), ('WI','55'), ('WY','56')
  ])
)
SELECT
  CONCAT(s.fips, SUBSTR(f.adm2, 3, 3)) AS fips,
  FORMAT_DATE('%Y-Q%Q', f.pub_date) AS quarter,
  COUNT(*) AS article_count,
  AVG(f.tone) AS mean_tone,
  AVG(IF(f.tone < -2, 1, 0)) AS share_negative
FROM first_mention f
JOIN state_fips s ON s.abbr = SUBSTR(f.adm2, 1, 2)
GROUP BY fips, quarter
ORDER BY article_count DESC;
