# Comparison Report: Option A `v1` vs `v2` Keyword Strategy

## Scope

This report compares two `Option A` runs on the same outlet panel and the same
time window:

- `v1` baseline rerun: legacy global keyword logic
- `v2` seed rerun: country-aware multilingual context and abbreviation rules

Both runs use:

- `11` countries
- `5` mainstream + `5` specialist outlets per country
- `2018-06-01` to `2026-04-01` (end exclusive), which yields `94` monthly rows
  per country

Source files:

- `results/gdelt_ai_country_monthly_201806_202604_optionA_v1rerun.csv`
- `results/gdelt_ai_country_monthly_201806_202604_optionA_v2.csv`

Run logs:

- `results/fullrun_log_201806_202604_optionA_v1rerun.txt`
- `results/fullrun_log_201806_202604_optionA_v2.txt`

## Comparability note

The comparison is based on a same-day rerun of `v1`, not on the older released
`v1` file. That was necessary because the GDELT table is live and historical
counts can drift slightly over time.

Even after forcing a same-day baseline, the denominator is still not perfectly
identical:

- `v1` total `all_articles = 12,220,614`
- `v2` total `all_articles = 12,220,490`
- difference = `-124` articles, or about `-0.0010%`

That remaining drift is too small to matter substantively, but it should be
treated as live-table noise rather than a keyword effect.

## Dry-run cost

The two strategies cost essentially the same to scan.

- `v1`: `2,272,103,038,974` bytes, about `2.066466 TiB`, about `USD 12.92 / GBP 10.09`
- `v2`: `2,272,064,513,239` bytes, about `2.066431 TiB`, about `USD 12.92 / GBP 10.09`

So the multilingual `v2` design does not create a meaningful BigQuery cost
penalty.

## Executive summary

At the full-panel level:

- `v1`: `172,804` balanced AI articles, weighted `ai_proportion_balanced = 1.4140%`
- `v2`: `173,715` balanced AI articles, weighted `ai_proportion_balanced = 1.4215%`

Net effect:

- balanced AI articles rise by `+911` (`+0.53%`)
- weighted balanced AI proportion rises by `+0.0075` percentage points
- strict AI counts are effectively unchanged: `166,407` to `166,402`

The practical interpretation is clear: the seed `v2` design produces a modest
increase in measured AI coverage, but that increase comes almost entirely from
the broader `balanced` layer rather than the conservative `strict` layer.

## Country-level results

Weighted `ai_proportion_balanced`, aggregated across the full panel:

| Country | `v1` | `v2` | Change (percentage points) | Balanced article change |
| --- | ---: | ---: | ---: | ---: |
| France | `1.1031%` | `1.1630%` | `+0.0599` | `+684` |
| Portugal | `2.2767%` | `2.3096%` | `+0.0328` | `+181` |
| Austria | `0.8605%` | `0.8644%` | `+0.0039` | `+51` |
| Hungary | `0.4601%` | `0.4601%` | `+0.0000` | `0` |
| Slovenia | `0.3844%` | `0.3844%` | `+0.0000` | `0` |
| Czech Republic | `0.6305%` | `0.6305%` | `+0.0000` | `0` |
| Finland | `0.5383%` | `0.5383%` | `+0.0000` | `0` |
| Iceland | `0.0762%` | `0.0762%` | `+0.0000` | `0` |
| Belgium | `0.4731%` | `0.4731%` | `+0.0000` | `0` |
| United Kingdom | `2.0608%` | `2.0607%` | `-0.0001` | `-3` |
| Poland | `4.0072%` | `4.0071%` | `-0.0001` | `-2` |

The only substantively meaningful gains are:

- `FR`
- `PT`
- `AT`

Everything else is either flat or moving at a level that is best treated as
live-table noise.

## What changed mechanically

The `strict` layer is almost unchanged in this seed implementation.

- No country shows a meaningful increase in `ai_articles_strict`
- The net full-panel strict change is `-5`, which is far too small to interpret
  as a real keyword effect

So the observed uplift is almost entirely a `balanced`-layer effect.

That is consistent with the design of `v2`:

- `FR` gains from adding French abbreviation support such as `IA`
- `PT` gains from adding Portuguese abbreviation support such as `IA`
- `AT` gains from adding German abbreviation support such as `KI`

By contrast, the newly added Dutch and Icelandic strict terms do not produce an
observable country-level increase in this panel. That suggests either:

- those forms are rare in the relevant GDELT text fields, or
- the current source mix often surfaces AI stories through other already-covered
  markers

That second point is an inference from the results, not a direct outlet-level
validation.

## Stability across months

The uplift is not equally distributed across time.

Countries with persistent `v2` balanced gains:

- `FR`: `90 / 94` months higher
- `PT`: `70 / 94` months higher
- `AT`: `29 / 94` months higher, `65` tied

Countries that are effectively unchanged:

- `BE`, `CZ`, `FI`, `HU`, `IS`, `SI`: `94 / 94` months tied in balanced article counts

Tiny negative one-month deviations:

- `UK`: `1` month lower
- `PL`: `1` month lower

Those negative deviations are extremely small and should not be interpreted as
evidence that `v2` is actually removing AI matches. The more plausible reading
is residual table drift between the two runs.

## Largest monthly gains

The biggest single-month `balanced` gains are concentrated in France:

- `FR`, `2020-02`: `+99` articles, `+0.4874` percentage points
- `FR`, `2024-01`: `+35` articles, `+0.4409` percentage points
- `PT`, `2024-01`: `+24` articles, `+0.2656` percentage points

This pattern reinforces the view that the first successful `v2` effect is
mainly coming from local abbreviation-plus-context matching, not from global
structural changes across all countries.

## Ranking effects

The country ranking does not change.

The `balanced` ranking remains:

1. `PL`
2. `PT`
3. `UK`
4. `FR`
5. `AT`
6. `CZ`
7. `FI`
8. `BE`
9. `HU`
10. `SI`
11. `IS`

So the seed `v2` design changes levels more than it changes cross-national
ordering.

## Interpretation

This seed `v2` implementation does improve recall, but only modestly at the
full-panel level and mainly in three language environments:

- French
- Portuguese
- German

That makes the first conclusion fairly narrow:

- the strongest early value of `v2` is country-aware abbreviation handling

The second conclusion is more cautionary:

- simply adding multilingual strict terms is not enough by itself to move the
  released panel very much

In other words, the architecture change is useful, but the immediate empirical
payoff is concentrated rather than universal.

## Recommended next step

The next validation step should focus on `FR`, `PT`, and `AT`.

For those countries, manually inspect articles that are:

- captured by `v2`
- not captured by same-day `v1`
- driven by abbreviation-plus-context logic

That is the right way to determine whether the observed uplift is genuine recall
improvement or whether it is introducing new false positives.
