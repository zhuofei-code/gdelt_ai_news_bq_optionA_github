-- name: all_countries_monthly_panel
-- BigQuery Standard SQL
-- Parameters:
--   @start_date       DATE
--   @end_date         DATE (exclusive)
--   @strict_regex     STRING
--   @context_regex    STRING
--   @ai_abbrev_regex  STRING
--   @country_domain_map ARRAY<STRING> with format "CC|domain"

WITH domain_country_map AS (
  SELECT
    SPLIT(map_value, '|')[SAFE_OFFSET(0)] AS country,
    SPLIT(map_value, '|')[SAFE_OFFSET(1)] AS domain
  FROM UNNEST(@country_domain_map) AS map_value
  WHERE ARRAY_LENGTH(SPLIT(map_value, '|')) = 2
),
base AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS event_date,
    DATE_TRUNC(PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)), MONTH) AS month_date,
    LOWER(IFNULL(NET.HOST(DocumentIdentifier), '')) AS host,
    IFNULL(DocumentIdentifier, '') AS article_id,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone,
    LOWER(
      CONCAT(
        REPLACE(IFNULL(V2Themes, ''), '_', ' '), ' ',
        REPLACE(IFNULL(Themes, ''), '_', ' '), ' ',
        IFNULL(V2Persons, ''), ' ',
        IFNULL(V2Organizations, ''), ' ',
        IFNULL(AllNames, ''), ' ',
        IFNULL(Locations, '')
      )
    ) AS ai_text
  FROM `{{GDELT_TABLE}}`
  WHERE DATE(_PARTITIONTIME) >= @start_date
    AND DATE(_PARTITIONTIME) < @end_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) >= @start_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) < @end_date
    AND DocumentIdentifier IS NOT NULL
    AND DocumentIdentifier != ''
),
domain_filtered AS (
  SELECT
    b.event_date,
    b.month_date,
    m.country,
    b.article_id,
    b.tone,
    b.ai_text
  FROM base AS b
  JOIN domain_country_map AS m
    ON b.host = m.domain OR ENDS_WITH(b.host, CONCAT('.', m.domain))
),
doc_month AS (
  SELECT
    country,
    month_date,
    article_id,
    AVG(tone) AS doc_tone,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @strict_regex)) AS strict_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @ai_abbrev_regex)) AS abbrev_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @context_regex)) AS context_match
  FROM domain_filtered
  GROUP BY country, month_date, article_id
),
monthly AS (
  SELECT
    country,
    month_date,
    COUNT(*) AS all_articles,
    COUNTIF(strict_match) AS ai_articles_strict,
    AVG(IF(strict_match, doc_tone, NULL)) AS ai_tone_strict,
    COUNTIF((strict_match OR (abbrev_match AND context_match))) AS ai_articles_balanced,
    AVG(IF((strict_match OR (abbrev_match AND context_match)), doc_tone, NULL)) AS ai_tone_balanced
  FROM doc_month
  GROUP BY country, month_date
),
countries AS (
  SELECT DISTINCT country
  FROM domain_country_map
),
month_grid AS (
  SELECT month_date
  FROM UNNEST(
    GENERATE_DATE_ARRAY(
      DATE_TRUNC(@start_date, MONTH),
      DATE_TRUNC(DATE_SUB(@end_date, INTERVAL 1 DAY), MONTH),
      INTERVAL 1 MONTH
    )
  ) AS month_date
),
country_month_grid AS (
  SELECT c.country, mg.month_date
  FROM countries AS c
  CROSS JOIN month_grid AS mg
)
SELECT
  cmg.country AS country,
  cmg.month_date AS month,
  COALESCE(m.all_articles, 0) AS all_articles,
  COALESCE(m.ai_articles_strict, 0) AS ai_articles_strict,
  m.ai_tone_strict AS ai_tone_strict,
  COALESCE(m.ai_articles_balanced, 0) AS ai_articles_balanced,
  m.ai_tone_balanced AS ai_tone_balanced
FROM country_month_grid AS cmg
LEFT JOIN monthly AS m
  ON cmg.country = m.country
 AND cmg.month_date = m.month_date
ORDER BY country, month;

-- name: country_monthly_panel
-- BigQuery Standard SQL
-- Parameters:
--   @country          STRING
--   @start_date       DATE
--   @end_date         DATE
--   @domains          ARRAY<STRING>
--   @strict_regex     STRING
--   @context_regex    STRING
--   @ai_abbrev_regex  STRING

WITH base AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS event_date,
    DATE_TRUNC(PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)), MONTH) AS month_date,
    LOWER(IFNULL(NET.HOST(DocumentIdentifier), '')) AS host,
    IFNULL(DocumentIdentifier, '') AS article_id,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone,
    LOWER(
      CONCAT(
        REPLACE(IFNULL(V2Themes, ''), '_', ' '), ' ',
        REPLACE(IFNULL(Themes, ''), '_', ' '), ' ',
        IFNULL(V2Persons, ''), ' ',
        IFNULL(V2Organizations, ''), ' ',
        IFNULL(AllNames, ''), ' ',
        IFNULL(Locations, '')
      )
    ) AS ai_text
  FROM `{{GDELT_TABLE}}`
  WHERE DATE(_PARTITIONTIME) >= @start_date
    AND DATE(_PARTITIONTIME) < @end_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) >= @start_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) < @end_date
    AND DocumentIdentifier IS NOT NULL
    AND DocumentIdentifier != ''
),
domain_filtered AS (
  SELECT *
  FROM base
  WHERE EXISTS (
    SELECT 1
    FROM UNNEST(@domains) AS d
    WHERE host = d OR ENDS_WITH(host, CONCAT('.', d))
  )
),
doc_month AS (
  SELECT
    month_date,
    article_id,
    AVG(tone) AS doc_tone,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @strict_regex)) AS strict_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @ai_abbrev_regex)) AS abbrev_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @context_regex)) AS context_match
  FROM domain_filtered
  GROUP BY month_date, article_id
),
doc_flags AS (
  SELECT
    month_date,
    article_id,
    doc_tone,
    strict_match,
    (strict_match OR (abbrev_match AND context_match)) AS balanced_match
  FROM doc_month
),
monthly AS (
  SELECT
    month_date,
    COUNT(*) AS all_articles,
    COUNTIF(strict_match) AS ai_articles_strict,
    AVG(IF(strict_match, doc_tone, NULL)) AS ai_tone_strict,
    COUNTIF(balanced_match) AS ai_articles_balanced,
    AVG(IF(balanced_match, doc_tone, NULL)) AS ai_tone_balanced
  FROM doc_flags
  GROUP BY month_date
),
month_grid AS (
  SELECT month_date
  FROM UNNEST(
    GENERATE_DATE_ARRAY(
      DATE_TRUNC(@start_date, MONTH),
      DATE_TRUNC(DATE_SUB(@end_date, INTERVAL 1 DAY), MONTH),
      INTERVAL 1 MONTH
    )
  ) AS month_date
)
SELECT
  @country AS country,
  mg.month_date AS month,
  COALESCE(m.all_articles, 0) AS all_articles,
  COALESCE(m.ai_articles_strict, 0) AS ai_articles_strict,
  m.ai_tone_strict AS ai_tone_strict,
  COALESCE(m.ai_articles_balanced, 0) AS ai_articles_balanced,
  m.ai_tone_balanced AS ai_tone_balanced
FROM month_grid AS mg
LEFT JOIN monthly AS m USING (month_date)
ORDER BY month;

-- name: sanity_sample
-- BigQuery Standard SQL
-- Parameters:
--   @start_date          DATE
--   @end_exclusive_date  DATE
--   @domains             ARRAY<STRING>
--   @strict_regex        STRING
--   @context_regex       STRING
--   @ai_abbrev_regex     STRING
--   @sanity_mode         STRING
--   @limit_rows          INT64

WITH base AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS event_date,
    DATE_TRUNC(PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)), MONTH) AS month_date,
    LOWER(IFNULL(NET.HOST(DocumentIdentifier), '')) AS host,
    IFNULL(DocumentIdentifier, '') AS article_id,
    SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone,
    LOWER(
      CONCAT(
        REPLACE(IFNULL(V2Themes, ''), '_', ' '), ' ',
        REPLACE(IFNULL(Themes, ''), '_', ' '), ' ',
        IFNULL(V2Persons, ''), ' ',
        IFNULL(V2Organizations, ''), ' ',
        IFNULL(AllNames, ''), ' ',
        IFNULL(Locations, '')
      )
    ) AS ai_text
  FROM `{{GDELT_TABLE}}`
  WHERE DATE(_PARTITIONTIME) >= @start_date
    AND DATE(_PARTITIONTIME) < @end_exclusive_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) >= @start_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) < @end_exclusive_date
    AND DocumentIdentifier IS NOT NULL
    AND DocumentIdentifier != ''
),
domain_filtered AS (
  SELECT *
  FROM base
  WHERE EXISTS (
    SELECT 1
    FROM UNNEST(@domains) AS d
    WHERE host = d OR ENDS_WITH(host, CONCAT('.', d))
  )
),
doc_sample AS (
  SELECT
    month_date,
    host,
    article_id,
    MAX(event_date) AS event_date,
    AVG(tone) AS tone,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @strict_regex)) AS strict_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @ai_abbrev_regex)) AS abbrev_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @context_regex)) AS context_match
  FROM domain_filtered
  GROUP BY month_date, host, article_id
),
doc_flags AS (
  SELECT
    month_date,
    host,
    article_id,
    event_date,
    tone,
    strict_match,
    (strict_match OR (abbrev_match AND context_match)) AS balanced_match
  FROM doc_sample
)
SELECT
  month_date AS month,
  host AS domain,
  article_id AS url,
  CAST(NULL AS STRING) AS title,
  tone
FROM doc_flags
WHERE (
  (@sanity_mode = 'strict' AND strict_match)
  OR
  (@sanity_mode = 'balanced' AND balanced_match)
)
ORDER BY event_date DESC
LIMIT @limit_rows;

-- name: debug_counts
-- BigQuery Standard SQL
-- Parameters:
--   @start_date          DATE
--   @end_exclusive_date  DATE
--   @domains             ARRAY<STRING>
--   @strict_regex        STRING
--   @context_regex       STRING
--   @ai_abbrev_regex     STRING

WITH base AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS event_date,
    LOWER(IFNULL(NET.HOST(DocumentIdentifier), '')) AS host,
    IFNULL(DocumentIdentifier, '') AS article_id,
    LOWER(
      CONCAT(
        REPLACE(IFNULL(V2Themes, ''), '_', ' '), ' ',
        REPLACE(IFNULL(Themes, ''), '_', ' '), ' ',
        IFNULL(V2Persons, ''), ' ',
        IFNULL(V2Organizations, ''), ' ',
        IFNULL(AllNames, ''), ' ',
        IFNULL(Locations, '')
      )
    ) AS ai_text
  FROM `{{GDELT_TABLE}}`
  WHERE DATE(_PARTITIONTIME) >= @start_date
    AND DATE(_PARTITIONTIME) < @end_exclusive_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) >= @start_date
    AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) < @end_exclusive_date
    AND DocumentIdentifier IS NOT NULL
    AND DocumentIdentifier != ''
),
domain_filtered AS (
  SELECT *
  FROM base
  WHERE EXISTS (
    SELECT 1
    FROM UNNEST(@domains) AS d
    WHERE host = d OR ENDS_WITH(host, CONCAT('.', d))
  )
),
doc_flags AS (
  SELECT
    article_id,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @strict_regex)) AS strict_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @ai_abbrev_regex)) AS abbrev_match,
    LOGICAL_OR(REGEXP_CONTAINS(ai_text, @context_regex)) AS context_match
  FROM domain_filtered
  GROUP BY article_id
)
SELECT
  COUNT(*) AS n_all,
  COUNTIF(strict_match) AS n_strict,
  COUNTIF(abbrev_match) AS n_abbrev,
  COUNTIF(context_match) AS n_context,
  COUNTIF(abbrev_match AND context_match) AS n_abbrev_and_context,
  COUNTIF(strict_match OR (abbrev_match AND context_match)) AS n_balanced
FROM doc_flags;
