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

# Full pipeline (ingest → cluster → score → scrape → analyze)
python -m pipeline.main

# Run individual stages
python -m pipeline.main ingest           # fetch + normalize + embed + store
python -m pipeline.main cluster          # assign articles → stories
python -m pipeline.main score            # impact + attention + gaps
python -m pipeline.main scrape           # extract article bodies
python -m pipeline.main analyze          # generate Claude analyses

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
| `pipeline/main.py` | CLI entry point — single run, continuous mode, dry-run |
| `pipeline/ingest.py` | Orchestrates fetch, normalize, deduplicate, embed, store |
| `pipeline/process.py` | Orchestrates clustering, scoring, analysis sequencing |
| `pipeline/poc_analysis.py` | PoC analysis for 10 hand-picked stories |
| `pipeline/cleanup.py` | One-time fix for stale scores and bad labels |

**Ingestion**

| File | Purpose |
|------|---------|
| `ingestion/rss.py` | Concurrent RSS fetcher with httpx + feedparser |
| `ingestion/googlenews.py` | Google News RSS decoder for protobuf URLs |
| `ingestion/newsdata.py` | NewsData.io API fetcher by category |
| `ingestion/scraper.py` | Article body extraction via trafilatura |
| `ingestion/embed.py` | 384-dim embeddings via OpenAI or local sentence-transformers |
| `ingestion/normalize.py` | RawArticle to Article conversion with domain/bias lookup |

**Analysis**

| File | Purpose |
|------|---------|
| `analysis/generator.py` | Claude Sonnet AP-style analysis with contrasts + fact checks |
| `analysis/staleness.py` | Determines which stories need new/updated analyses |
| `analysis/framing.py` | Per-article editorial framing classification via Claude Haiku |
| `analysis/headlines.py` | Rewrites vague cluster headlines into specific neutral ones |

**Scoring**

| File | Purpose |
|------|---------|
| `scoring/impact.py` | 0-100 real-world significance score (5 weighted factors) |
| `scoring/gaps.py` | Coverage gap detection — significance vs attention comparison |

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
| `scripts/backfill_analyses.py` | Generate analyses for all scored stories missing one |
| `scripts/scrape_backfill.py` | Backfill article bodies with rate limiting |
| `scripts/filter_topics.py` | GPT-4o-mini significance scoring and topic renaming |
| `scripts/backfill_time_metadata.py` | Backfill first_seen, last_article_at, status from timestamps |
| `scripts/migrate_headlines.py` | Fix truncated/vague/long headlines using Claude Haiku (dry run by default) |
