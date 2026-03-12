#!/usr/bin/env python3
"""GDELT AI news monthly panel via BigQuery."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from dateutil.relativedelta import relativedelta
from google.api_core.exceptions import BadRequest
from google.api_core.exceptions import Forbidden
from google.api_core.exceptions import NotFound
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery
from tqdm import tqdm

# Keyword mode
KEYWORDS_MODE = "strict+balanced"

# Smoke/full toggles
COUNTRY_FILTER: list[str] | None = None
SMOKE_TEST = False
SMOKE_MONTHS = 3
SMOKE_DOMAIN_LIMIT: int | None = None
SMOKE_KEYWORD_LIMIT = 0  # 0 means no limit
FULL_YEARS = 10
DOMAIN_LIMIT: int | None = None

# Fixed full-run window, end is exclusive
USE_FIXED_WINDOW = True
START_DATE_UTC = "2018-06-01T00:00:00Z"
END_DATE_UTC = "2025-06-01T00:00:00Z"

# Tiny sanity check toggles
SANITY_CHECK = False
SANITY_COUNTRY = "UK"
SANITY_MONTHS = 1
SANITY_DOMAIN_LIMIT = 1
SANITY_LIMIT_ROWS = 30
SANITY_MODE = "balanced"  # strict or balanced

# Tiny debug counts toggles
DEBUG_COUNTS = False
DEBUG_COUNTRY = "UK"
DEBUG_MONTHS = 1
DEBUG_DOMAIN_LIMIT = 1

COUNTRY_QUERY_MAX_RETRIES = 3
COUNTRY_QUERY_RETRY_BASE_SECONDS = 3
MAXIMUM_BYTES_BILLED: int | None = 50 * 1024**3
ZERO_MONTH_WARNING_THRESHOLD_RATIO = 0.2
GDELT_TABLE = os.getenv("GDELT_TABLE", "gdelt-bq.gdeltv2.gkg_partitioned")
AUTO_MONTHLY_FALLBACK_ON_BYTES_LIMIT = True
INITIAL_CHUNK_MONTHS = 12
BQ_ONDEMAND_USD_PER_TIB = float(os.getenv("BQ_ONDEMAND_USD_PER_TIB", "6.25"))
GBP_TO_USD = float(os.getenv("GBP_TO_USD", "1.28"))
BUDGET_GBP_LIMIT = float(os.getenv("BUDGET_GBP_LIMIT", "300"))
MAX_TOTAL_BYTES_BUDGET = int((BUDGET_GBP_LIMIT * GBP_TO_USD / BQ_ONDEMAND_USD_PER_TIB) * (1024**4))

# Match AI and A.I. as standalone tokens (RE2-safe, lowercase)
AI_ABBREV_REGEX = r"(?:^|[^a-z0-9])(?:ai|a\.i\.)(?:[^a-z0-9]|$)"
DEFAULT_ABBREVIATION_TERMS = ["ai", "a.i."]

# Optional explicit project override (otherwise uses ADC default project)
BIGQUERY_PROJECT = os.getenv("BQ_PROJECT", "")

start_date_override = os.getenv("START_DATE_UTC", "").strip()
if start_date_override:
    START_DATE_UTC = start_date_override

end_date_override = os.getenv("END_DATE_UTC", "").strip()
if end_date_override:
    END_DATE_UTC = end_date_override

# Optional runtime overrides for one-country-at-a-time execution.
country_filter_override = os.getenv("COUNTRY_FILTER", "").strip()
if country_filter_override:
    COUNTRY_FILTER = [c.strip().upper() for c in country_filter_override.split(",") if c.strip()]

domain_limit_override = os.getenv("DOMAIN_LIMIT", "").strip()
if domain_limit_override:
    DOMAIN_LIMIT = int(domain_limit_override)

max_bytes_override = os.getenv("MAXIMUM_BYTES_BILLED", "").strip()
if max_bytes_override:
    parsed_max = int(max_bytes_override)
    MAXIMUM_BYTES_BILLED = parsed_max if parsed_max > 0 else None

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PACKAGE_ROOT / "config"
sources_file_override = os.getenv("SOURCES_FILE", "").strip()
if sources_file_override:
    sources_path_candidate = Path(sources_file_override)
    if not sources_path_candidate.is_absolute():
        sources_path_candidate = PACKAGE_ROOT / sources_path_candidate
    SOURCES_PATH = sources_path_candidate.resolve()
else:
    SOURCES_PATH = CONFIG_DIR / "sources_v2_optionA.yaml"
keyword_rules_file_override = os.getenv("KEYWORD_RULES_FILE", "").strip()
KEYWORD_RULES_PATH: Path | None = None
if keyword_rules_file_override:
    keyword_rules_path_candidate = Path(keyword_rules_file_override)
    if not keyword_rules_path_candidate.is_absolute():
        keyword_rules_path_candidate = PACKAGE_ROOT / keyword_rules_path_candidate
    KEYWORD_RULES_PATH = keyword_rules_path_candidate.resolve()
output_suffix_raw = os.getenv("OUTPUT_SUFFIX", "").strip()
OUTPUT_SUFFIX = ""
if output_suffix_raw:
    safe_suffix = re.sub(r"[^A-Za-z0-9._-]+", "_", output_suffix_raw)
    if safe_suffix:
        OUTPUT_SUFFIX = f"_{safe_suffix}"


def make_window_tag(start_utc: str, end_utc: str) -> str:
    start_dt = datetime.strptime(start_utc[:10], "%Y-%m-%d")
    end_dt = datetime.strptime(end_utc[:10], "%Y-%m-%d")
    return f"{start_dt.strftime('%Y%m')}_{end_dt.strftime('%Y%m')}"


OUTPUT_WINDOW_TAG = make_window_tag(START_DATE_UTC, END_DATE_UTC)
KEYWORDS_STRICT_PATH = CONFIG_DIR / "keywords_strict.txt"
KEYWORDS_CONTEXT_PATH = CONFIG_DIR / "keywords_context.txt"
SQL_PATH = SCRIPT_DIR / "bq_queries.sql"
OUTPUT_DIR = PACKAGE_ROOT / "results"
OUTPUT_PATH = OUTPUT_DIR / f"gdelt_ai_country_monthly_{OUTPUT_WINDOW_TAG}{OUTPUT_SUFFIX}.csv"
LOG_PATH = OUTPUT_DIR / f"fullrun_log_{OUTPUT_WINDOW_TAG}{OUTPUT_SUFFIX}.txt"


def load_sources() -> dict[str, Any]:
    with SOURCES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    countries = data.get("countries", {})
    if not isinstance(countries, dict) or not countries:
        raise RuntimeError("Invalid sources.yaml: missing countries mapping")
    return countries


def load_keywords(file_path: Path) -> list[str]:
    with file_path.open("r", encoding="utf-8") as f:
        keywords = [line.strip().lower() for line in f if line.strip()]
    if not keywords:
        raise RuntimeError(f"Keyword file is empty: {file_path}")
    return keywords


def normalize_phrase_list(values: list[Any]) -> list[str]:
    phrases = [str(value).strip().lower() for value in values if str(value).strip()]
    return dedupe_preserve_order(phrases)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def escape_regex(phrase: str) -> str:
    return re.escape(phrase)


def make_boundary_pattern(phrase: str) -> str:
    return rf"(?:^|[^a-z0-9]){escape_regex(phrase)}(?:[^a-z0-9]|$)"


def build_regex_from_phrases(phrases: list[str]) -> str:
    clean_phrases = dedupe_preserve_order([p.strip().lower() for p in phrases if p.strip()])
    if not clean_phrases:
        raise RuntimeError("No phrases available to build regex")
    patterns = [make_boundary_pattern(phrase) for phrase in clean_phrases]
    return "(" + "|".join(patterns) + ")"


def resolve_config_reference(base_dir: Path, file_ref: str) -> Path:
    candidate = Path(file_ref)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def load_keywords_from_files(file_paths: list[Path]) -> list[str]:
    phrases: list[str] = []
    for file_path in file_paths:
        phrases.extend(load_keywords(file_path))
    return dedupe_preserve_order(phrases)


def build_country_keyword_rules(
    countries: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if KEYWORD_RULES_PATH is None:
        strict_keywords = load_keywords(KEYWORDS_STRICT_PATH)
        if SMOKE_TEST and SMOKE_KEYWORD_LIMIT > 0:
            strict_keywords = strict_keywords[:SMOKE_KEYWORD_LIMIT]

        context_keywords = load_keywords(KEYWORDS_CONTEXT_PATH)
        strict_regex = build_regex_from_phrases(strict_keywords)
        context_regex = build_regex_from_phrases(context_keywords)

        country_rules = {
            country_code: {
                "strict_keywords": list(strict_keywords),
                "context_keywords": list(context_keywords),
                "abbreviation_terms": list(DEFAULT_ABBREVIATION_TERMS),
                "strict_regex": strict_regex,
                "context_regex": context_regex,
                "ai_abbrev_regex": AI_ABBREV_REGEX,
                "languages": ["en"],
                "context_languages": ["en"],
            }
            for country_code in countries
        }
        strategy_info = {
            "version": "legacy_global",
            "rules_file": "",
            "strict_base_files": [str(KEYWORDS_STRICT_PATH.name)],
            "context_files": {"en": str(KEYWORDS_CONTEXT_PATH.name)},
            "default_abbreviation_terms": list(DEFAULT_ABBREVIATION_TERMS),
            "strict_keyword_count": len(strict_keywords),
            "context_languages_used": ["en"],
        }
        return country_rules, strategy_info

    with KEYWORD_RULES_PATH.open("r", encoding="utf-8") as f:
        rules_data = yaml.safe_load(f) or {}

    metadata = rules_data.get("metadata", {})
    country_cfg_map = rules_data.get("countries", {})
    if not isinstance(country_cfg_map, dict):
        raise RuntimeError(f"Invalid keyword rules file: missing countries mapping in {KEYWORD_RULES_PATH}")

    rules_base_dir = KEYWORD_RULES_PATH.parent
    strict_base_refs = metadata.get("strict_base_files", [KEYWORDS_STRICT_PATH.name])
    if not isinstance(strict_base_refs, list) or not strict_base_refs:
        raise RuntimeError(f"Invalid keyword rules file: strict_base_files missing in {KEYWORD_RULES_PATH}")
    strict_base_paths = [resolve_config_reference(rules_base_dir, str(ref)) for ref in strict_base_refs]
    strict_base_keywords = load_keywords_from_files(strict_base_paths)

    context_file_map_raw = metadata.get("context_files", {})
    if not isinstance(context_file_map_raw, dict) or not context_file_map_raw:
        raise RuntimeError(f"Invalid keyword rules file: context_files missing in {KEYWORD_RULES_PATH}")
    context_file_map = {
        str(lang).strip().lower(): resolve_config_reference(rules_base_dir, str(file_ref))
        for lang, file_ref in context_file_map_raw.items()
        if str(lang).strip()
    }
    if not context_file_map:
        raise RuntimeError(f"Invalid keyword rules file: no usable context_files in {KEYWORD_RULES_PATH}")

    default_context_languages = normalize_phrase_list(metadata.get("default_context_languages", ["en"]))
    default_abbreviation_terms = normalize_phrase_list(
        metadata.get("default_abbreviation_terms", DEFAULT_ABBREVIATION_TERMS)
    )
    if not default_abbreviation_terms:
        raise RuntimeError(f"Invalid keyword rules file: no default_abbreviation_terms in {KEYWORD_RULES_PATH}")

    country_rules: dict[str, dict[str, Any]] = {}
    context_languages_used: set[str] = set()

    for country_code in countries:
        rule_cfg = country_cfg_map.get(country_code, {})
        if rule_cfg is None:
            rule_cfg = {}
        if not isinstance(rule_cfg, dict):
            raise RuntimeError(
                f"Invalid keyword rules file: country rule for {country_code} must be a mapping"
            )

        strict_terms = list(strict_base_keywords)
        strict_extra_file_refs = rule_cfg.get("strict_extra_files", [])
        if strict_extra_file_refs:
            if not isinstance(strict_extra_file_refs, list):
                raise RuntimeError(
                    f"Invalid keyword rules file: strict_extra_files for {country_code} must be a list"
                )
            strict_extra_paths = [
                resolve_config_reference(rules_base_dir, str(file_ref)) for file_ref in strict_extra_file_refs
            ]
            strict_terms.extend(load_keywords_from_files(strict_extra_paths))
        strict_terms.extend(normalize_phrase_list(rule_cfg.get("strict_extra_terms", [])))
        strict_terms = dedupe_preserve_order(strict_terms)
        if SMOKE_TEST and SMOKE_KEYWORD_LIMIT > 0:
            strict_terms = strict_terms[:SMOKE_KEYWORD_LIMIT]

        context_languages = normalize_phrase_list(rule_cfg.get("context_languages", default_context_languages))
        if not context_languages:
            raise RuntimeError(f"Invalid keyword rules file: context_languages empty for {country_code}")

        context_paths: list[Path] = []
        for language_code in context_languages:
            context_path = context_file_map.get(language_code)
            if context_path is None:
                raise RuntimeError(
                    f"Invalid keyword rules file: no context file for language '{language_code}'"
                )
            context_paths.append(context_path)
        context_terms = load_keywords_from_files(context_paths)
        context_terms.extend(normalize_phrase_list(rule_cfg.get("context_extra_terms", [])))
        context_terms = dedupe_preserve_order(context_terms)

        abbreviation_terms_raw = rule_cfg.get("abbreviation_terms")
        if abbreviation_terms_raw is None:
            abbreviation_terms = list(default_abbreviation_terms)
        else:
            abbreviation_terms = normalize_phrase_list(abbreviation_terms_raw)
        if not abbreviation_terms:
            raise RuntimeError(f"Invalid keyword rules file: abbreviation_terms empty for {country_code}")

        languages = normalize_phrase_list(rule_cfg.get("languages", []))
        strict_regex = build_regex_from_phrases(strict_terms)
        context_regex = build_regex_from_phrases(context_terms)
        ai_abbrev_regex = build_regex_from_phrases(abbreviation_terms)

        country_rules[country_code] = {
            "strict_keywords": strict_terms,
            "context_keywords": context_terms,
            "abbreviation_terms": abbreviation_terms,
            "strict_regex": strict_regex,
            "context_regex": context_regex,
            "ai_abbrev_regex": ai_abbrev_regex,
            "languages": languages,
            "context_languages": context_languages,
        }
        context_languages_used.update(context_languages)

    strategy_info = {
        "version": str(metadata.get("version", "country_rules")),
        "rules_file": str(KEYWORD_RULES_PATH),
        "strict_base_files": [str(path.name) for path in strict_base_paths],
        "context_files": {lang: str(path.name) for lang, path in context_file_map.items()},
        "default_abbreviation_terms": list(default_abbreviation_terms),
        "strict_keyword_count": len(strict_base_keywords),
        "context_languages_used": sorted(context_languages_used),
    }
    return country_rules, strategy_info


def parse_utc_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def get_time_window(smoke_test: bool) -> tuple[datetime, datetime]:
    if USE_FIXED_WINDOW:
        start_dt = parse_utc_datetime(START_DATE_UTC)
        end_dt = parse_utc_datetime(END_DATE_UTC)
        if start_dt >= end_dt:
            raise RuntimeError("START_DATE_UTC must be earlier than END_DATE_UTC")
        return start_dt, end_dt

    end_dt = datetime.now(timezone.utc).replace(microsecond=0)
    if smoke_test:
        start_candidate = end_dt - relativedelta(months=SMOKE_MONTHS)
    else:
        start_candidate = end_dt - relativedelta(years=FULL_YEARS)

    start_dt = start_candidate.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_dt, end_dt


def get_sanity_time_window() -> tuple[datetime, datetime]:
    if SANITY_MONTHS <= 0:
        raise RuntimeError("SANITY_MONTHS must be >= 1")

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    end_exclusive = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_exclusive - relativedelta(months=SANITY_MONTHS)
    return start_dt, end_exclusive


def get_debug_time_window() -> tuple[datetime, datetime]:
    if DEBUG_MONTHS <= 0:
        raise RuntimeError("DEBUG_MONTHS must be >= 1")

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    end_exclusive = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_exclusive - relativedelta(months=DEBUG_MONTHS)
    return start_dt, end_exclusive


def month_starts(start_dt: datetime, end_dt: datetime) -> list[datetime]:
    starts: list[datetime] = []
    cursor = start_dt
    while cursor < end_dt:
        starts.append(cursor)
        cursor += relativedelta(months=1)
    return starts


def month_end(month_start: datetime, end_dt: datetime) -> datetime:
    next_month = month_start + relativedelta(months=1)
    return min(next_month, end_dt)


def month_diff(start_dt: datetime, end_dt: datetime) -> int:
    return (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)


def load_sql_templates() -> dict[str, str]:
    text = SQL_PATH.read_text(encoding="utf-8")
    templates: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.lower().startswith("-- name:"):
            if current_name is not None:
                templates[current_name] = "\n".join(current_lines).strip()
            current_name = line.split(":", 1)[1].strip()
            current_lines = []
            continue
        if current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        templates[current_name] = "\n".join(current_lines).strip()

    if not templates:
        raise RuntimeError(f"No SQL templates found in {SQL_PATH}")
    return templates


def render_sql_template(sql: str) -> str:
    return sql.replace("{{GDELT_TABLE}}", GDELT_TABLE)


def build_country_domain_map_values(countries: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for country_code, cfg in countries.items():
        for domain in cfg.get("domains", []):
            domain_value = str(domain).strip().lower()
            if domain_value:
                values.append(f"{country_code}|{domain_value}")
    if not values:
        raise RuntimeError("No domains available to build country-domain map values")
    return values


def build_country_rule_map_values(country_rules: dict[str, dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for country_code, rule in country_rules.items():
        payload = {
            "country": country_code,
            "strict_regex": rule["strict_regex"],
            "context_regex": rule["context_regex"],
            "ai_abbrev_regex": rule["ai_abbrev_regex"],
        }
        values.append(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    if not values:
        raise RuntimeError("No keyword rules available to build country-rule map values")
    return values


def render_all_countries_sql(sql: str) -> str:
    return render_sql_template(sql)


def get_sql_template(templates: dict[str, str], name: str) -> str:
    sql = templates.get(name, "").strip()
    if not sql:
        raise RuntimeError(f"Missing SQL template '{name}' in {SQL_PATH}")
    return sql


def prepare_countries(countries: dict[str, Any]) -> dict[str, Any]:
    if COUNTRY_FILTER:
        countries = {code: countries[code] for code in COUNTRY_FILTER if code in countries}
    if not countries:
        raise RuntimeError(f"No countries left after COUNTRY_FILTER={COUNTRY_FILTER}")

    effective_limit = DOMAIN_LIMIT
    if effective_limit is None and SMOKE_TEST:
        effective_limit = SMOKE_DOMAIN_LIMIT

    if effective_limit is None or effective_limit <= 0:
        return countries

    trimmed: dict[str, Any] = {}
    for code, cfg in countries.items():
        new_cfg = dict(cfg)
        domains = list(cfg.get("domains", []))
        new_cfg["domains"] = domains[:effective_limit]
        trimmed[code] = new_cfg
    return trimmed


def preflight_sql_access(client: bigquery.Client) -> int:
    """Dry-run a minimal query against GDELT public table."""
    if GDELT_TABLE.endswith("gkg_partitioned"):
        date_filter = "DATE(_PARTITIONTIME) >= DATE '2020-01-01' AND DATE(_PARTITIONTIME) < DATE '2020-01-02'"
    else:
        date_filter = (
            "PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) >= DATE '2020-01-01' "
            "AND PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) < DATE '2020-01-02'"
        )
    preflight_sql = """
    SELECT DATE, DocumentIdentifier
    FROM `__GDELT_TABLE__`
    WHERE __DATE_FILTER__
    LIMIT 1
    """
    preflight_sql = preflight_sql.replace("__GDELT_TABLE__", GDELT_TABLE).replace("__DATE_FILTER__", date_filter)
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        use_legacy_sql=False,
    )
    dry_run_job = client.query(preflight_sql, job_config=job_config)
    return int(dry_run_job.total_bytes_processed or 0)


def run_country_query(
    client: bigquery.Client,
    sql: str,
    country_code: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    query_params = [
        bigquery.ScalarQueryParameter("country", "STRING", country_code),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_dt.date()),
        bigquery.ArrayQueryParameter("domains", "STRING", [d.lower() for d in domains]),
        bigquery.ScalarQueryParameter("strict_regex", "STRING", strict_regex),
        bigquery.ScalarQueryParameter("context_regex", "STRING", context_regex),
        bigquery.ScalarQueryParameter("ai_abbrev_regex", "STRING", ai_abbrev_regex),
    ]
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_params,
        use_legacy_sql=False,
        maximum_bytes_billed=MAXIMUM_BYTES_BILLED,
    )

    rows: list[dict[str, Any]] = []
    query_job = client.query(sql, job_config=job_config)
    for row in query_job.result():
        rows.append(
            {
                "country": row["country"],
                "month": row["month"],
                "all_articles": int(row["all_articles"] or 0),
                "ai_articles_strict": int(row["ai_articles_strict"] or 0),
                "ai_tone_strict": float(row["ai_tone_strict"])
                if row["ai_tone_strict"] is not None
                else math.nan,
                "ai_articles_balanced": int(row["ai_articles_balanced"] or 0),
                "ai_tone_balanced": float(row["ai_tone_balanced"])
                if row["ai_tone_balanced"] is not None
                else math.nan,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "country",
                "month",
                "all_articles",
                "ai_articles_strict",
                "ai_tone_strict",
                "ai_articles_balanced",
                "ai_tone_balanced",
            ]
        )
    return pd.DataFrame(rows)


def run_country_query_with_retries(
    client: bigquery.Client,
    sql: str,
    country_code: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    start_dt: datetime,
    end_dt: datetime,
    retry_label: str,
) -> tuple[pd.DataFrame, Exception | None]:
    country_query_df = pd.DataFrame(
        columns=[
            "country",
            "month",
            "all_articles",
            "ai_articles_strict",
            "ai_tone_strict",
            "ai_articles_balanced",
            "ai_tone_balanced",
        ]
    )
    last_error: Exception | None = None

    for attempt in range(1, COUNTRY_QUERY_MAX_RETRIES + 1):
        try:
            country_query_df = run_country_query(
                client=client,
                sql=sql,
                country_code=country_code,
                domains=domains,
                strict_regex=strict_regex,
                context_regex=context_regex,
                ai_abbrev_regex=ai_abbrev_regex,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            last_error = None
            break
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if attempt < COUNTRY_QUERY_MAX_RETRIES:
                sleep_seconds = COUNTRY_QUERY_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                print(
                    f"[WARN] {retry_label} query failed attempt {attempt}/"
                    f"{COUNTRY_QUERY_MAX_RETRIES}: {exc}. Retrying in {sleep_seconds}s..."
                )
                time.sleep(sleep_seconds)
            else:
                print(
                    f"[ERROR] {retry_label} query failed after "
                    f"{COUNTRY_QUERY_MAX_RETRIES} attempts: {exc}"
                )

    return country_query_df, last_error


def estimate_country_query_bytes(
    client: bigquery.Client,
    sql: str,
    country_code: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    query_params = [
        bigquery.ScalarQueryParameter("country", "STRING", country_code),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_dt.date()),
        bigquery.ArrayQueryParameter("domains", "STRING", [d.lower() for d in domains]),
        bigquery.ScalarQueryParameter("strict_regex", "STRING", strict_regex),
        bigquery.ScalarQueryParameter("context_regex", "STRING", context_regex),
        bigquery.ScalarQueryParameter("ai_abbrev_regex", "STRING", ai_abbrev_regex),
    ]
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_params,
        use_legacy_sql=False,
        dry_run=True,
        use_query_cache=False,
    )
    dry_run_job = client.query(sql, job_config=job_config)
    return int(dry_run_job.total_bytes_processed or 0)


def run_all_countries_query(
    client: bigquery.Client,
    sql: str,
    country_domain_map_values: list[str],
    country_rule_map_values: list[str],
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    query_params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_dt.date()),
        bigquery.ArrayQueryParameter("country_domain_map", "STRING", country_domain_map_values),
        bigquery.ArrayQueryParameter("country_rule_map", "STRING", country_rule_map_values),
    ]
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_params,
        use_legacy_sql=False,
        maximum_bytes_billed=MAXIMUM_BYTES_BILLED,
    )

    rows: list[dict[str, Any]] = []
    query_job = client.query(sql, job_config=job_config)
    for row in query_job.result():
        rows.append(
            {
                "country": row["country"],
                "month": row["month"],
                "all_articles": int(row["all_articles"] or 0),
                "ai_articles_strict": int(row["ai_articles_strict"] or 0),
                "ai_tone_strict": float(row["ai_tone_strict"])
                if row["ai_tone_strict"] is not None
                else math.nan,
                "ai_articles_balanced": int(row["ai_articles_balanced"] or 0),
                "ai_tone_balanced": float(row["ai_tone_balanced"])
                if row["ai_tone_balanced"] is not None
                else math.nan,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "country",
            "month",
            "all_articles",
            "ai_articles_strict",
            "ai_tone_strict",
            "ai_articles_balanced",
            "ai_tone_balanced",
        ],
    )


def run_all_countries_query_with_retries(
    client: bigquery.Client,
    sql: str,
    country_domain_map_values: list[str],
    country_rule_map_values: list[str],
    start_dt: datetime,
    end_dt: datetime,
    retry_label: str,
) -> tuple[pd.DataFrame, Exception | None]:
    query_df = pd.DataFrame(
        columns=[
            "country",
            "month",
            "all_articles",
            "ai_articles_strict",
            "ai_tone_strict",
            "ai_articles_balanced",
            "ai_tone_balanced",
        ]
    )
    last_error: Exception | None = None

    for attempt in range(1, COUNTRY_QUERY_MAX_RETRIES + 1):
        try:
            query_df = run_all_countries_query(
                client=client,
                sql=sql,
                country_domain_map_values=country_domain_map_values,
                country_rule_map_values=country_rule_map_values,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            last_error = None
            break
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if attempt < COUNTRY_QUERY_MAX_RETRIES:
                sleep_seconds = COUNTRY_QUERY_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                print(
                    f"[WARN] {retry_label} query failed attempt {attempt}/"
                    f"{COUNTRY_QUERY_MAX_RETRIES}: {exc}. Retrying in {sleep_seconds}s..."
                )
                time.sleep(sleep_seconds)
            else:
                print(
                    f"[ERROR] {retry_label} query failed after "
                    f"{COUNTRY_QUERY_MAX_RETRIES} attempts: {exc}"
                )

    return query_df, last_error


def estimate_all_countries_query_bytes(
    client: bigquery.Client,
    sql: str,
    country_domain_map_values: list[str],
    country_rule_map_values: list[str],
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    query_params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_dt.date()),
        bigquery.ArrayQueryParameter("country_domain_map", "STRING", country_domain_map_values),
        bigquery.ArrayQueryParameter("country_rule_map", "STRING", country_rule_map_values),
    ]
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_params,
        use_legacy_sql=False,
        dry_run=True,
        use_query_cache=False,
    )
    dry_run_job = client.query(sql, job_config=job_config)
    return int(dry_run_job.total_bytes_processed or 0)


def run_all_countries_query_chunked(
    client: bigquery.Client,
    sql: str,
    country_domain_map_values: list[str],
    country_rule_map_values: list[str],
    start_dt: datetime,
    end_dt: datetime,
    initial_chunk_months: int,
) -> tuple[pd.DataFrame, list[str], int]:
    frames: list[pd.DataFrame] = []
    failed_chunks: list[str] = []
    total_estimated_bytes = 0

    chunk_windows: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    step_months = max(1, initial_chunk_months)
    while cursor < end_dt:
        next_dt = min(cursor + relativedelta(months=step_months), end_dt)
        chunk_windows.append((cursor, next_dt))
        cursor = next_dt

    idx = 0
    while idx < len(chunk_windows):
        chunk_start_dt, chunk_end_dt = chunk_windows[idx]
        months_in_chunk = month_diff(chunk_start_dt, chunk_end_dt)
        chunk_label = (
            f"{chunk_start_dt.strftime('%Y-%m')}.."
            f"{(chunk_end_dt - relativedelta(days=1)).strftime('%Y-%m')}"
        )

        estimated_bytes: int | None = None
        try:
            estimated_bytes = estimate_all_countries_query_bytes(
                client=client,
                sql=sql,
                country_domain_map_values=country_domain_map_values,
                country_rule_map_values=country_rule_map_values,
                start_dt=chunk_start_dt,
                end_dt=chunk_end_dt,
            )
            total_estimated_bytes += estimated_bytes
            print(
                f"Dry run ALL {chunk_label}, estimated bytes={estimated_bytes}, "
                f"months={months_in_chunk}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Dry run failed for ALL {chunk_label}: {exc}")

        if (
            AUTO_MONTHLY_FALLBACK_ON_BYTES_LIMIT
            and MAXIMUM_BYTES_BILLED is not None
            and estimated_bytes is not None
            and estimated_bytes > MAXIMUM_BYTES_BILLED
            and months_in_chunk > 1
        ):
            split_months = max(1, months_in_chunk // 2)
            split_dt = min(chunk_start_dt + relativedelta(months=split_months), chunk_end_dt)
            if split_dt <= chunk_start_dt or split_dt >= chunk_end_dt:
                split_dt = chunk_start_dt + relativedelta(months=1)
            left = (chunk_start_dt, split_dt)
            right = (split_dt, chunk_end_dt)
            print(
                f"[INFO] ALL {chunk_label} exceeds bytes cap, "
                f"splitting into {left[0].strftime('%Y-%m')}.."
                f"{(left[1] - relativedelta(days=1)).strftime('%Y-%m')} and "
                f"{right[0].strftime('%Y-%m')}.."
                f"{(right[1] - relativedelta(days=1)).strftime('%Y-%m')}."
            )
            chunk_windows[idx : idx + 1] = [left, right]
            continue

        chunk_df, chunk_error = run_all_countries_query_with_retries(
            client=client,
            sql=sql,
            country_domain_map_values=country_domain_map_values,
            country_rule_map_values=country_rule_map_values,
            start_dt=chunk_start_dt,
            end_dt=chunk_end_dt,
            retry_label=f"ALL {chunk_label}",
        )
        if chunk_error is not None:
            failed_chunks.append(chunk_label)
        elif not chunk_df.empty:
            frames.append(chunk_df)

        idx += 1

    if not frames:
        empty_df = pd.DataFrame(
            columns=[
                "country",
                "month",
                "all_articles",
                "ai_articles_strict",
                "ai_tone_strict",
                "ai_articles_balanced",
                "ai_tone_balanced",
            ]
        )
        return empty_df, failed_chunks, total_estimated_bytes

    merged_df = pd.concat(frames, ignore_index=True)
    merged_df = (
        merged_df.sort_values(["country", "month"])
        .drop_duplicates(subset=["country", "month"], keep="last")
        .reset_index(drop=True)
    )
    return merged_df, failed_chunks, total_estimated_bytes


def run_country_query_chunked(
    client: bigquery.Client,
    sql: str,
    country_code: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    start_dt: datetime,
    end_dt: datetime,
    initial_chunk_months: int,
) -> tuple[pd.DataFrame, list[str], int]:
    frames: list[pd.DataFrame] = []
    failed_chunks: list[str] = []
    total_estimated_bytes = 0

    chunk_windows: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    step_months = max(1, initial_chunk_months)
    while cursor < end_dt:
        next_dt = min(cursor + relativedelta(months=step_months), end_dt)
        chunk_windows.append((cursor, next_dt))
        cursor = next_dt

    idx = 0
    while idx < len(chunk_windows):
        chunk_start_dt, chunk_end_dt = chunk_windows[idx]
        months_in_chunk = month_diff(chunk_start_dt, chunk_end_dt)
        chunk_label = f"{chunk_start_dt.strftime('%Y-%m')}..{(chunk_end_dt - relativedelta(days=1)).strftime('%Y-%m')}"

        estimated_bytes: int | None = None
        try:
            estimated_bytes = estimate_country_query_bytes(
                client=client,
                sql=sql,
                country_code=country_code,
                domains=domains,
                strict_regex=strict_regex,
                context_regex=context_regex,
                ai_abbrev_regex=ai_abbrev_regex,
                start_dt=chunk_start_dt,
                end_dt=chunk_end_dt,
            )
            total_estimated_bytes += estimated_bytes
            print(
                f"Dry run {country_code} {chunk_label}, estimated bytes={estimated_bytes}, "
                f"months={months_in_chunk}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Dry run failed for {country_code} {chunk_label}: {exc}")

        if (
            AUTO_MONTHLY_FALLBACK_ON_BYTES_LIMIT
            and MAXIMUM_BYTES_BILLED is not None
            and estimated_bytes is not None
            and estimated_bytes > MAXIMUM_BYTES_BILLED
            and months_in_chunk > 1
        ):
            split_months = max(1, months_in_chunk // 2)
            split_dt = min(chunk_start_dt + relativedelta(months=split_months), chunk_end_dt)
            if split_dt <= chunk_start_dt or split_dt >= chunk_end_dt:
                split_dt = chunk_start_dt + relativedelta(months=1)
            left = (chunk_start_dt, split_dt)
            right = (split_dt, chunk_end_dt)
            print(
                f"[INFO] {country_code} {chunk_label} exceeds bytes cap, "
                f"splitting into {left[0].strftime('%Y-%m')}..{(left[1]-relativedelta(days=1)).strftime('%Y-%m')} "
                f"and {right[0].strftime('%Y-%m')}..{(right[1]-relativedelta(days=1)).strftime('%Y-%m')}."
            )
            chunk_windows[idx : idx + 1] = [left, right]
            continue

        chunk_df, chunk_error = run_country_query_with_retries(
            client=client,
            sql=sql,
            country_code=country_code,
            domains=domains,
            strict_regex=strict_regex,
            context_regex=context_regex,
            ai_abbrev_regex=ai_abbrev_regex,
            start_dt=chunk_start_dt,
            end_dt=chunk_end_dt,
            retry_label=f"{country_code} {chunk_label}",
        )
        if chunk_error is not None:
            failed_chunks.append(chunk_label)
        elif not chunk_df.empty:
            frames.append(chunk_df)

        idx += 1

    if not frames:
        empty_df = pd.DataFrame(
            columns=[
                "country",
                "month",
                "all_articles",
                "ai_articles_strict",
                "ai_tone_strict",
                "ai_articles_balanced",
                "ai_tone_balanced",
            ]
        )
        return empty_df, failed_chunks, total_estimated_bytes

    merged_df = pd.concat(frames, ignore_index=True)
    merged_df = merged_df.sort_values("month").drop_duplicates(subset=["month"], keep="last")
    return merged_df, failed_chunks, total_estimated_bytes


def run_sanity_query(
    client: bigquery.Client,
    sql: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    sanity_mode: str,
    start_dt: datetime,
    end_exclusive_dt: datetime,
    limit_rows: int,
) -> pd.DataFrame:
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_exclusive_date", "DATE", end_exclusive_dt.date()),
        bigquery.ArrayQueryParameter("domains", "STRING", [d.lower() for d in domains]),
        bigquery.ScalarQueryParameter("strict_regex", "STRING", strict_regex),
        bigquery.ScalarQueryParameter("context_regex", "STRING", context_regex),
        bigquery.ScalarQueryParameter("ai_abbrev_regex", "STRING", ai_abbrev_regex),
        bigquery.ScalarQueryParameter("sanity_mode", "STRING", sanity_mode),
        bigquery.ScalarQueryParameter("limit_rows", "INT64", int(limit_rows)),
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params, use_legacy_sql=False)

    rows: list[dict[str, Any]] = []
    query_job = client.query(sql, job_config=job_config)
    for row in query_job.result():
        rows.append(
            {
                "month": str(row["month"]),
                "domain": row["domain"],
                "url": row["url"],
                "title": row["title"],
                "tone": float(row["tone"]) if row["tone"] is not None else math.nan,
            }
        )

    return pd.DataFrame(rows, columns=["month", "domain", "url", "title", "tone"])


def run_debug_counts_query(
    client: bigquery.Client,
    sql: str,
    domains: list[str],
    strict_regex: str,
    context_regex: str,
    ai_abbrev_regex: str,
    start_dt: datetime,
    end_exclusive_dt: datetime,
) -> dict[str, int]:
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_dt.date()),
        bigquery.ScalarQueryParameter("end_exclusive_date", "DATE", end_exclusive_dt.date()),
        bigquery.ArrayQueryParameter("domains", "STRING", [d.lower() for d in domains]),
        bigquery.ScalarQueryParameter("strict_regex", "STRING", strict_regex),
        bigquery.ScalarQueryParameter("context_regex", "STRING", context_regex),
        bigquery.ScalarQueryParameter("ai_abbrev_regex", "STRING", ai_abbrev_regex),
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params, use_legacy_sql=False)
    query_job = client.query(sql, job_config=job_config)
    row = next(iter(query_job.result()), None)
    if row is None:
        return {
            "n_all": 0,
            "n_strict": 0,
            "n_abbrev": 0,
            "n_context": 0,
            "n_abbrev_and_context": 0,
            "n_balanced": 0,
        }
    return {
        "n_all": int(row["n_all"] or 0),
        "n_strict": int(row["n_strict"] or 0),
        "n_abbrev": int(row["n_abbrev"] or 0),
        "n_context": int(row["n_context"] or 0),
        "n_abbrev_and_context": int(row["n_abbrev_and_context"] or 0),
        "n_balanced": int(row["n_balanced"] or 0),
    }


def run_debug_counts(
    client: bigquery.Client,
    sql: str,
    all_sources: dict[str, Any],
    country_rules: dict[str, dict[str, Any]],
) -> None:
    cfg = all_sources.get(DEBUG_COUNTRY)
    if not cfg:
        raise RuntimeError(f"DEBUG_COUNTRY not found in sources.yaml: {DEBUG_COUNTRY}")
    country_rule = country_rules.get(DEBUG_COUNTRY)
    if not country_rule:
        raise RuntimeError(f"DEBUG_COUNTRY not found in keyword rules: {DEBUG_COUNTRY}")

    domains = [str(d).lower() for d in cfg.get("domains", [])]
    if DEBUG_DOMAIN_LIMIT > 0:
        domains = domains[:DEBUG_DOMAIN_LIMIT]
    if not domains:
        raise RuntimeError(f"No debug domains available for country {DEBUG_COUNTRY}")

    debug_start, debug_end_exclusive = get_debug_time_window()
    print(
        "Debug counts: "
        f"country={DEBUG_COUNTRY}, domains={domains}, "
        f"window={debug_start.date()}..{debug_end_exclusive.date()}(exclusive)"
    )

    counts = run_debug_counts_query(
        client=client,
        sql=sql,
        domains=domains,
        strict_regex=country_rule["strict_regex"],
        context_regex=country_rule["context_regex"],
        ai_abbrev_regex=country_rule["ai_abbrev_regex"],
        start_dt=debug_start,
        end_exclusive_dt=debug_end_exclusive,
    )
    print(
        "DEBUG_COUNTS row: "
        f"n_all={counts['n_all']}, "
        f"n_strict={counts['n_strict']}, "
        f"n_abbrev={counts['n_abbrev']}, "
        f"n_context={counts['n_context']}, "
        f"n_abbrev_and_context={counts['n_abbrev_and_context']}, "
        f"n_balanced={counts['n_balanced']}"
    )
    if counts["n_abbrev_and_context"] <= 0:
        print(
            "[WARN] n_abbrev_and_context is 0; Rule B contributes little in this slice. "
            "Consider broadening context terms or adjusting text field in a next iteration."
        )


def run_sanity_check(
    client: bigquery.Client,
    sql: str,
    all_sources: dict[str, Any],
    country_rules: dict[str, dict[str, Any]],
) -> None:
    mode = SANITY_MODE.strip().lower()
    if mode not in {"strict", "balanced"}:
        raise RuntimeError("SANITY_MODE must be 'strict' or 'balanced'")

    country_cfg = all_sources.get(SANITY_COUNTRY)
    if not country_cfg:
        raise RuntimeError(f"SANITY_COUNTRY not found in sources.yaml: {SANITY_COUNTRY}")
    country_rule = country_rules.get(SANITY_COUNTRY)
    if not country_rule:
        raise RuntimeError(f"SANITY_COUNTRY not found in keyword rules: {SANITY_COUNTRY}")

    domains = [str(d).lower() for d in country_cfg.get("domains", [])]
    if SANITY_DOMAIN_LIMIT > 0:
        domains = domains[:SANITY_DOMAIN_LIMIT]
    if not domains:
        raise RuntimeError(f"No sanity domains available for country {SANITY_COUNTRY}")

    sanity_start, sanity_end_exclusive = get_sanity_time_window()
    print(
        "Sanity check: "
        f"mode={mode}, country={SANITY_COUNTRY}, domains={domains}, "
        f"window={sanity_start.date()}..{sanity_end_exclusive.date()}(exclusive), "
        f"limit={SANITY_LIMIT_ROWS}"
    )

    sanity_df = run_sanity_query(
        client=client,
        sql=sql,
        domains=domains,
        strict_regex=country_rule["strict_regex"],
        context_regex=country_rule["context_regex"],
        ai_abbrev_regex=country_rule["ai_abbrev_regex"],
        sanity_mode=mode,
        start_dt=sanity_start,
        end_exclusive_dt=sanity_end_exclusive,
        limit_rows=SANITY_LIMIT_ROWS,
    )

    sanity_output_path = OUTPUT_DIR / f"sanity_sample_{mode}.csv"
    sanity_df.to_csv(sanity_output_path, index=False)

    print(f"Sanity sample rows: {len(sanity_df)}")
    print(f"Sanity sample saved: {sanity_output_path}")

    if not sanity_df.empty:
        preview = sanity_df[["url", "title", "tone"]].head(10)
        print("Sanity sample first 10 rows (url + title + tone):")
        print(preview.to_string(index=False))

    print(
        "Manual check: open 5-10 URLs and verify most are genuinely AI-related. "
        "If >30% are unrelated, tighten context keywords."
    )


def build_country_panel(
    country_code: str,
    country_name: str,
    domains: list[str],
    month_list: list[datetime],
    end_dt: datetime,
    country_df: pd.DataFrame,
) -> pd.DataFrame:
    month_grid = pd.DataFrame({"month": [m.date() for m in month_list]})

    if country_df.empty:
        merged = month_grid.copy()
        merged["all_articles"] = 0
        merged["ai_articles_strict"] = 0
        merged["ai_tone_strict"] = math.nan
        merged["ai_articles_balanced"] = 0
        merged["ai_tone_balanced"] = math.nan
    else:
        work_df = country_df.copy()
        work_df["month"] = pd.to_datetime(work_df["month"]).dt.date
        merged = month_grid.merge(work_df, on="month", how="left")
        merged["all_articles"] = merged["all_articles"].fillna(0).astype(int)
        merged["ai_articles_strict"] = merged["ai_articles_strict"].fillna(0).astype(int)
        merged["ai_articles_balanced"] = merged["ai_articles_balanced"].fillna(0).astype(int)
        merged["ai_tone_strict"] = merged["ai_tone_strict"].astype(float)
        merged["ai_tone_balanced"] = merged["ai_tone_balanced"].astype(float)

    denominator = merged["all_articles"].astype(float).replace(0.0, math.nan)
    ai_prop_strict = merged["ai_articles_strict"].astype(float) / denominator
    ai_prop_balanced = merged["ai_articles_balanced"].astype(float) / denominator

    month_start_values = [datetime(m.year, m.month, 1, tzinfo=timezone.utc) for m in merged["month"]]
    month_end_values = [month_end(ms, end_dt) for ms in month_start_values]

    panel = pd.DataFrame(
        {
            "country": country_code,
            "country_name": country_name,
            "month_start_utc": [d.strftime("%Y-%m-%dT%H:%M:%SZ") for d in month_start_values],
            "month_end_utc": [d.strftime("%Y-%m-%dT%H:%M:%SZ") for d in month_end_values],
            "all_articles": merged["all_articles"],
            "ai_articles_strict": merged["ai_articles_strict"],
            "ai_proportion_strict": ai_prop_strict,
            "ai_tone_strict": merged["ai_tone_strict"],
            "ai_articles_balanced": merged["ai_articles_balanced"],
            "ai_proportion_balanced": ai_prop_balanced,
            "ai_tone_balanced": merged["ai_tone_balanced"],
            "domains": ",".join(domains),
        }
    )
    return panel


def validate_full_output(
    df: pd.DataFrame,
    countries: dict[str, Any],
    months: list[datetime],
) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    messages: list[str] = []
    expected_months = len(months)
    expected_rows = expected_months * len(countries)
    actual_rows = len(df)

    messages.append(
        f"Row count check, expected_months={expected_months}, "
        f"expected_rows={expected_rows}, actual_rows={actual_rows}"
    )

    expected_month_keys = {m.strftime("%Y-%m-%dT%H:%M:%SZ") for m in months}
    missing_month_lines: list[str] = []
    for country_code in countries:
        country_months = set(df.loc[df["country"] == country_code, "month_start_utc"].tolist())
        missing = sorted(expected_month_keys - country_months)
        if missing:
            missing_month_lines.append(f"{country_code}: missing_months={len(missing)}")
    if missing_month_lines:
        messages.append("Missing month check failed, " + "; ".join(missing_month_lines))
    else:
        messages.append("Missing month check passed, no months missing")

    cond_counts = {
        "strict_gt_balanced": int((df["ai_articles_strict"] > df["ai_articles_balanced"]).sum()),
        "balanced_gt_all": int((df["ai_articles_balanced"] > df["all_articles"]).sum()),
        "prop_strict_out_of_range": int(
            ((df["ai_proportion_strict"] < 0) | (df["ai_proportion_strict"] > 1))
            .fillna(False)
            .sum()
        ),
        "prop_balanced_out_of_range": int(
            ((df["ai_proportion_balanced"] < 0) | (df["ai_proportion_balanced"] > 1))
            .fillna(False)
            .sum()
        ),
    }
    messages.append(
        "Plausibility checks, "
        + ", ".join(f"{k}={v}" for k, v in cond_counts.items())
    )

    balanced_nonnull = df.dropna(subset=["ai_proportion_balanced"]).copy()
    top_high = (
        balanced_nonnull.sort_values("ai_proportion_balanced", ascending=False)
        .head(10)[["country", "month_start_utc", "ai_proportion_balanced"]]
    )
    top_low = (
        balanced_nonnull.sort_values("ai_proportion_balanced", ascending=True)
        .head(10)[["country", "month_start_utc", "ai_proportion_balanced"]]
    )

    return messages, top_high, top_low


def main() -> None:
    all_sources = load_sources()
    countries = prepare_countries(all_sources)
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_lines: list[str] = []

    if KEYWORDS_MODE.strip().lower() != "strict+balanced":
        raise RuntimeError("This workflow expects KEYWORDS_MODE='strict+balanced'")

    country_rules, keyword_strategy = build_country_keyword_rules(countries)
    strict_keyword_counts = sorted({len(rule["strict_keywords"]) for rule in country_rules.values()})
    context_keyword_counts = sorted({len(rule["context_keywords"]) for rule in country_rules.values()})
    abbreviation_term_counts = sorted({len(rule["abbreviation_terms"]) for rule in country_rules.values()})

    start_dt, end_dt = get_time_window(SMOKE_TEST)
    months = month_starts(start_dt, end_dt)

    run_mode = "SMOKE" if SMOKE_TEST else "FULL"
    print(f"Running {run_mode} window from {start_dt.isoformat()} to {end_dt.isoformat()}")
    print(f"Countries: {', '.join(countries.keys())}")
    print(f"Month windows: {len(months)}")
    print(
        "Keyword strategy: "
        f"version={keyword_strategy['version']}, "
        f"rules_file={keyword_strategy['rules_file'] or 'legacy_global'}"
    )
    print(f"Strict keyword counts by country: {strict_keyword_counts}")
    print(f"Context keyword counts by country: {context_keyword_counts}")
    print(f"Abbreviation term counts by country: {abbreviation_term_counts}")
    print(f"Maximum bytes billed per query: {MAXIMUM_BYTES_BILLED}")
    print(f"GDELT table: {GDELT_TABLE}")
    print(
        "Budget guardrail, "
        f"gbp_limit={BUDGET_GBP_LIMIT}, "
        f"max_total_bytes={MAX_TOTAL_BYTES_BUDGET}"
    )

    log_lines.append(f"timestamp_utc={run_timestamp}")
    log_lines.append(f"bq_project={BIGQUERY_PROJECT or 'default_from_adc'}")
    log_lines.append(f"run_mode={run_mode}")
    log_lines.append(f"start_utc={start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    log_lines.append(f"end_utc_exclusive={end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    log_lines.append(f"country_count={len(countries)}")
    log_lines.append(f"month_count={len(months)}")
    log_lines.append(f"maximum_bytes_billed={MAXIMUM_BYTES_BILLED}")
    log_lines.append(f"gdelt_table={GDELT_TABLE}")
    log_lines.append(f"sources_file={SOURCES_PATH}")
    log_lines.append(f"keyword_strategy_version={keyword_strategy['version']}")
    log_lines.append(f"keyword_rules_file={keyword_strategy['rules_file'] or 'legacy_global'}")
    log_lines.append(f"keyword_strict_base_files={','.join(keyword_strategy['strict_base_files'])}")
    log_lines.append(f"keyword_context_languages={','.join(keyword_strategy['context_languages_used'])}")
    log_lines.append(
        f"default_abbreviation_terms={','.join(keyword_strategy['default_abbreviation_terms'])}"
    )
    log_lines.append(f"output_suffix={OUTPUT_SUFFIX}")
    log_lines.append(f"auto_monthly_fallback_on_bytes_limit={AUTO_MONTHLY_FALLBACK_ON_BYTES_LIMIT}")
    log_lines.append(f"initial_chunk_months={INITIAL_CHUNK_MONTHS}")
    log_lines.append(f"budget_gbp_limit={BUDGET_GBP_LIMIT}")
    log_lines.append(f"gbp_to_usd={GBP_TO_USD}")
    log_lines.append(f"usd_per_tib={BQ_ONDEMAND_USD_PER_TIB}")
    log_lines.append(f"max_total_bytes_budget={MAX_TOTAL_BYTES_BUDGET}")

    templates = load_sql_templates()
    all_monthly_sql = render_all_countries_sql(get_sql_template(templates, "all_countries_monthly_panel"))
    country_domain_map_values = build_country_domain_map_values(countries)
    country_rule_map_values = build_country_rule_map_values(country_rules)
    print(f"Country-domain mappings: {len(country_domain_map_values)}")
    log_lines.append(f"country_domain_mapping_count={len(country_domain_map_values)}")
    log_lines.append(f"country_rule_mapping_count={len(country_rule_map_values)}")
    for country_code in countries:
        rule = country_rules[country_code]
        log_lines.append(
            f"keyword_rule_{country_code}=strict:{len(rule['strict_keywords'])},"
            f"context:{len(rule['context_keywords'])},"
            f"abbrev:{'|'.join(rule['abbreviation_terms'])},"
            f"context_languages:{'|'.join(rule['context_languages'])}"
        )
    sanity_sql = render_sql_template(get_sql_template(templates, "sanity_sample")) if SANITY_CHECK else ""
    debug_sql = render_sql_template(get_sql_template(templates, "debug_counts")) if DEBUG_COUNTS else ""

    try:
        client = bigquery.Client(project=BIGQUERY_PROJECT or None)
    except DefaultCredentialsError as exc:
        raise RuntimeError(
            "BigQuery credentials not found. Run `gcloud auth application-default login` "
            "or set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON."
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(f"Failed to create BigQuery client: {exc}") from exc

    try:
        estimated_bytes = preflight_sql_access(client)
        print(f"BigQuery SQL preflight OK (estimated bytes: {estimated_bytes})")
        log_lines.append(f"global_preflight_estimated_bytes={estimated_bytes}")
    except Forbidden as exc:
        raise RuntimeError(
            "BigQuery access denied. Confirm the account has BigQuery permissions "
            "and access to public dataset `gdelt-bq.gdeltv2`."
        ) from exc
    except NotFound as exc:
        raise RuntimeError(
            f"GDELT table not found: `{GDELT_TABLE}`. "
            "Check dataset availability in BigQuery Explorer."
        ) from exc
    except BadRequest as exc:
        raise RuntimeError(f"BigQuery preflight query invalid: {exc}") from exc

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DEBUG_COUNTS:
        run_debug_counts(
            client=client,
            sql=debug_sql,
            all_sources=all_sources,
            country_rules=country_rules,
        )

    if SANITY_CHECK:
        run_sanity_check(
            client=client,
            sql=sanity_sql,
            all_sources=all_sources,
            country_rules=country_rules,
        )

    estimated_all_bytes: int | None = None
    all_query_error: Exception | None = None
    all_query_df = pd.DataFrame(
        columns=[
            "country",
            "month",
            "all_articles",
            "ai_articles_strict",
            "ai_tone_strict",
            "ai_articles_balanced",
            "ai_tone_balanced",
        ]
    )

    try:
        estimated_all_bytes = estimate_all_countries_query_bytes(
            client=client,
            sql=all_monthly_sql,
            country_domain_map_values=country_domain_map_values,
            country_rule_map_values=country_rule_map_values,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        est_tib = estimated_all_bytes / float(1024**4)
        est_cost_usd = est_tib * BQ_ONDEMAND_USD_PER_TIB
        est_cost_gbp = est_cost_usd / GBP_TO_USD
        print(f"Dry run ALL, estimated bytes={estimated_all_bytes}")
        print(
            "Projected query scan and cost, "
            f"tib={est_tib:.3f}, usd={est_cost_usd:.2f}, gbp={est_cost_gbp:.2f}"
        )
        log_lines.append(f"dry_run_bytes_all={estimated_all_bytes}")
        log_lines.append(f"projected_scan_tib={est_tib:.6f}")
        log_lines.append(f"projected_cost_usd={est_cost_usd:.2f}")
        log_lines.append(f"projected_cost_gbp={est_cost_gbp:.2f}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[WARN] Dry run failed for ALL: {exc}")
        log_lines.append(f"dry_run_failed_all={exc}")

    if estimated_all_bytes is not None and estimated_all_bytes > MAX_TOTAL_BYTES_BUDGET:
        budget_tib = MAX_TOTAL_BYTES_BUDGET / float(1024**4)
        budget_usd = BUDGET_GBP_LIMIT * GBP_TO_USD
        raise RuntimeError(
            "Projected scan exceeds budget guardrail, "
            f"projected_bytes={estimated_all_bytes}, "
            f"budget_bytes={MAX_TOTAL_BYTES_BUDGET}, "
            f"budget_tib={budget_tib:.3f}, "
            f"budget_gbp={BUDGET_GBP_LIMIT:.2f}, budget_usd={budget_usd:.2f}"
        )

    used_chunked_fallback = False
    failed_chunks: list[str] = []
    if (
        AUTO_MONTHLY_FALLBACK_ON_BYTES_LIMIT
        and MAXIMUM_BYTES_BILLED is not None
        and estimated_all_bytes is not None
        and estimated_all_bytes > MAXIMUM_BYTES_BILLED
    ):
        used_chunked_fallback = True
        print(
            f"[INFO] ALL estimated bytes ({estimated_all_bytes}) exceed "
            f"cap ({MAXIMUM_BYTES_BILLED}), switching to chunked queries."
        )
        log_lines.append("used_chunked_fallback_all=true")
        all_query_df, failed_chunks, chunk_estimated_total = run_all_countries_query_chunked(
            client=client,
            sql=all_monthly_sql,
            country_domain_map_values=country_domain_map_values,
            country_rule_map_values=country_rule_map_values,
            start_dt=start_dt,
            end_dt=end_dt,
            initial_chunk_months=INITIAL_CHUNK_MONTHS,
        )
        log_lines.append(f"chunk_estimated_bytes_total_all={chunk_estimated_total}")
        if failed_chunks:
            print(f"[WARN] ALL failed chunks ({len(failed_chunks)}): {', '.join(failed_chunks)}")
            log_lines.append(f"failed_chunks_all={','.join(failed_chunks)}")
            all_query_error = RuntimeError(f"ALL chunk failures: {','.join(failed_chunks)}")
        elif all_query_df.empty:
            all_query_error = RuntimeError("ALL chunk query returned no rows")

    if not used_chunked_fallback:
        all_query_df, all_query_error = run_all_countries_query_with_retries(
            client=client,
            sql=all_monthly_sql,
            country_domain_map_values=country_domain_map_values,
            country_rule_map_values=country_rule_map_values,
            start_dt=start_dt,
            end_dt=end_dt,
            retry_label="ALL",
        )

    all_country_frames: list[pd.DataFrame] = []
    failed_countries: list[str] = list(countries.keys()) if all_query_error is not None else []

    for country_code, cfg in tqdm(countries.items(), desc="Countries", unit="country"):
        country_name = str(cfg.get("name", country_code))
        domains = [str(d).lower() for d in cfg.get("domains", [])]
        if not domains:
            continue

        country_query_df = (
            all_query_df[all_query_df["country"] == country_code].copy()
            if not all_query_df.empty
            else pd.DataFrame(
                columns=[
                    "country",
                    "month",
                    "all_articles",
                    "ai_articles_strict",
                    "ai_tone_strict",
                    "ai_articles_balanced",
                    "ai_tone_balanced",
                ]
            )
        )

        panel_df = build_country_panel(
            country_code=country_code,
            country_name=country_name,
            domains=domains,
            month_list=months,
            end_dt=end_dt,
            country_df=country_query_df,
        )

        country_output = OUTPUT_DIR / f"{country_code.lower()}_monthly_{OUTPUT_WINDOW_TAG}{OUTPUT_SUFFIX}.csv"
        panel_df.to_csv(country_output, index=False)
        all_country_frames.append(panel_df)
        log_lines.append(f"rows_{country_code}={len(panel_df)}")

    if not all_country_frames:
        raise RuntimeError("No output generated. Check sources.yaml and filters.")

    final_df = pd.concat(all_country_frames, ignore_index=True)
    final_df = final_df.sort_values(["country", "month_start_utc"]).reset_index(drop=True)
    final_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(final_df)} rows to {OUTPUT_PATH}")
    log_lines.append(f"output_csv={OUTPUT_PATH}")
    log_lines.append(f"actual_rows={len(final_df)}")

    if failed_countries:
        print(f"[WARN] Countries with fallback zero panels due to repeated failures: {failed_countries}")
        log_lines.append(f"failed_countries={','.join(failed_countries)}")

    validation_lines, top_high, top_low = validate_full_output(final_df, countries, months)
    for line in validation_lines:
        print(line)
        log_lines.append(line)

    print("Top 10 highest ai_proportion_balanced:")
    print(top_high.to_string(index=False))
    print("Top 10 lowest ai_proportion_balanced:")
    print(top_low.to_string(index=False))
    log_lines.append("top10_highest_ai_proportion_balanced")
    log_lines.extend(top_high.to_csv(index=False).strip().splitlines())
    log_lines.append("top10_lowest_ai_proportion_balanced")
    log_lines.extend(top_low.to_csv(index=False).strip().splitlines())

    expected_months = len(months)
    zero_warning_threshold = int(math.ceil(expected_months * ZERO_MONTH_WARNING_THRESHOLD_RATIO))
    zero_country_messages: list[str] = []
    for country_code, cfg in countries.items():
        country_slice = final_df[final_df["country"] == country_code]
        zero_months = int((country_slice["all_articles"] == 0).sum())
        if zero_months >= zero_warning_threshold:
            domains = ",".join(cfg.get("domains", []))
            zero_country_messages.append(
                f"{country_code}: zero_months={zero_months}, domains={domains}"
            )
    if zero_country_messages:
        warning_text = "Countries with many zero article months, " + "; ".join(zero_country_messages)
        print(warning_text)
        log_lines.append(warning_text)

    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"Wrote full run log to {LOG_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] {exc}")
        sys.exit(1)
