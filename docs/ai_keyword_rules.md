# AI-related article identification rules (GDELT news)

## 1. Overview
Purpose, identify AI related news articles in GDELT.
Two tier definition, Strict and Balanced.

## 2. Rule A: Strict definition
An article is AI related if it matches any long form AI term, or any distinctive model and product name.
Short ambiguous abbreviations are excluded as standalone triggers, for example AI, IA, SI, ML, KI.
Matching procedure uses lowercasing, with boundary aware regex to avoid substring matches.

Regex pattern style:

```text
(?:^|[^a-z0-9])<phrase>(?:[^a-z0-9]|$)
```

## 3. Rule B: Balanced definition
Balanced match is Strict match, or AI abbreviation match with context match.
AI abbreviation match includes AI and A.I. as standalone tokens with boundaries.
Context match uses governance, risk, and impact terms from keywords_context.txt.

Formula:

```text
balanced = strict OR (abbrev_AI AND context)
```

## 4. Notes on interpretation
ai_proportion is the share of AI related coverage within all articles from selected domains.
ai_tone is the mean GDELT tone among matched AI articles, it reflects overall article tone, not necessarily attitude toward AI.

## 5. Appendix A: Strict keyword list

| Keyword |
|---|
| artificial intelligence |
| machine learning |
| deep learning |
| neural network |
| large language model |
| generative ai |
| foundation model |
| transformer model |
| prompt engineering |
| retrieval augmented generation |
| fine tuning |
| ai regulation |
| algorithmic bias |
| ai ethics |
| automated decision making |
| ai governance |
| synthetic data |
| ai safety |
| chatgpt |
| openai |
| claude |
| gemini |
| copilot |
| intelligence artificielle |
| apprentissage automatique |
| apprentissage profond |
| réseau neuronal |
| modèle de langage |
| grand modèle de langage |
| modèle génératif |
| ia générative |
| éthique de l’ia |
| régulation de l’ia |
| künstliche intelligenz |
| maschinelles lernen |
| neuronales netz |
| sprachmodell |
| großes sprachmodell |
| generative ki |
| ki regulierung |
| ki ethik |
| inteligência artificial |
| aprendizagem automática |
| aprendizagem profunda |
| rede neural |
| ia generativa |
| modelo de linguagem |
| regulação da ia |
| sztuczna inteligencja |
| uczenie maszynowe |
| głębokie uczenie |
| sieć neuronowa |
| generatywna si |
| umělá inteligence |
| strojové učení |
| generativní ai |
| mesterséges intelligencia |
| gépi tanulás |
| generatív mi |
| tekoäly |
| koneoppiminen |
| umetna inteligenca |
| gpt-5 |
| gpt 5 |
| gpt-5.1 |
| gpt 5.1 |
| gpt-5.2 |
| gpt 5.2 |
| gpt-4 |
| gpt 4 |
| gpt-4.1 |
| gpt 4.1 |
| gpt-4o |
| gpt 4o |
| gpt-4.5 |
| gpt 4.5 |
| codex |
| gpt-5-codex |
| gpt-5.1-codex |
| gpt-5.2-codex |
| anthropic |
| claude opus |
| claude sonnet |
| claude haiku |
| google gemini |
| gemma |
| palm |
| palm 2 |
| microsoft copilot |
| phi-2 |
| phi 2 |
| phi-3 |
| phi 3 |
| phi-4 |
| phi 4 |
| llama |
| llama 2 |
| llama 3 |
| llama 3.1 |
| llama 3.2 |
| llama 4 |
| mistral |
| mistral large |
| mistral small |
| mixtral |
| mixtral 8x7b |
| mixtral 8x22b |
| pixtral |
| grok |
| grok 1 |
| grok 2 |
| grok 2.5 |
| grok 3 |
| deepseek |
| deepseek-llm |
| deepseek r1 |
| deepseek-r1 |
| deepseek v3 |
| deepseek-v3 |
| deepseek v2 |
| deepseek-v2 |
| qwen |
| qwen2 |
| qwen 2 |
| qwen2.5 |
| qwen 2.5 |
| qwen3 |
| qwen 3 |
| hunyuan |
| 腾讯混元 |
| ernie |
| ernie bot |
| 文心一言 |
| 讯飞星火 |
| sparkdesk |
| glm |
| chatglm |
| glm-4 |
| kimi |
| moonshot |
| 01.ai |
| baichuan |
| baichuan2 |
| doubao |
| cohere |
| command |
| command r |
| command r+ |
| command r plus |
| ai21 |
| jurassic |
| jamba |
| dbrx |
| falcon |
| stablelm |
| stable lm |
| amazon nova |
| nova micro |
| nova lite |
| nova pro |
| bloom |
| mpt |
| olmo |
| pythia |
| bert |

## 6. Appendix B: Context keyword list

| Keyword |
|---|
| regulation |
| regulated |
| regulator |
| policy |
| policies |
| law |
| laws |
| act |
| legislation |
| governance |
| oversight |
| ethic |
| ethics |
| ethical |
| bias |
| biased |
| fairness |
| discrimination |
| accountability |
| transparency |
| risk |
| risks |
| safety |
| harm |
| harms |
| misinformation |
| disinformation |
| deepfake |
| deepfakes |
| fraud |
| scam |
| scams |
| security |
| cybersecurity |
| privacy |
| surveillance |
| jobs |
| job |
| employment |
| workforce |
| automation |
| automated |
| productivity |
| chatbot |
| chatbots |
| hallucination |
| hallucinations |
| generative |
| generator |
| synthetic |
| copyright |
| intellectual property |
| data protection |
