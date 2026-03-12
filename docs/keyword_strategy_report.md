# Keyword Strategy for BigQuery AI-News Scanning

## What the production workflow actually uses

The current production workflow uses a **two-tier keyword strategy** called
`strict+balanced`.

This is not based on a single keyword file. It uses:

- `config/keywords_strict.txt`
- `config/keywords_context.txt`

It also uses a separate hard-coded abbreviation rule for `AI` and `A.I.` in the
Python runner.

The older file `config/keywords.txt` is **not** used by the current production
pipeline. It is a legacy or exploratory list and should not be cited as the
active rule base for the released panels.

## Core logic

The workflow defines two article-level AI indicators:

1. `strict`
2. `balanced`

The governing mode in the runner is:

```text
KEYWORDS_MODE = "strict+balanced"
```

In operational terms:

```text
strict = article matches any term in keywords_strict.txt
balanced = strict OR ((AI or A.I.) AND any term in keywords_context.txt)
```

The `AI` abbreviation itself is handled separately through this boundary-aware
regex:

```text
(?:^|[^a-z0-9])(?:ai|a\.i\.)(?:[^a-z0-9]|$)
```

So the pipeline does **not** treat every mention of `AI` as automatically
AI-related. An article that only contains `AI` counts as `balanced` only when
`AI` appears together with a context term such as regulation, bias, safety,
privacy, automation, copyright, and so on.

## Matching procedure

The SQL pipeline first builds a lowercased text field from the following GDELT
GKG fields:

- `V2Themes`
- `Themes`
- `V2Persons`
- `V2Organizations`
- `AllNames`
- `Locations`

These fields are concatenated into a single lowercased string and then scanned
with regular expressions.

Phrase matching uses boundary-aware regex generation in the Python runner, with
the form:

```text
(?:^|[^a-z0-9])<phrase>(?:[^a-z0-9]|$)
```

This is meant to reduce accidental substring matches.

## Current file counts

In the current public repository:

- `keywords_strict.txt` contains `165` entries
- `keywords_context.txt` contains `53` entries
- `keywords.txt` contains `80` entries, but is not used in production

## What is in the strict list

The strict list is intentionally broad but still requires relatively explicit AI
language. It includes four main families of terms.

### 1. Core AI concepts

Examples:

- `artificial intelligence`
- `machine learning`
- `deep learning`
- `neural network`
- `large language model`
- `generative ai`
- `foundation model`
- `transformer model`
- `prompt engineering`
- `retrieval augmented generation`
- `fine tuning`

### 2. AI governance and risk phrases

Examples:

- `ai regulation`
- `algorithmic bias`
- `ai ethics`
- `automated decision making`
- `ai governance`
- `synthetic data`
- `ai safety`

### 3. Model, vendor, and product names

Examples:

- `chatgpt`
- `openai`
- `claude`
- `gemini`
- `copilot`
- `gpt-5`
- `gpt-4`
- `gpt-4o`
- `codex`
- `anthropic`
- `gemma`
- `mistral`
- `mixtral`
- `grok`
- `deepseek`
- `qwen`
- `ernie`
- `chatglm`
- `kimi`
- `cohere`
- `dbrx`
- `falcon`
- `stablelm`
- `amazon nova`
- `bert`

### 4. Multilingual AI terms

The strict list also includes non-English AI vocabulary for the countries in the
sample and nearby language environments.

Examples:

- French: `intelligence artificielle`, `apprentissage automatique`
- German: `künstliche intelligenz`, `maschinelles lernen`
- Portuguese: `inteligência artificial`, `aprendizagem automática`
- Polish: `sztuczna inteligencja`, `uczenie maszynowe`
- Czech: `umělá inteligence`, `strojové učení`
- Hungarian: `mesterséges intelligencia`, `gépi tanulás`
- Finnish: `tekoäly`, `koneoppiminen`
- Slovenian: `umetna inteligenca`

The strict list therefore captures both general AI terminology and brand/model
references that commonly signal AI-related coverage.

## What is in the context list

The context list is smaller and is only used together with the `AI`/`A.I.`
abbreviation rule. It is designed to catch cases where short-form `AI` appears
in a clearly policy, risk, labor, or impact-oriented setting.

Examples from `keywords_context.txt`:

- regulation and policy: `regulation`, `regulator`, `policy`, `law`, `legislation`, `governance`, `oversight`
- ethics and fairness: `ethic`, `ethics`, `ethical`, `bias`, `fairness`, `discrimination`, `accountability`, `transparency`
- risk and safety: `risk`, `safety`, `harm`, `misinformation`, `disinformation`, `deepfake`, `fraud`, `security`, `cybersecurity`, `privacy`, `surveillance`
- labor and automation: `jobs`, `employment`, `workforce`, `automation`, `automated`, `productivity`
- generative AI symptoms and applications: `chatbot`, `hallucination`, `generative`, `synthetic`
- legal/data issues: `copyright`, `intellectual property`, `data protection`

## Why the workflow uses two tiers

The split between `strict` and `balanced` is deliberate.

- `strict` is the conservative indicator. It tries to count only articles with
  explicit AI wording or highly distinctive AI model/vendor references.
- `balanced` is the broader indicator. It keeps all `strict` matches, but also
  allows short-form `AI` when the surrounding language strongly suggests an
  AI-related policy, risk, or impact discussion.

This is why the released datasets expose both:

- `ai_articles_strict`
- `ai_proportion_strict`
- `ai_articles_balanced`
- `ai_proportion_balanced`

## What should be cited in the GitHub repo

If the repository needs one short description of the scanning strategy, the most
accurate wording is:

> AI-related coverage is identified using a two-tier `strict+balanced` keyword
> design. `Strict` matches explicit AI terms and distinctive model/vendor names
> from `keywords_strict.txt`. `Balanced` equals `strict` plus standalone `AI` or
> `A.I.` mentions when they co-occur with governance, risk, labor, or impact
> terms from `keywords_context.txt`.

## Files to cite

- `config/keywords_strict.txt`
- `config/keywords_context.txt`
- `code/run_gdelt_bigquery.py`
- `code/bq_queries.sql`

These four files define the active production keyword logic.
