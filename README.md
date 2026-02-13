# ClearSignal

Multi-perspective news analysis platform. Tracks 100+ sources across the political spectrum, clusters articles into stories, scores coverage gaps, and generates neutral AP-style analyses.

```
    RSS Feeds          NewsData.io         Google News
        |                  |                   |
        v                  v                   v
   +-------------------------------------------------+
   |              INGESTION PIPELINE                  |
   |  fetch -> normalize -> dedup -> embed -> store   |
   +-------------------------------------------------+
                         |
                         v
   +-------------------------------------------------+
   |            CLUSTERING PIPELINE                   |
   |  assign -> discover -> split -> label ->         |
   |  rename -> entities -> graph -> merge ->         |
   |  validate                                        |
   +-------------------------------------------------+
                         |
                         v
   +-------------------------------------------------+
   |              SCORING PIPELINE                    |
   |  impact -> coverage -> attention -> sentiment -> |
   |  timeline -> gaps -> ranking -> heat -> insights |
   +-------------------------------------------------+
                         |
                         v
   +-------------------------------------------------+
   |             ANALYSIS PIPELINE                    |
   |  select -> scrape -> frame -> analyze            |
   +-------------------------------------------------+
                         |
                         v
              Supabase (PostgreSQL + pgvector)
                         |
                         v
                Next.js Frontend
```

## Quick Start

```bash
# 1. Clone and set up backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in API keys

# 2. Run database migrations
python -m db.migrations

# 3. Run the full pipeline
python -m pipeline.main

# 4. Start the frontend
cd ../frontend
npm install
npm run dev   # http://localhost:3000

# 5. (Optional) Health check
cd ../backend
python -m scripts.health_check
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | -- | Supabase project URL |
| `SUPABASE_KEY` | Yes | -- | Supabase service role key |
| `OPENAI_API_KEY` | Yes | -- | OpenAI API key (embeddings, selection, validation) |
| `ANTHROPIC_API_KEY` | Yes | -- | Anthropic API key (labeling, scoring, analysis) |
| `NEWSDATA_API_KEY` | No | `""` | NewsData.io API key (optional extra source) |
| `EMBEDDING_MODE` | No | `openai` | `openai` or `local` (sentence-transformers) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for validation and selection |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Model for full analysis generation |
| `HAIKU_MODEL` | No | `claude-haiku-4-5-20251001` | Model for labeling, framing, scoring |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | OpenAI embedding model |
| `ANALYSIS_BATCH_SIZE` | No | `10` | Max stories analyzed per cycle |
| `MAX_STORIES_PER_ANALYSIS_CYCLE` | No | `8` | Max stories selected for analysis |
| `SELECTION_ENABLED` | No | `true` | Use AI editorial selection |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |

## Commands

### Pipeline

All commands run from the `backend/` directory.

```bash
# Full pipeline (ingest -> cluster -> score -> select -> scrape -> analyze)
python -m pipeline.main

# Individual stages
python -m pipeline.main ingest       # Fetch, normalize, deduplicate, embed, store
python -m pipeline.main cluster      # Assign, discover, split, label, rename, merge, validate
python -m pipeline.main validate     # Filter non-current topics (standalone)
python -m pipeline.main entities     # Extract named entities from topics
python -m pipeline.main graph        # Update entity graph (edges, strengths, importance)
python -m pipeline.main score        # Impact, coverage, attention, sentiment, gaps, heat, insights
python -m pipeline.main heat         # Recompute heat scores (no AI, formula only)
python -m pipeline.main select       # GPT-4o-mini editorial triage
python -m pipeline.main scrape       # Extract article bodies via trafilatura
python -m pipeline.main analyze      # Generate Claude-powered AP-style analyses

# Daemon mode (recurring full pipeline)
python -m pipeline.main --daemon                # Default: every 15 minutes
python -m pipeline.main --daemon --interval 30  # Custom interval

# Dry run (no database writes)
python -m pipeline.main --dry-run
python -m pipeline.main ingest --dry-run
```

### Scripts

```bash
# Database
python -m db.migrations                              # Run all migrations (idempotent)

# Health check
python -m scripts.health_check                       # Quick health check
python -m scripts.health_check --verbose             # Detailed output

# Codebase audit
python -m scripts.audit                              # Scan for code quality issues

# Re-analysis
python -m scripts.reanalyze_all                      # Dry run (preview)
python -m scripts.reanalyze_all --execute            # Full re-analysis
python -m scripts.reanalyze_all --execute --limit 3  # Small batch test
python -m scripts.reanalyze_all --execute --resume   # Resume if interrupted

# Backfills
python -m scripts.backfill_analyses --limit 10       # Generate missing analyses
python -m scripts.backfill_analyses --min-impact 50  # Only high-impact stories
python -m scripts.scrape_backfill --limit 100        # Scrape missing article bodies
python -m scripts.backfill_categories                # Categorize uncategorized stories
python -m scripts.backfill_time_metadata             # Populate time fields
python -m scripts.backfill_daily_counts              # Populate daily article counts
python -m scripts.backfill_coverage                  # Compute coverage scores

# Topic management
python -m scripts.filter_topics --dry-run            # Preview topic filtering
python -m scripts.migrate_headlines                   # Preview headline fixes
python -m scripts.migrate_headlines --apply --limit 10
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Dev server at localhost:3000
npm run build        # Production build
npm run lint         # ESLint check
```

## Pipeline Stages

| Stage | What It Does | AI Model | Cost per Cycle |
|-------|-------------|----------|----------------|
| **Ingest** | Fetch ~40 RSS feeds, normalize URLs, deduplicate, embed | OpenAI embeddings | ~$0.01 |
| **Cluster** | Group articles by semantic similarity (HDBSCAN), label topics | Claude Haiku | ~$0.02 |
| **Entities** | Extract named entities (people, orgs, cases, legislation) | GPT-4o-mini | ~$0.003 |
| **Graph** | Build entity relationship edges, compute PageRank importance | None | Free |
| **Validate** | Filter non-current topics, US relevance check | GPT-4o-mini | ~$0.001 |
| **Score** | Rate impact (5-factor model), coverage, attention, sentiment, heat | Claude Haiku | ~$0.03 |
| **Heat** | Front-page prominence: impact + source breadth + velocity + divergence | None (formula) | Free |
| **Select** | Editorial triage -- pick stories for expensive analysis | GPT-4o-mini | ~$0.002 |
| **Scrape** | Extract article body text from URLs via trafilatura | None | Free |
| **Frame** | Classify editorial framing per article (7 categories) | Claude Haiku | ~$0.05 |
| **Analyze** | Generate full structured analysis with contrasts and fact checks | Claude Sonnet | ~$0.50-1.50 |

**Typical full cycle: ~$0.20-0.90** depending on how many stories are analyzed.

## Database

PostgreSQL with pgvector on Supabase.

| Table | Purpose |
|-------|---------|
| `articles` | Raw and enriched articles with 384-dim embeddings (`story_id` FK to stories) |
| `stories` | Topic clusters with scores, metadata, heat |
| `analyses` | Claude-generated structured analyses per story |
| `story_daily_counts` | Daily article counts per story (for trends) |
| `entities` | Named entities (people, organizations, cases) |
| `topic_entities` | Many-to-many join (story <-> entity) |
| `entity_relationships` | Entity co-occurrence edges with strength |
| `insights_cache` | Cached global insights for the dashboard |

Run `python -m db.migrations` to create all tables. Migrations are idempotent.

## Project Structure

```
clearsignal/
+-- README.md
+-- pyproject.toml
+-- .gitignore
|
+-- backend/
|   +-- .env.example
|   +-- requirements.txt
|   +-- constants.py           # Business logic constants
|   |
|   +-- config/
|   |   +-- settings.py        # Pydantic settings from .env
|   |   +-- sources.py         # RSS feeds + editorial bias registry
|   |
|   +-- db/
|   |   +-- client.py          # Supabase client singleton
|   |   +-- queries.py         # All database operations
|   |   +-- migrations.py      # Schema migrations (idempotent)
|   |
|   +-- models/
|   |   +-- schemas.py         # Pydantic models (RawArticle, Article, Story, Analysis)
|   |
|   +-- pipeline/
|   |   +-- main.py            # CLI entry point (single/daemon/dry-run)
|   |   +-- ingest.py          # Fetch -> normalize -> dedup -> embed -> store
|   |   +-- process.py         # Clustering, scoring, analysis orchestration
|   |   +-- select.py          # GPT-4o-mini editorial selection
|   |   +-- extract_entities.py
|   |   +-- update_graph.py
|   |
|   +-- ingestion/
|   |   +-- rss.py             # Concurrent RSS fetcher (httpx + feedparser)
|   |   +-- googlenews.py      # Google News RSS decoder
|   |   +-- newsdata.py        # NewsData.io API
|   |   +-- normalize.py       # URL normalization, bias lookup
|   |   +-- dedup.py           # Deduplication (URL + title similarity)
|   |   +-- embed.py           # 384-dim embeddings (OpenAI or local)
|   |   +-- scraper.py         # Article body extraction (trafilatura)
|   |
|   +-- clustering/
|   |   +-- assign.py          # Fast-path article assignment
|   |   +-- discover.py        # HDBSCAN new cluster discovery
|   |   +-- split.py           # Split oversized clusters
|   |   +-- label.py           # Claude Haiku topic labeling
|   |   +-- merge.py           # Merge converged stories
|   |   +-- validate.py        # Currency + US relevance filtering
|   |
|   +-- analysis/
|   |   +-- generator.py       # Claude Sonnet structured analysis
|   |   +-- framing.py         # Per-article framing classification
|   |   +-- headlines.py       # Vague headline rewriting
|   |   +-- staleness.py       # Analysis freshness detection
|   |
|   +-- scoring/
|   |   +-- impact.py          # 0-100 significance (Claude Haiku)
|   |   +-- coverage.py        # 0-100 coverage breadth
|   |   +-- attention.py       # 0-100 media attention
|   |   +-- sentiment.py       # VADER sentiment by political lean
|   |   +-- heat.py            # Front-page heat (formula, no AI)
|   |   +-- timeline.py        # Daily trends + lifecycle status
|   |   +-- gaps.py            # Coverage gap detection
|   |   +-- ranking.py         # Homepage sort order
|   |   +-- insights.py        # Category-level insights for dashboard
|   |
|   +-- utils/
|   |   +-- exceptions.py      # Custom exception hierarchy
|   |
|   +-- scripts/
|   |   +-- audit.py           # Codebase quality audit
|   |   +-- health_check.py    # Supabase health check
|   |   +-- reanalyze_all.py
|   |   +-- backfill_*.py      # Various backfill scripts
|   |
|   +-- tests/
|       +-- test_analysis.py
|       +-- test_clustering.py
|
+-- frontend/
|   +-- package.json
|   +-- next.config.js
|   +-- src/
|       +-- app/               # Next.js App Router pages
|       |   +-- page.js        # Landing page
|       |   +-- news/page.js   # Daily briefing
|       |   +-- topic/[id]/    # Topic detail
|       |   +-- archive/       # Archive
|       |   +-- methodology/   # How it works
|       +-- components/        # 30+ React components
|       +-- lib/               # Supabase client, queries, constants
|
+-- docs/
    +-- prototypes/            # Early HTML/JSX mockups
```

## Tech Stack

**Frontend:** Next.js 14, React 18, Supabase JS client, inline styles
**Backend:** Python 3.12, async pipeline, Pydantic v2, Rich CLI
**AI:** Anthropic Claude (Sonnet for analysis, Haiku for scoring/labeling), OpenAI (embeddings, GPT-4o-mini for selection)
**Database:** Supabase (PostgreSQL + pgvector for vector similarity)
**Fonts:** Playfair Display, DM Sans, JetBrains Mono

## Troubleshooting

**"Missing required env var" on startup**
Copy `.env.example` to `.env` and fill in all required API keys.

**"No articles fetched" during ingest**
Some RSS feeds may be temporarily down. Check feed health: `python -m config.sources`

**Embeddings failing**
If using `EMBEDDING_MODE=openai`, verify your OpenAI key has API access. For local mode, install `sentence-transformers`.

**"No active stories" in scoring**
Run the full pipeline at least once: `python -m pipeline.main`. Stories need to be ingested and clustered before scoring.

**Frontend shows no data**
Verify `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `frontend/.env.local`. Run `python -m scripts.health_check` to verify database health.

**Heat scores are all 0**
Run `python -m pipeline.main heat` to recompute heat scores.
