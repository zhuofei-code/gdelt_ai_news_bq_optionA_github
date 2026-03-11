# GDELT AI News BigQuery: Option A (10 Outlets per Country)

This folder is a GitHub-ready release package for the `Option A` source design:

- `11` countries
- `5` mainstream outlets per country
- `5` specialist outlets per country
- fixed monthly panel from `2018-06-01` to `2025-06-01` (end exclusive)

The package contains the code, configuration, source-selection notes, and output files used for the `10 outlets per country` run.

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
- `docs/source_selection_optionA.md`: recorded mainstream and specialist outlet choices by country
- `docs/run_summary_optionA.md`: public-facing summary of the completed run
- `results/gdelt_ai_country_monthly_201806_202506_optionA.csv`: final combined monthly panel
- `results/gdelt_ai_country_monthly_201806_202506_mainstream5.csv`: mainstream-only comparison panel

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

You will still need valid Google Cloud credentials and a billable BigQuery project. No credentials are included in this package.

## Citation

GitHub will surface citation metadata from `CITATION.cff`.

If you use this package in a paper, report, or derivative dataset, cite the repository and note the released source design as `Option A (10 outlets per country)`.

## Status Note

The `Option A` specialist outlets are recorded as a working research configuration. Some small-market specialist domains remain better described as `provisional_pre_profiling`, especially in Iceland, Belgium, Portugal, Austria, and Slovenia.
