# Lowest AI Proportion in the Latest Option A Results

Source table: `results/gdelt_ai_country_monthly_201806_202506_optionA.csv`

## Bottom-Line Finding

In the latest `Option A` output, **Iceland (`IS`) has the lowest AI proportion** under both available definitions:

- `ai_proportion_balanced`: `0.0769%` (`408 / 530,229`)
- `ai_proportion_strict`: `0.0768%` (`407 / 530,229`)

This result is based on the full `2018-06-01` to `2025-06-01` panel, aggregated across all `84` months.

## Country Ranking by Weighted `ai_proportion_balanced`

| Rank | Country | Balanced AI proportion | Strict AI proportion | All articles | AI articles (balanced) |
|---|---|---:|---:|---:|---:|
| 1 | Iceland | 0.0769% | 0.0768% | 530,229 | 408 |
| 2 | Finland | 0.3589% | 0.3560% | 776,460 | 2,787 |
| 3 | Slovenia | 0.4029% | 0.3814% | 572,042 | 2,305 |
| 4 | Hungary | 0.4722% | 0.4717% | 632,327 | 2,986 |
| 5 | Belgium | 0.4919% | 0.4598% | 581,183 | 2,859 |
| 6 | Czech Republic | 0.6373% | 0.6162% | 1,149,317 | 7,325 |
| 7 | Austria | 0.7844% | 0.7479% | 1,178,701 | 9,246 |
| 8 | France | 1.1182% | 1.0560% | 1,052,310 | 11,767 |
| 9 | United Kingdom | 2.0303% | 1.9328% | 3,185,590 | 64,677 |
| 10 | Portugal | 2.0474% | 1.9484% | 479,983 | 9,827 |
| 11 | Poland | 3.7105% | 3.6587% | 990,842 | 36,765 |

Iceland is not just marginally lowest. Its balanced AI proportion is only about `21.4%` of Finland's, the second-lowest country.

## Why Iceland Looks So Low

### 1. The pattern is persistent, not a one-month anomaly

Iceland stays low throughout the panel:

- `2018`: `0.0926%`
- `2019`: `0.0956%`
- `2020`: `0.0755%`
- `2021`: `0.0673%`
- `2022`: `0.0552%`
- `2023`: `0.0795%`
- `2024`: `0.0776%`
- `2025` (Jan-May): `0.0705%`

Additional monthly diagnostics:

- `62 / 84` months are below `0.1%`
- `83 / 84` months are below `0.2%`
- lowest month: `2024-12`, `0.0119%` (`1 / 8,377`)
- highest month: `2019-10`, `0.2262%` (`12 / 5,305`)

So this is a structurally low series, not a result driven by one bad month.

### 2. The problem is not mainly the strict keyword rule

The gap between the two AI definitions is almost zero:

- balanced AI articles: `408`
- strict AI articles: `407`

That means loosening the rule barely changes Iceland's count. The low result therefore does **not** look like a case where Iceland has lots of borderline AI mentions that the strict rule misses.

### 3. A source-coverage explanation is plausible

The source-selection note already flags Iceland as the hardest market in the sample for specialist-domain coverage. The current Iceland source set is:

- mainstream: `ruv.is`, `mbl.is`, `visir.is`, `dv.is`, `stundin.is`
- specialist: `vb.is`, `startupiceland.com`, `laeknabladid.is`, `samorka.is`, `kjarninn.is`

The same note explicitly marks `startupiceland.com`, `samorka.is`, and `kjarninn.is` as the highest-priority domains to validate in profiling.

This matters because a very small or weakly archived specialist set can push AI proportions down even if AI coverage exists elsewhere in the national media system.

### 4. It is not simply a denominator artifact

Iceland's total article count (`530,229`) is not the largest in the sample. In fact, Portugal (`479,983`) and Slovenia (`572,042`) are in a similar volume range, yet both show much higher AI proportions. The Iceland result is low because the numerator is extremely small, not because the denominator is unusually inflated.

## Interpretation

The most defensible interpretation is:

1. Iceland is the lowest-AI-proportion country in the current published `Option A` panel.
2. That ranking is robust across both strict and balanced definitions.
3. The low value is probably a mix of real market size effects and measurement effects from specialist-domain selection.
4. The current public panel is not enough to attribute the shortfall to specific outlets, because it only publishes country-month aggregates rather than outlet-month counts.

## Recommended Next Check

If you want to validate whether Iceland is substantively low or mainly a source-selection artifact, the next best step is a domain-level diagnostic for the Iceland set, especially:

- `startupiceland.com`
- `samorka.is`
- `kjarninn.is`

That diagnostic should inspect continuity, archive coverage, total hit volume, and AI-hit concentration by domain before any source replacement decision.
