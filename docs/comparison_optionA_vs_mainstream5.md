# Comparison Report: Option A vs Mainstream-Only 5

## Scope

This report compares two released source designs built on the same extraction
pipeline and the same fixed time window, `2018-06-01` to `2025-06-01`:

- `Option A`: `5` mainstream + `5` specialist outlets per country
- `mainstream5`: `5` mainstream outlets only, with all specialist outlets removed

Source tables:

- `results/gdelt_ai_country_monthly_201806_202506_optionA.csv`
- `results/gdelt_ai_country_monthly_201806_202506_mainstream5.csv`

Both runs cover `11` countries and `84` monthly observations per country.

## Executive Summary

The mainstream-only version is not a trivial subset. It changes the level of
measured AI attention in several countries, and it changes the interpretation
of the panel.

At the full-panel level:

- `Option A`: `11,128,984` total articles, `150,952` balanced AI articles, weighted `ai_proportion_balanced = 1.3564%`
- `mainstream5`: `10,092,134` total articles, `139,522` balanced AI articles, weighted `ai_proportion_balanced = 1.3825%`

So after removing specialist outlets:

- total article volume falls by `9.32%`
- balanced AI article volume falls by `7.57%`
- the overall balanced AI proportion rises by `0.0261` percentage points

The reason is straightforward: specialist outlets add substantial volume, but
that added volume is not uniformly more AI-intensive than mainstream coverage.

## Country-Level Results

Weighted `ai_proportion_balanced`, aggregated across the full panel:

| Country | Option A | Mainstream5 | Change (percentage points) | Reading |
|---|---:|---:|---:|---|
| Poland | 3.7105% | 4.4613% | +0.7509 | removing specialist outlets raises measured AI salience sharply |
| Czech Republic | 0.6373% | 0.6751% | +0.0377 | modest increase |
| Hungary | 0.4722% | 0.4906% | +0.0183 | modest increase |
| Slovenia | 0.4029% | 0.4175% | +0.0146 | modest increase |
| United Kingdom | 2.0303% | 2.0413% | +0.0110 | near-flat, slight increase |
| Iceland | 0.0769% | 0.0773% | +0.0004 | effectively unchanged |
| Finland | 0.3589% | 0.3073% | -0.0516 | moderate decrease |
| Belgium | 0.4919% | 0.4311% | -0.0608 | moderate decrease |
| Austria | 0.7844% | 0.7038% | -0.0806 | clear decrease |
| France | 1.1182% | 1.0100% | -0.1082 | clear decrease |
| Portugal | 2.0474% | 1.9291% | -0.1183 | largest decrease |

## What Changed Mechanically

Removing specialist outlets lowers both the denominator (`all_articles`) and
the numerator (`ai_articles_balanced`). The direction of the proportion change
depends on which of those falls faster.

Examples:

- `Poland`: total volume falls by `21.07%`, but balanced AI volume falls by only `5.10%`. Result: the AI proportion rises sharply.
- `France`: total volume falls by `26.16%`, but balanced AI volume still falls even faster, by `33.31%`. Result: the AI proportion declines.
- `Portugal`: total volume falls by only `2.63%`, but balanced AI volume falls by `8.25%`. Result: the AI proportion declines.
- `Iceland`: total volume falls by `7.09%` and balanced AI volume falls by `6.62%`. Result: almost no change.

This is the core interpretation rule for the comparison:

- if the proportion rises after removing specialist outlets, the specialist set was adding relatively more non-AI volume than AI volume
- if the proportion falls after removing specialist outlets, the specialist set was contributing relatively AI-dense coverage

## Stability Across Months

The country-level differences are not equally stable.

Countries where `mainstream5` is higher in most months:

- `Poland`: `81 / 84` months
- `Czech Republic`: `72 / 84` months
- `Slovenia`: `71 / 84` months
- `Iceland`: `64 / 84` months, but with extremely small magnitudes
- `United Kingdom`: `58 / 84` months

Countries where `mainstream5` is lower in most months:

- `Austria`: `78 / 84` months
- `Finland`: `65 / 84` months
- `France`: `62 / 84` months

Mixed cases:

- `Belgium`: `37` months higher, `47` lower
- `Portugal`: `38` months higher, `42` lower, `4` tied
- `Hungary`: `48` higher, `18` lower, `18` tied

This means the largest changes are not just one-off outliers. The Poland and
Austria patterns, in particular, are persistent across the panel.

## Country Ranking Effects

Some rankings stay intact, some move:

- `Iceland` remains the lowest-AI-proportion country in both designs
- `Poland` remains the highest-AI-proportion country in both designs
- `United Kingdom` moves above `Portugal` in the mainstream-only version
- `Belgium` and `Hungary` switch order in the lower-middle part of the ranking

So the design change affects both levels and relative ranking.

## Interpretation

The two designs answer slightly different questions.

`Option A` is closer to a broader national information environment that mixes
general-interest coverage with sector-specific reporting. It is useful if the
research question is about AI attention across the wider media system.

`mainstream5` is cleaner if the goal is to compare public-facing, mass-audience
news agendas across countries without specialist-domain effects. It is the
better baseline if you want "popular mainstream coverage" rather than a hybrid
mainstream-specialist media ecology.

Based on the current results:

- use `mainstream5` as the primary specification if your conceptual target is national mainstream salience
- keep `Option A` as a robustness or alternative-specification check
- do not treat the two panels as interchangeable

## Limits

This report compares released country-month aggregates. It does not include
domain-level outlet-month output.

That means we can identify where the specialist set changes the country-level
series, but we cannot yet say which specific specialist outlet is responsible
for the change in each country.

If that level of attribution matters, the next step is an outlet-level
diagnostic for the `Option A` domains.
