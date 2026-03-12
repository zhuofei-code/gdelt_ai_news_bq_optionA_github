# Improvement Plan for the AI Keyword Strategy

## Executive summary

The current production workflow is not English-only, but it is still
linguistically asymmetric.

The main issue is not the `strict` layer. The main issue is the expansion layer:

- `keywords_strict.txt` already includes many multilingual full-form AI terms
- `keywords_context.txt` is still English-only
- the abbreviation rule only recognizes `AI` and `A.I.`

This means non-English coverage can be undercounted when outlets use local
abbreviations or local policy, risk, labor, and governance vocabulary rather
than English context words.

The recommended fix is a versioned `v2` design:

- multilingual `strict`
- multilingual context
- country-aware abbreviation rules

The released panel should remain the baseline until the upgraded design is
validated.

## What needs to change

## 1. Expand the `strict` layer where language coverage is missing

The short-term priority is to fill clear gaps in the current full-form keyword
coverage.

Confirmed priorities:

- `BE`: add Dutch AI terms, because the current strict list covers French but
  not Dutch
- `IS`: add Icelandic AI terms, because Icelandic is currently missing from the
  strict list

Secondary priority:

- review Czech, Hungarian, Finnish, and Slovenian for common inflected or
  alternate phrasings that may still be missing

This is the lowest-risk change because full-form native-language AI phrases are
usually much less ambiguous than abbreviations.

## 2. Replace the English-only context layer with multilingual context support

The current `balanced` rule works as:

```text
balanced = strict OR ((AI or A.I.) AND context)
```

That structure can stay. What needs to change is the context vocabulary.

Instead of one English-only `keywords_context.txt`, `v2` should use
language-aware context resources built around the same concept families:

- regulation and law
- governance and oversight
- ethics, bias, and discrimination
- safety, harm, and misinformation
- privacy, surveillance, and security
- jobs, labor, automation, and productivity
- copyright, intellectual property, and data protection

The important point is that the concepts should stay stable across countries,
while the actual lexical realizations should be localized.

## 3. Replace one global abbreviation rule with country-aware rules

The current abbreviation rule is safe but narrow:

```text
AI or A.I. only
```

That avoids many false positives, but it is not language-neutral.

The recommended `v2` rule is to move to country-aware abbreviation patterns.

### First-wave safe additions

Only add abbreviations that are both common and relatively low-risk:

- `FR`: add `IA`
- `PT`: add `IA`
- `AT`: add `KI`

### Countries that should stay conservative at first

Do not add new abbreviations immediately for:

- `CZ`
- `FI`
- `HU`
- `IS`
- `PL`
- `SI`
- `UK`

These countries should keep `AI` and `A.I.` only until manual validation shows
that extra abbreviations are both common and precise.

### Belgium needs a separate treatment

`BE` is bilingual in the source design, so it should not be handled with one
country-wide abbreviation assumption.

Recommended approach:

- first add Dutch full-form strict terms
- then build separate French and Dutch context coverage
- only after that consider whether `IA` should be enabled for clearly
  francophone Belgian sources

## 4. Move configuration from global regexes to country-aware rules

The current runner builds one global `context_regex` and one global
`ai_abbrev_regex`. That is convenient, but it forces all countries into an
Anglicized expansion logic.

The better architecture is:

- one global strict list for shared full-form AI terms and model names
- optional language-specific strict additions
- country-specific context regex
- country-specific abbreviation regex

The cleanest way to represent this is a new config file such as:

- `config/country_language_rules.yaml`

For each country, this file should define:

- primary language or languages
- context keyword resource
- safe abbreviation regex
- optional exclusions or overrides

Then the SQL should apply the country-specific rules after the outlet-domain to
country mapping step, rather than using one global expansion rule for all rows.

## Proposed `v2` operating model

At the article level:

```text
strict_v2 = global_strict OR country_specific_strict
balanced_v2 = strict_v2 OR (country_abbrev AND country_context)
```

This preserves the original logic while removing the strongest language bias.

## Country priorities

The first validation wave should focus on the countries where the current design
is most likely to be asymmetric.

| Country | Reason for priority | Immediate action |
| --- | --- | --- |
| `IS` | Icelandic strict terms are missing | add validated Icelandic full-form AI terms before any abbreviation expansion |
| `BE` | French is covered better than Dutch | add Dutch strict terms and separate French/Dutch context support |
| `FI` | balanced-over-strict uplift is very small | inspect whether local AI coverage relies on missing context vocabulary |
| `HU` | balanced-over-strict uplift is very small | inspect whether local AI coverage relies on missing context vocabulary |
| `FR` | local abbreviation likely underused by current rule | test `IA` with French context vocabulary |
| `PT` | local abbreviation likely underused by current rule | test `IA` with Portuguese context vocabulary |
| `AT` | local abbreviation likely underused by current rule | test `KI` with German context vocabulary |

## Validation strategy

The upgraded design should not replace the released series until it has passed
both mechanical and manual checks.

### Mechanical checks

Run old and new keyword designs on the same source panel and compare:

- total AI article counts
- country-level changes in `ai_articles_strict`
- country-level changes in `ai_articles_balanced`
- balanced-over-strict uplift by country
- month-by-month ranking changes
- countries with the largest proportional jumps

### Manual precision checks

For each priority country, manually review samples from:

- newly captured `strict_v2` articles
- newly captured abbreviation-plus-context articles
- articles captured by local-language context expansions

The question is not only whether recall increases. The question is whether the
extra matches are genuinely AI-related.

### Release rule

Only replace the current released keyword design if both of these conditions
hold:

- recall improves in the targeted countries
- false-positive rates remain acceptably low in manual review

## Deliverables

The `v2` upgrade should produce five concrete outputs:

1. `config/keywords_strict_v2.txt`
2. `config/keywords_context_multilingual_v2.txt` or per-language context files
3. `config/country_language_rules.yaml`
4. runner and SQL support for country-specific abbreviation and context rules
5. a comparison report of `v1` versus `v2`

## Recommended implementation order

The practical rollout path is:

1. build `keywords_strict_v2.txt` with Dutch and Icelandic additions first
2. build multilingual context resources
3. add conservative country-specific abbreviation rules
4. run a full sensitivity test on the existing `Option A` panel
5. manually validate new captures in the priority countries
6. decide whether to publish `v2` as a replacement series or as a parallel
   robustness series

## Bottom line

The present keyword strategy is already stronger than a simple English keyword
list, but it is still not fully comparable across the `11` countries.

The highest-value upgrade is not just "more keywords." The highest-value
upgrade is:

- multilingual strict terms
- multilingual context support
- country-aware abbreviation rules

That combination is the most defensible way to reduce systematic undercounting
in non-English coverage without creating a large false-positive problem.
