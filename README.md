# GDELT AI News BigQuery: Option A (10 Outlets per Country)

This folder is a GitHub-ready release package for the `Option A` source design:

- `11` countries
- `5` mainstream outlets per country
- `5` specialist outlets per country
- fixed monthly panel from `2018-06-01` to `2025-06-01` (end exclusive)

The package contains the code, configuration, source-selection notes, and output files used for the `10 outlets per country` run.

The repository now also includes an extended update through `2026-03` (with
`2026-04-01` as the exclusive end boundary) for both the mixed-source and
mainstream-only panels.

An additional comparison variant is also included:

- `mainstream5`: `11` countries, `5` mainstream outlets per country, no specialist outlets

## Folder Structure

- `code/`: extraction script and SQL templates
- `config/`: source lists and keyword files
- `docs/`: source-selection notes, keyword documentation, and run summary
- `results/`: panel output and country-level CSV files

## Key Files

- `config/sources_v2_optionA.yaml`: the `11 x 10` outlet source file used in the final run
- `config/sources_v3_mainstream5.yaml`: the `11 x 5` mainstream-only source file
- `config/country_language_rules_v2.yaml`: seed `v2` country-aware keyword rules for multilingual context and abbreviations
- `docs/source_selection_optionA.md`: recorded mainstream and specialist outlet choices by country
- `docs/keyword_strategy_report.md`: production keyword strategy used in BigQuery scanning
- `docs/keyword_strategy_improvement_plan.md`: roadmap for reducing language-related undercount in non-English coverage
- `docs/comparison_optionA_v1_vs_v2_keyword_strategy.md`: same-day `v1` versus `v2` keyword-strategy sensitivity report
- `docs/comparison_mainstream5_v1_vs_v2_keyword_strategy.md`: same-day `mainstream5` `v1` versus `v2` keyword-strategy sensitivity report
- `docs/run_summary_optionA.md`: public-facing summary of the completed run
- `results/gdelt_ai_country_monthly_201806_202506_optionA.csv`: final combined monthly panel
- `results/gdelt_ai_country_monthly_201806_202506_mainstream5.csv`: mainstream-only comparison panel
- `results/gdelt_ai_country_monthly_201806_202604_optionA.csv`: updated mixed-source panel through `2026-03`
- `results/gdelt_ai_country_monthly_201806_202604_mainstream5.csv`: updated mainstream-only panel through `2026-03`
- `results/gdelt_ai_country_monthly_201806_202604_optionA_v1rerun.csv`: same-day `v1` baseline rerun for keyword sensitivity testing
- `results/gdelt_ai_country_monthly_201806_202604_optionA_v2.csv`: `v2` seed rerun with country-aware multilingual keyword rules
- `results/gdelt_ai_country_monthly_201806_202604_mainstream5_v1rerun.csv`: same-day `mainstream5` `v1` baseline rerun
- `results/gdelt_ai_country_monthly_201806_202604_mainstream5_v2.csv`: `mainstream5` rerun with `v2` seed keyword rules
- `docs/monthly_ranking_chart.html`: interactive month-by-month ranking race using the latest panel data

## Run Summary

- Countries: `11`
- Country-domain mappings: `110`
- Monthly rows: `924`
- Time window: `2018-06-01` to `2025-06-01`
- Dry-run scan estimate: `1.893013 TiB`
- Estimated BigQuery cost: `USD 11.83` / `GBP 9.24`
- Final output checks: row count passed, missing-month check passed, plausibility checks passed

## Reproduction

From the repository root:

```bash
python -m pip install -r requirements.txt
OUTPUT_SUFFIX=optionA python code/run_gdelt_bigquery.py
```

The packaged script defaults to `config/sources_v2_optionA.yaml` and writes new run outputs into `results/`.

It also supports runtime date overrides:

```bash
START_DATE_UTC=2018-06-01T00:00:00Z
END_DATE_UTC=2026-04-01T00:00:00Z
OUTPUT_SUFFIX=optionA
python code/run_gdelt_bigquery.py
```

To test the seed `v2` multilingual keyword design without replacing the current
released rule base:

```bash
KEYWORD_RULES_FILE=config/country_language_rules_v2.yaml
OUTPUT_SUFFIX=optionA_v2
python code/run_gdelt_bigquery.py
```

You will still need valid Google Cloud credentials and a billable BigQuery project. No credentials are included in this package.

## Citation

GitHub will surface citation metadata from `CITATION.cff`.

If you use this package in a paper, report, or derivative dataset, cite the repository and note the released source design as `Option A (10 outlets per country)`.

## Status Note

The `Option A` specialist outlets are recorded as a working research configuration. Some small-market specialist domains remain better described as `provisional_pre_profiling`, especially in Iceland, Belgium, Portugal, Austria, and Slovenia.
