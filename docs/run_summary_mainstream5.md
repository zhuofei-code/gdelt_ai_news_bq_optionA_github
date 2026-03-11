# Run Summary: Mainstream-Only Version

This run uses `5` mainstream, general-interest outlets per country and removes
all specialist outlets from the source design.

## Run Scope

- Countries: `11`
- Outlets per country: `5`
- Country-domain mappings: `55`
- Time window: `2018-06-01` to `2025-06-01` (end exclusive)
- Rows in final panel: `924`

## Cost and Runtime

- Dry-run bytes: `2,081,389,844,972`
- Projected scan: `1.893013 TiB`
- Projected cost: `USD 11.83` / `GBP 9.24`
- `maximum_bytes_billed`: `120 GiB` per query
- Execution mode: chunked fallback
- Run timestamp: `2026-03-11T23:02:20Z`

## Validation

- Row count check passed
- Missing month check passed
- Plausibility checks passed

## Main Files

- Config: `config/sources_v3_mainstream5.yaml`
- Source note: `docs/source_selection_mainstream5.md`
- Full log: `results/fullrun_log_201806_202506_mainstream5.txt`
- Combined panel: `results/gdelt_ai_country_monthly_201806_202506_mainstream5.csv`

## Comparison With Option A

This run is intended as a clean comparison against the earlier `Option A`
design (`5 mainstream + 5 specialist`).

At the full-panel level:

- `Option A` total balanced AI proportion: `1.3564%`
- `Mainstream-only` total balanced AI proportion: `1.3825%`

Selected country-level changes in weighted `ai_proportion_balanced`:

- `PL`: `3.7105%` -> `4.4613%`
- `FR`: `1.1182%` -> `1.0100%`
- `PT`: `2.0474%` -> `1.9291%`
- `IS`: `0.0769%` -> `0.0773%`

The mainstream-only version should therefore be treated as a distinct design,
not just a lighter variant of `Option A`.
