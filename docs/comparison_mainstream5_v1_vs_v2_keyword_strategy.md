# Comparison Report: Mainstream5 `v1` vs `v2` Keyword Strategy

## Scope

This report compares two `mainstream5` runs on the same outlet panel and the
same time window:

- `v1` baseline rerun: legacy global keyword logic
- `v2` seed rerun: country-aware multilingual context and abbreviation rules

Both runs use:

- `11` countries
- `5` mainstream outlets per country
- `2018-06-01` to `2026-04-01` (end exclusive), which yields `94` monthly rows
  per country

Source files:

- `results/gdelt_ai_country_monthly_201806_202604_mainstream5_v1rerun.csv`
- `results/gdelt_ai_country_monthly_201806_202604_mainstream5_v2.csv`

Run logs:

- `results/fullrun_log_201806_202604_mainstream5_v1rerun.txt`
- `results/fullrun_log_201806_202604_mainstream5_v2.txt`

## Comparability note

The comparison is based on a same-day rerun of `v1`, not on the older released
`mainstream5` file. That avoids conflating keyword changes with slow drift in
the live GDELT table.

Even after forcing a same-day baseline, the denominator is still not perfectly
identical:

- `v1` total `all_articles = 11,093,749`
- `v2` total `all_articles = 11,093,651`
- difference = `-98` articles, or about `-0.0009%`

That residual difference is negligible and is best treated as live-table noise.

## Dry-run cost

The two strategies cost essentially the same to scan.

- `v1`: `2,272,175,477,049` bytes, about `2.066566 TiB`, about `USD 12.92 / GBP 10.09`
- `v2`: `2,272,152,306,902` bytes, about `2.066545 TiB`, about `USD 12.92 / GBP 10.09`

So the `v2` keyword architecture does not materially change BigQuery cost for
the mainstream-only panel.

## Executive summary

At the full-panel level:

- `v1`: `157,829` balanced AI articles, weighted `ai_proportion_balanced = 1.4227%`
- `v2`: `158,539` balanced AI articles, weighted `ai_proportion_balanced = 1.4291%`

Net effect:

- balanced AI articles rise by `+710` (`+0.45%`)
- weighted balanced AI proportion rises by `+0.0064` percentage points
- strict AI counts are effectively unchanged: `151,898` to `151,894`

So the mainstream-only panel shows the same broad pattern as `Option A`: `v2`
adds a modest amount of AI recall, but almost entirely through the broader
`balanced` layer rather than the conservative `strict` layer.

## Country-level results

Weighted `ai_proportion_balanced`, aggregated across the full panel:

| Country | `v1` | `v2` | Change (percentage points) | Balanced article change |
| --- | ---: | ---: | ---: | ---: |
| France | `0.9903%` | `1.0481%` | `+0.0578` | `+498` |
| Portugal | `2.1482%` | `2.1815%` | `+0.0334` | `+179` |
| Austria | `0.7637%` | `0.7666%` | `+0.0029` | `+36` |
| Hungary | `0.4809%` | `0.4809%` | `+0.0000` | `0` |
| Czech Republic | `0.6679%` | `0.6679%` | `+0.0000` | `0` |
| Finland | `0.3174%` | `0.3174%` | `+0.0000` | `0` |
| United Kingdom | `2.0612%` | `2.0612%` | `+0.0000` | `0` |
| Slovenia | `0.3957%` | `0.3957%` | `+0.0000` | `0` |
| Iceland | `0.0771%` | `0.0771%` | `+0.0000` | `0` |
| Belgium | `0.4181%` | `0.4181%` | `+0.0000` | `0` |
| Poland | `4.7894%` | `4.7892%` | `-0.0003` | `-3` |

As in `Option A`, the only substantively meaningful gains are:

- `FR`
- `PT`
- `AT`

Everything else is flat at the country level.

## What changed mechanically

The `strict` layer is again almost unchanged.

- No country shows a meaningful increase in `ai_articles_strict`
- The net full-panel strict change is `-4`, which should be interpreted as
  live-table noise rather than a real keyword effect

The measurable change is therefore a `balanced`-layer effect, which is exactly
what the seed `v2` architecture was designed to test.

The most plausible interpretation is:

- `FR` gains from French abbreviation support such as `IA`
- `PT` gains from Portuguese abbreviation support such as `IA`
- `AT` gains from German abbreviation support such as `KI`

By contrast, the Dutch and Icelandic strict additions do not produce an
observable country-level lift in the mainstream-only panel.

That is an inference from aggregate results, not a direct outlet-level article
audit.

## Stability across months

The uplift is concentrated but persistent.

Countries with repeated `v2` balanced gains:

- `FR`: `81 / 94` months higher
- `PT`: `69 / 94` months higher
- `AT`: `24 / 94` months higher, `69` tied, `1` lower

Countries that are effectively unchanged:

- `BE`, `CZ`, `FI`, `HU`, `IS`, `SI`, `UK`: `94 / 94` months tied in balanced article counts

Tiny negative deviations:

- `PL`: `1` month lower
- `AT`: `1` month lower

Those tiny negative deviations are too small to interpret as genuine loss of AI
coverage. The more defensible reading is residual live-table drift between the
two runs.

## Largest monthly gains

The biggest single-month gains are again concentrated in France and Portugal:

- `FR`, `2020-02`: `+84` articles, `+0.4988` percentage points
- `PT`, `2024-01`: `+24` articles, `+0.2747` percentage points
- `PT`, `2020-02`: `+11` articles, `+0.3512` percentage points

This pattern supports the same conclusion as the `Option A` comparison: the
most immediate empirical benefit of `v2` is country-aware abbreviation-plus-
context matching.

## Ranking effects

The country ranking does not change.

The `balanced` ranking remains:

1. `PL`
2. `PT`
3. `UK`
4. `FR`
5. `AT`
6. `CZ`
7. `HU`
8. `BE`
9. `SI`
10. `FI`
11. `IS`

So the seed `v2` design changes levels slightly, but it does not change the
cross-national ordering of mainstream salience.

## Interpretation

The mainstream-only panel confirms the same substantive conclusion already seen
in `Option A`:

- the first successful empirical payoff of `v2` is concentrated in `FR`, `PT`,
  and `AT`

It also sharpens the caution:

- broad multilingual strict expansion by itself is not yet moving the panel much

So, at least in the current seed implementation, the most defensible story is
that country-aware abbreviation handling matters more than simply appending more
full-form local-language AI terms.

## Recommended next step

The next validation step should still focus on `FR`, `PT`, and `AT`.

For those countries, manually inspect articles that are:

- captured by `v2`
- not captured by same-day `v1`
- matched through abbreviation-plus-context logic

If those article audits look clean, the case for adopting `v2` as a robustness
series becomes much stronger.
