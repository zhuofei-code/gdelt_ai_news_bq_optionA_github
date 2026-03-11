# Option A Run Summary

Run date: 2026-03-11

Configuration:

- Mode: `FULL`
- Source design: `11 countries x 10 outlets`
- Window start: `2018-06-01T00:00:00Z`
- Window end exclusive: `2025-06-01T00:00:00Z`
- Country-domain mappings: `110`
- Query table: `gdelt-bq.gdeltv2.gkg_partitioned`

BigQuery dry run:

- Preflight bytes: `26,577,238`
- Full estimated bytes: `2,081,389,844,972`
- Projected scan: `1.893013 TiB`
- Projected cost: `USD 11.83`
- Projected cost: `GBP 9.24`

Execution notes:

- The full query exceeded the per-query bytes cap and ran in chunked mode.
- The final `Option A` extraction completed successfully.
- Combined output rows: `924`
- Expected rows: `924`
- Missing month check: passed
- Plausibility checks: passed

Aggregate output summary:

- Countries in output: `AT, BE, CZ, FI, FR, HU, IS, PL, PT, SI, UK`
- Earliest month in output: `2018-06-01T00:00:00Z`
- Latest month in output: `2025-05-01T00:00:00Z`
- Sum of `all_articles`: `11,128,984`
- Sum of `ai_articles_balanced`: `150,952`

Top 10 highest `ai_proportion_balanced`:

```text
PL 2024-08-01T00:00:00Z 0.061376658033121416
PL 2025-04-01T00:00:00Z 0.06021309406981635
PL 2024-07-01T00:00:00Z 0.05958549222797927
PL 2025-01-01T00:00:00Z 0.056244653550042774
PL 2023-08-01T00:00:00Z 0.0556640625
PL 2024-06-01T00:00:00Z 0.0550423402617398
PL 2024-05-01T00:00:00Z 0.05467647277319664
PL 2024-09-01T00:00:00Z 0.05412586350869202
PL 2023-07-01T00:00:00Z 0.05298545640575897
PL 2023-05-01T00:00:00Z 0.052954561125284426
```

Top 10 lowest `ai_proportion_balanced`:

```text
IS 2024-12-01T00:00:00Z 0.0001193744777366599
IS 2023-09-01T00:00:00Z 0.00013743815283122595
IS 2018-09-01T00:00:00Z 0.00014367816091954023
IS 2021-05-01T00:00:00Z 0.00016452780519907864
IS 2021-01-01T00:00:00Z 0.00017627357659086903
IS 2022-08-01T00:00:00Z 0.00019376089905057158
IS 2020-05-01T00:00:00Z 0.0002004008016032064
IS 2019-12-01T00:00:00Z 0.00020271639975674033
IS 2021-08-01T00:00:00Z 0.0002051702913418137
BE 2020-08-01T00:00:00Z 0.00021372088053002778
```

Privacy note:

- This release package intentionally excludes local credential files.
- The included public run summary avoids machine-specific absolute paths.
