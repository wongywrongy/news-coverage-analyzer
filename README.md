# ClearSignal

Multi-perspective news analysis platform. Tracks 100+ sources across the political spectrum, clusters articles into stories, scores coverage gaps, and generates neutral AP-style analyses.

## Commands

### Frontend

```bash
cd frontend
npm install
npm run dev          # Dev server at localhost:3000
npm run build        # Production build
npm run lint         # ESLint check
```

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows ssss
pip install -r requirements.txt

# Full pipeline (ingest → cluster → score → select → scrape → analyze)
python -m pipeline.main

# Run individual stages
python -m pipeline.main ingest           # fetch + normalize + embed + store
python -m pipeline.main cluster          # assign, discover, split, label, rename, merge, validate
python -m pipeline.main validate         # filter non-current topics (standalone)
python -m pipeline.main score            # impact, coverage, attention, sentiment, timeline, gaps, ranking, insights
python -m pipeline.main select           # GPT-4o-mini editorial selection
python -m pipeline.main scrape           # extract article bodies
python -m pipeline.main analyze          # framing + Claude AP-style analyses

# Daemon mode (full pipeline on schedule, default 15min)
python -m pipeline.main --daemon
python -m pipeline.main --daemon --interval 30

# Dry run (no DB writes)
python -m pipeline.main --dry-run
python -m pipeline.main ingest --dry-run

# One-off scripts
python -m scripts.backfill_analyses
python -m scripts.scrape_backfilla
python -m scripts.backfill_time_metadata
python -m scripts.filter_topics
python -m scripts.migrate_headlines              # dry run (preview headline fixes)
python -m scripts.migrate_headlines --apply      # apply headline fixes
```

### Environment Variables

Copy `.env.example` (backend) and `.env.local.example` (frontend):

```
# backend/.env
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
NEWSDATA_API_KEY=
EMBEDDING_MODE=openai        # or "local"

# frontend/.env.local
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## Tech Stack

**Frontend:** Next.js 14, React 18, Supabase JS client
**Backend:** Python 3, async pipeline, Anthropic Claude, OpenAI embeddings
**Database:** Supabase (PostgreSQL + pgvector)
**Styling:** Inline styles, Source Serif 4 + JetBrains Mono fonts

## File Map

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `app/page.js` | Homepage — fetches stories + stats, renders Header/Hero/CoverageMonitor |
| `app/story/[id]/page.js` | Story detail page — fetches story + analysis by ID |
| `app/layout.js` | Root layout with font imports and metadata |
| `app/globals.css` | Global resets, keyframe animations, dark theme base |
| `lib/constants.js` | Category groups, scoring helpers, activity day computation |
| `lib/queries.js` | Supabase query functions for stories, analyses, stats |
| `lib/supabase.js` | Supabase client singleton |
| `components/Header.jsx` | Site header with tracking count |
| `components/Hero.jsx` | Hero section with tagline, stat mosaic, stats band |
| `components/CategoryNav.jsx` | 4-group category navigation with activity indicators |
| `components/CoverageMonitor.jsx` | Main story list with category grouping and coverage filters |
| `components/CategorySection.jsx` | Collapsible story grid section per category group |
| `components/CoverageCard.jsx` | Story card with timeline, coverage label, scores |
| `components/CoverageTimeline.jsx` | 14-day continuous bar timeline with hover tooltips |
| `components/StoryDetail.jsx` | Full story analysis view — scores, contrasts, facts, bottom line |
| `components/ContrastCard.jsx` | Side-by-side framing comparison (left vs right source) |
| `components/FactCheck.jsx` | Claim verdict display with evidence |

### Backend (`backend/`)

**Pipeline**

| File | Purpose |
|------|---------|
| `pipeline/main.py` | CLI entry point — single run, daemon mode, dry-run |
| `pipeline/ingest.py` | Orchestrates fetch, normalize, deduplicate, embed, store |
| `pipeline/process.py` | Orchestrates clustering, scoring, analysis sequencing |
| `pipeline/select.py` | GPT-4o-mini editorial selection — picks stories for Claude analysis |

**Ingestion**

| File | Purpose |
|------|---------|
| `ingestion/rss.py` | Concurrent RSS fetcher with httpx + feedparser |
| `ingestion/googlenews.py` | Google News RSS decoder for protobuf URLs |
| `ingestion/newsdata.py` | NewsData.io API fetcher by category |
| `ingestion/scraper.py` | Article body extraction via trafilatura |
| `ingestion/dedup.py` | URL-based deduplication before storing |
| `ingestion/embed.py` | 384-dim embeddings via OpenAI or local sentence-transformers |
| `ingestion/normalize.py` | RawArticle to Article conversion with domain/bias lookup |

**Clustering**

| File | Purpose |
|------|---------|
| `clustering/assign.py` | Fast-path: assign unassigned articles to existing stories by embedding similarity |
| `clustering/discover.py` | HDBSCAN clustering to discover new story clusters from remaining articles |
| `clustering/split.py` | Split oversized stories into finer-grained sub-stories |
| `clustering/label.py` | Claude Haiku generates topic labels for unlabeled stories |
| `clustering/merge.py` | Merge stories that have become too similar after growth |
| `clustering/validate.py` | Filter non-current topics (historical, evergreen) via keyword + GPT-4o-mini |

**Analysis**

| File | Purpose |
|------|---------|
| `analysis/generator.py` | Claude Sonnet AP-style analysis with contrasts + fact checks |
| `analysis/staleness.py` | Determines which stories need new/updated analyses |
| `analysis/framing.py` | Per-article editorial framing classification via Claude Haiku (7 categories) |
| `analysis/headlines.py` | Rewrites vague cluster headlines into specific neutral ones |

**Scoring**

| File | Purpose |
|------|---------|
| `scoring/impact.py` | 0-100 real-world significance score via Claude Haiku (5 weighted factors) |
| `scoring/coverage.py` | 0-100 coverage score from article volume, source diversity, recency, velocity |
| `scoring/attention.py` | 0-100 media attention score — percentile-ranked article/source/bias breadth |
| `scoring/sentiment.py` | VADER sentiment analysis on headlines, grouped by left/center/right lean |
| `scoring/timeline.py` | Daily article-count trends, peak date, lifecycle status (breaking → stale) |
| `scoring/trends.py` | Trend computation from story_daily_counts table |
| `scoring/gaps.py` | Coverage gap detection — significance vs coverage comparison |
| `scoring/ranking.py` | Homepage rank score (0-100) from impact, coverage, velocity, recency, framing |
| `scoring/insights.py` | Category-level gap + surge detection for the frontend insights bar |

**Config & Data**

| File | Purpose |
|------|---------|
| `config/sources.py` | RSS feed registry (~40 feeds) + editorial bias ratings |
| `config/settings.py` | Pydantic settings from .env (keys, modes, thresholds) |
| `models/schemas.py` | Shared Pydantic models (RawArticle, Article, Story, Analysis) |
| `db/client.py` | Supabase client singleton |
| `db/queries.py` | DB query functions for articles, stories, analyses, vectors |

**Scripts**

| File | Purpose |
|------|---------|
| `scripts/backfill_analyses.py` | Generate Claude analyses for stories missing one |
| `scripts/scrape_backfill.py` | Backfill article bodies via trafilatura |
| `scripts/filter_topics.py` | GPT-4o-mini significance scoring, coherence check, topic renaming |
| `scripts/backfill_time_metadata.py` | Populate first_seen, last_article_at, status, velocity |
| `scripts/backfill_coverage.py` | Compute coverage_score from article count, diversity, recency |
| `scripts/backfill_daily_counts.py` | Populate story_daily_counts from article publish dates |
| `scripts/backfill_categories.py` | Categorize stories via keyword matching + Claude fallback |
| `scripts/migrate_headlines.py` | Fix truncated/vague headlines using Claude Haiku (dry run default) |
