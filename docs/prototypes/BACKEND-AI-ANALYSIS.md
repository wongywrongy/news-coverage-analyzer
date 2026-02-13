# ClearSignal Backend AI Analysis

## Overview

ClearSignal uses **6 distinct AI call sites** across the backend pipeline. Five use Anthropic (Claude), one uses OpenAI. No bias labels are ever sent to any AI prompt — framing is classified from article text alone.

---

## Pipeline Flow & AI Touchpoints

```
INGEST → EMBED → CLUSTER → LABEL → SCORE → SCRAPE → FRAMING → ANALYZE
           ^                  ^       ^                  ^         ^
         OpenAI            Claude   Claude            Claude    Claude
       embeddings          Haiku    Haiku             Haiku    Sonnet
```

---

## 1. Embedding (OpenAI)

**File:** `backend/ingestion/embed.py`
**Model:** `text-embedding-3-small` (384 dimensions)
**Cost:** ~$0.0001 per article

### What's sent per article
```
"{title}. {description[:200]}"
```

- Title + first 200 chars of description
- No body text, no bias labels, no source info
- Batched in groups of 100

### Purpose
Generates vector embeddings for clustering articles into stories by topic similarity.

### Fallback
Local `all-MiniLM-L6-v2` model (same 384-dim output) when OpenAI is unavailable.

---

## 2. Topic Labeling (Claude Haiku)

**File:** `backend/clustering/label.py`
**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 50
**Cost:** ~$0.001 per 20 stories

### System prompt
None (uses user prompt only).

### What's sent per story
```
You are a wire-service editor writing a topic slug.
Given these headlines about the same story, generate a concise
3-8 word neutral topic label. No punctuation. No articles (a, an, the).
Just the factual topic.

Examples of good labels:
- Senate Passes Immigration Reform Bill
- SC Measles Outbreak Reaches 900 Cases
- Federal Reserve Holds Interest Rates
- Ukraine Russia Ceasefire Negotiations

Headlines:
- {headline 1}
- {headline 2}
- ... (up to 15 deduplicated headlines)

Topic label:
```

### Article content included
- Headlines only (up to 15)
- NO body text, NO descriptions, NO source names

### Triggers
Only runs when a story topic looks like a placeholder (contains " - ", " | ", >80 chars, quotes, "...", or starts lowercase).

---

## 3. Headline Refinement (Claude Haiku)

**File:** `backend/analysis/headlines.py`
**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 256
**Cost:** ~$0.001 per story

### System prompt
```
You rewrite vague or generic news story titles into specific, neutral
headlines. You follow strict rules for neutrality.
```

### What's sent per story
```
Rewrite this story title to be specific and neutral.

Current title: {topic}

Article headlines from this cluster:
- {title} ({source_name})
- ... (up to 20 articles)

Rules:
- Maximum 12 words.
- Use factual, descriptive language only.
- No emotional adjectives (devastating, controversial, unprecedented,
  alarming, historic, shocking).
- No loaded framing: prefer 'X would change Y by Z' over 'X threatens Y'
  or 'X saves Y.'
- Identify the most specific shared subject across articles.
- If articles describe different angles of one event, lead with the
  event, not the angle.

Respond ONLY with valid JSON:
{
  "headline": "<max 12 words, specific, neutral>",
  "rationale": "<one sentence>"
}
```

### Article content included
- Headlines + source names (up to 20)
- NO body text, NO descriptions

### Triggers
Only runs when topic contains vague words ("various", "multiple", "several", etc.) or is >15 words.

---

## 4. Impact Scoring (Claude Haiku)

**File:** `backend/scoring/impact.py`
**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 1,024
**Cost:** ~$0.002 per story

### System prompt
```
You are a news significance scorer. You evaluate the real-world impact
of a news story using 5 measurable factors. You are descriptive, not
prescriptive. You do not judge whether a story 'deserves' coverage —
you estimate its tangible impact on people and systems.
```

### What's sent per story
```
Evaluate the significance of this news story.

Story title: {topic}
Article headlines and excerpts:
- {title} ({source_name}): "{first 150 words of body or description}"
- ... (up to 50 articles)

Score each factor from 0 to its maximum. Base scores ONLY on facts
stated or directly implied in the articles.

Factors:
1. population_affected (0-30): Number of people who experience direct,
   tangible consequences. [detailed scoring rubric]
2. economic_magnitude (0-25): [detailed scoring rubric]
3. policy_change (0-20): [detailed scoring rubric]
4. duration (0-15): [detailed scoring rubric]
5. irreversibility (0-10): [detailed scoring rubric]

Rules:
- Do not inflate scores based on emotional language in articles.
- Do not score based on how 'interesting' or 'clickable' the story is.
- When in doubt, score lower and flag insufficient data.

Respond ONLY with valid JSON:
{
  "significance_score": <sum of 5 factors, 0-100>,
  "factors": {
    "population_affected": {"score": <int>, "rationale": "<one sentence>"},
    "economic_magnitude": {"score": <int>, "rationale": "<one sentence>"},
    "policy_change": {"score": <int>, "rationale": "<one sentence>"},
    "duration": {"score": <int>, "rationale": "<one sentence>"},
    "irreversibility": {"score": <int>, "rationale": "<one sentence>"}
  },
  "insufficient_data": ["<factors scored 0 due to missing info>"],
  "confidence": "low" | "medium" | "high"
}
```

### Article content included
- Headlines + source names
- Body/description excerpts: **first 150 words** per article
- Up to **50 articles** (most recent first)
- NO bias labels

### Triggers
- Never been scored (impact_score = 0 or NULL)
- Article count grew >20% since last score
- Last scored >6 hours ago AND has new articles

---

## 5. Framing Classification (Claude Haiku)

**File:** `backend/analysis/framing.py`
**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 512
**Cost:** ~$0.001 per article

### System prompt
```
You classify the editorial framing of a single news article. You
describe WHAT the article emphasizes, not WHERE it falls on a political
spectrum. You do not judge source credibility.
```

### What's sent per article
```
Classify the framing of this article.

Source: {source_name}
Headline: {title}
Excerpt (first 300 words): {body excerpt}

Other articles on this story (for comparison):
- {other_title} ({other_source})
- ... (up to 10 other article headlines)

Framing categories (select all that apply):
- "economic impact" — focuses on financial consequences, markets, costs, jobs
- "social/cultural impact" — focuses on communities, identity groups, social norms
- "policy/regulatory" — focuses on laws, rules, government action
- "human interest" — focuses on individual people, personal stories
- "geopolitical" — focuses on international relations, power dynamics
- "security/safety" — focuses on threats, risks, protection
- "factual/wire" — primarily factual reporting with minimal framing

Respond ONLY with valid JSON:
{
  "source": "{source_name}",
  "framings": ["<all applicable categories>"],
  "primary_framing": "<single dominant category>",
  "notable_inclusions": "<facts/angles present here but absent elsewhere>",
  "notable_omissions": "<facts/angles in other articles but absent here>"
}
```

### Article content included
- **Main article:** source name, headline, first 300 words of body
- **Context:** up to 10 other article headlines from same story cluster
- NO bias labels, NO political classifications

### Runs
Up to **8 articles per story** (to control costs). Called before the main analysis generation.

---

## 6. Full Analysis Generation (Claude Sonnet)

**File:** `backend/analysis/generator.py`
**Model:** configurable via `settings.claude_model` (default: `claude-sonnet-4-20250514`)
**Max tokens:** configurable via `settings.max_analysis_tokens`
**Cost:** ~$0.05-0.15 per story (highest cost call)

### System prompt
```
You are a news analyst for ClearSignal, a platform that shows readers
how the same story is covered across the political spectrum. Your
analysis must be rigorously neutral. You describe patterns — you do
not evaluate whether coverage is 'good,' 'bad,' 'sufficient,' or
'insufficient.' You never tell readers what to think.

Guiding principles:
- Attribute all contested claims to their source.
- When sources disagree on facts, state both versions without adjudicating.
- Do not use emotional or evaluative adjectives unless directly quoting.
- Do not infer motives for why outlets covered or framed a story.
- If all sources agree on framing, say so. Do not fabricate disagreement.
- Acknowledge when information is incomplete, developing, or uncertain.
- Do not reference political lean labels (left, right, center).

Respond in JSON only. No markdown, no preamble.
```

### What's sent per story
```
Analyze this story for ClearSignal readers.

Story: {topic}
Category: {category}
Impact score: {impact_score}/100 (factors: {significance_factors JSON})
Attention score: {attention_score}/100
Number of articles: {total} from {source_count} sources

Article excerpts (first 300 words each, {N} of {total}):

Source: {source_name}
Headline: {title}
Published: {published_at}
{description}
Excerpt: {first 300 words of body}
---
... (up to 8 selected articles)

Per-article framing analysis (pre-computed):
- {source}: primary framing = {framing}, notable inclusions = ..., notable omissions = ...
- ... (for each classified article)

Produce the following fields:
{
  "headline": "<max 12 words, neutral, factual>",
  "lede": "<2-3 sentences, who/what/when/where, max 60 words>",
  "context": "<5-7 paragraphs, in-depth background...>",
  "source_framings": [{ source, framings[], primary_framing, notable_inclusions, notable_omissions }],
  "contrasts": [{ theme, sourceA, framingA, claimA, sourceB, framingB, claimB }],
  "facts": [{ claim, reality, verdict }],
  "bottom_line": "<3-4 sentences, concrete impacts on reader>",
  "spectrum": "<1-2 sentences, overall coverage pattern>",
  "coverage_note": "<1 sentence, coverage volume vs impact>",
  "framing_check": "<internal audit, not user-facing>"
}
```

### Article selection strategy (8 of N articles)
1. Always include the **most recent** article
2. Always include the **earliest** article
3. Pick **one article per political lean** (LEFT, LEFT-CENTER, CENTER, RIGHT-CENTER, RIGHT) — chosen by longest body text
4. Fill remaining slots with most recent articles

### Article content included per selected article
| Field | Included | Limit |
|-------|----------|-------|
| source_name | Yes | — |
| title | Yes | — |
| published_at | Yes | — |
| description | Yes | Full |
| body | Yes | **First 300 words** |
| source_bias | **NO** | Not sent (by design) |
| source_domain | **NO** | Not sent |
| embedding | **NO** | Not sent |

### Pre-computed context also included
- Per-article framing analysis from Step 5 (if available)
- Story impact score + significance factor breakdown
- Story attention score

### Triggers
- No existing analysis
- Article count grew >30% since last generation
- Last generated >12 hours ago AND has new articles

---

## Article Body Scraping (No AI)

**File:** `backend/ingestion/scraper.py`
**Tool:** trafilatura (HTML → text extraction)

### What's extracted
- Full article body text from URL
- Truncated to **2,000 characters** (~300 words)
- Boilerplate, ads, navigation stripped

### Skipped domains (paywall/anti-scraper)
WSJ, FT, Bloomberg, NYTimes, WashPost, The Athletic, The Economist, Barron's, Google News, Politico, Axios

### Rate limit
1 request per second, max 50 articles per pipeline cycle.

---

## Summary: What AI Sees Per Article

| Stage | Source Name | Headline | Description | Body Excerpt | Bias Label | Other Articles |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| Embedding | - | title | 200 chars | - | - | - |
| Labeling | - | title only | - | - | - | 14 other headlines |
| Headlines | source | title only | - | - | - | 19 other headlines |
| Impact | source | title | - | 150 words | - | 49 other articles |
| Framing | source | title | - | 300 words | - | 10 other headlines |
| Analysis | source | title | full | 300 words | - | 7 other full articles |

---

## Cost Estimate Per Pipeline Cycle

| Call | Model | Per-unit | Typical volume | Est. cost |
|------|-------|----------|----------------|-----------|
| Embedding | text-embedding-3-small | ~$0.0001 | 50-200 articles | $0.005-0.02 |
| Labeling | Haiku 4.5 | ~$0.001 | 5-15 stories | $0.005-0.015 |
| Headlines | Haiku 4.5 | ~$0.001 | 2-5 stories | $0.002-0.005 |
| Impact | Haiku 4.5 | ~$0.002 | 10-30 stories | $0.02-0.06 |
| Framing | Haiku 4.5 | ~$0.001/article | 16-40 articles | $0.016-0.04 |
| Analysis | Sonnet | ~$0.05-0.15 | 3-5 stories | $0.15-0.75 |
| **Total** | | | | **~$0.20-0.90** |

Analysis generation (Sonnet) accounts for ~75-85% of total API cost per cycle.

---

## Key Design Decisions

1. **No bias labels in prompts.** Source political lean is never sent to any AI call. Framing is classified purely from article text. This is a deliberate design choice (CONFLICT-05 resolution) to prevent the AI from pattern-matching based on outlet reputation.

2. **Body text is always truncated.** Embedding gets 200 chars of description. Impact scoring gets 150 words. Framing + analysis get 300 words. Full article bodies are never sent.

3. **Article selection for analysis is diversity-weighted.** The analysis generator picks 1 article per political lean bucket, then fills with recency. This ensures the AI sees coverage from across the spectrum without knowing which direction each source leans.

4. **Two-pass framing → analysis.** Framing is classified per-article first (Haiku, cheap), then the framing results are passed as structured context to the full analysis (Sonnet, expensive). This gives Sonnet pre-digested editorial perspective data to work with.

5. **All prompts enforce neutrality.** Every system prompt and user message explicitly forbids emotional language, political labels, motive inference, and editorializing. The framing_check field in analysis output is an internal audit log of framing choices made by the AI.
