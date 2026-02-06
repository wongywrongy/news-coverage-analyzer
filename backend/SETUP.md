# ClearSignal Backend — Setup & Testing Guide

## Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project (free tier works)
- An [OpenAI](https://platform.openai.com) API key (for embeddings) **OR** enough RAM for local sentence-transformers (~500 MB)
- Optional: [NewsData.io](https://newsdata.io) API key (free tier = 200 credits/day)

---

## Step 1: Clone and Create Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

If you only want OpenAI embeddings (faster, cheaper) and don't need local mode:
```bash
pip install httpx feedparser supabase openai anthropic pydantic pydantic-settings python-dotenv apscheduler rich python-dateutil numpy
```

If you want local embeddings (free, no API key needed):
```bash
pip install sentence-transformers
```

---

## Step 2: Configure Environment Variables

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` with your real keys:

```ini
# REQUIRED — get these from your Supabase project dashboard
# Settings → API → Project URL
SUPABASE_URL=https://your-project-id.supabase.co
# Settings → API → service_role key (NOT the anon key — pipeline needs write access)
SUPABASE_KEY=eyJhbGciOi...your-service-role-key

# REQUIRED for OpenAI embeddings (skip if using EMBEDDING_MODE=local)
OPENAI_API_KEY=sk-your-openai-api-key

# REQUIRED later for AI analysis (not used by ingestion yet)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# OPTIONAL — leave empty to skip NewsData source
NEWSDATA_API_KEY=your-newsdata-api-key

# Choose embedding strategy
# "openai" = OpenAI text-embedding-3-small (fast, ~$0.02/1M tokens)
# "local"  = sentence-transformers all-MiniLM-L6-v2 (free, slower first run)
EMBEDDING_MODE=openai

LOG_LEVEL=INFO
```

**Verify it loads:**
```bash
python -m config.settings
```
Expected output:
```
ClearSignal Settings
  supabase_url   = https://your-project-id...
  embedding_mode = openai
  log_level      = INFO
```

---

## Step 3: Set Up the Database (Supabase)

The migration runner requires an `exec_sql` RPC function that Supabase doesn't have by default. **Use the SQL Editor approach instead.**

### Option A: Copy-paste SQL (recommended)

1. Generate the full schema SQL:
   ```bash
   python -m db.migrations --print-sql
   ```

2. Open your Supabase dashboard → **SQL Editor**

3. Paste the entire output and click **Run**

4. Verify tables were created: go to **Table Editor** — you should see `articles`, `stories`, and `analyses`

### Option B: Create the exec_sql RPC first (advanced)

If you want the Python migration runner to work directly, first run this in the SQL Editor:

```sql
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    EXECUTE query;
END;
$$;
```

Then run from Python:
```bash
python -m db.migrations
```

**Warning:** The `exec_sql` function allows arbitrary SQL execution. Only the service_role key can call it (RLS protects it from anon), but consider dropping it after migrations are done:
```sql
DROP FUNCTION IF EXISTS exec_sql(text);
```

### Verify Database Connection

```bash
python -m db.client
```
Expected output:
```
Connected → https://your-project-id.supabase.co
  articles row count: 0
```

---

## Step 4: Test Individual Modules

Run each module's built-in smoke test from the `backend/` directory. Test them in dependency order:

### 4a. Config & Sources

```bash
# Verify settings load from .env
python -m config.settings

# View all RSS feeds and their bias ratings
python -m config.sources
```

### 4b. Pydantic Models

```bash
python -m models.schemas
```
Shows round-trip serialization for RawArticle, Story, and IngestionResult.

### 4c. Database Queries (smoke test)

```bash
python -m db.queries
```
Runs read-only queries against your Supabase DB. Expected on a fresh DB:
```
existing urls check: set()
active stories: 0
unassigned articles: 0
stale analyses (>24h): 0
All queries executed successfully.
```

### 4d. RSS Fetcher

```bash
python -m ingestion.rss
```
Fetches from all ~40 RSS feeds. Takes 10-30 seconds. Some feeds may fail (404, timeout) — that's normal. Expected:
```
Total articles fetched: 200-600
  [nytimes.com] Senate Passes Major...  (2026-02-06 14:30)
  ...
```

### 4e. NewsData.io Fetcher (requires API key)

```bash
python -m ingestion.newsdata
```
Uses 5 credits from your daily 200 budget. Expected:
```
Total articles fetched: 30-50
```

If you don't have a NewsData key, this prints "NewsData API key not configured — skipping" and returns 0 articles. That's fine — RSS alone is sufficient.

### 4f. Google News Fetcher

```bash
python -m ingestion.googlenews
```
Fetches from Google News RSS (no API key needed). Expected:
```
Total articles fetched: 100-200
```

### 4g. Normalizer

```bash
python -m ingestion.normalize
```
Runs against hardcoded fixtures. Shows bias lookup, HTML cleaning, date parsing. Expected:
```
Normalized: 3 / 5 articles
  [nytimes.com] Senate Passes Major Climate Bill
    bias=left-center (+0.3)
    ...
```

### 4h. Deduplicator

```bash
python -m ingestion.dedup
```
Runs against fixtures showing URL dedup and Jaccard title dedup. Expected:
```
Input: 6 articles
Output: 3 unique articles
```

### 4i. Embedder

```bash
python -m ingestion.embed
```
Embeds 3 fixture articles. If using OpenAI mode, costs ~$0.001. Expected:
```
Using mode: openai
Embedded 3 articles
  [nytimes.com] Senate Passes Major Climate Bill
    dims=384  first_5=[0.0123, -0.0456, ...]
```

---

## Step 5: Run the Full Pipeline

### Single run (recommended for first test)

```bash
python -m pipeline.ingest --dry-run
```

This fetches, normalizes, deduplicates, and embeds — but **does not write to the database**. Use this to verify the full flow without side effects.

Expected output:
```
Ingestion Summary
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━┓
┃ Source              ┃ Bias          ┃ Fetched ┃ New ┃ Errors┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━┩
│ nytimes.com         │ left-center   │      20 │  20 │     0 │
│ foxnews.com         │ right-center  │      15 │  15 │     0 │
│ ...                 │ ...           │     ... │ ... │   ... │
└─────────────────────┴───────────────┴─────────┴─────┴───────┘

Totals: 450 fetched → 380 deduped → 375 embedded → 380 stored (18.3s)
```

### Single run with DB writes

```bash
python -m pipeline.ingest
```

After this, verify data in Supabase:
```bash
python -m db.queries
```
You should now see `unassigned articles: 300+`.

### Full pipeline via main entry point

```bash
# Single run then exit
python -m pipeline.main --once

# Daemon mode: runs every 15 minutes
python -m pipeline.main

# Custom interval (e.g., every 30 minutes)
python -m pipeline.main --interval 30
```

Press `Ctrl+C` to stop the daemon gracefully.

---

## Step 6: Verify Data in Supabase

Open your Supabase dashboard → **Table Editor**:

1. **articles** table: should have rows with `url`, `title`, `source_domain`, `source_bias`, `embedding` (non-null for most), `story_id` (all NULL — clustering isn't implemented yet)

2. **stories** table: empty (clustering stage not built yet)

3. **analyses** table: empty (analysis stage not built yet)

You can also query via the SQL Editor:
```sql
-- Count articles per source
SELECT source_domain, COUNT(*) as cnt
FROM articles
GROUP BY source_domain
ORDER BY cnt DESC;

-- Check embedding coverage
SELECT
  COUNT(*) as total,
  COUNT(embedding) as with_embedding,
  COUNT(*) - COUNT(embedding) as missing_embedding
FROM articles;

-- View latest articles
SELECT title, source_domain, source_bias, published_at
FROM articles
ORDER BY published_at DESC
LIMIT 20;
```

---

## Troubleshooting

### "Settings validation error" on startup
Your `.env` is missing required keys. Check that `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are all set. If you don't have an Anthropic key yet, set it to a placeholder: `ANTHROPIC_API_KEY=placeholder`.

### "exec_sql" RPC error during migrations
Use `python -m db.migrations --print-sql` and paste the SQL into Supabase SQL Editor manually. See Step 3.

### RSS feeds returning 0 articles
Some feeds block non-browser User-Agents or require specific headers. The pipeline logs warnings per feed — check for HTTP 403/429 errors. This is normal; the pipeline continues with whatever feeds succeed.

### "OpenAI 429 — retrying" messages
You're hitting OpenAI rate limits. The embedder retries with exponential backoff (1s, 2s, 4s). If it exhausts retries, articles are stored without embeddings. Consider switching to `EMBEDDING_MODE=local` for development.

### Embedding dimension errors from pgvector
If you created the tables with the old `vector(1536)` dimension before applying the fix, drop and recreate:
```sql
DROP TABLE IF EXISTS analyses;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS stories;
```
Then re-run the migration SQL (Step 3).

### NewsData "429 rate-limited" messages
Free tier = 200 credits/day. Each pipeline run uses 6 credits (one per category). At 15-minute intervals that's 576/day, which exhausts by afternoon. Options:
- Run the daemon at 30+ minute intervals (`--interval 30`)
- Leave `NEWSDATA_API_KEY` empty (RSS + Google News provide plenty of data)

### Import warnings like "embed_articles not available"
This means a module failed to import. Usually a missing dependency. Run `pip install -r requirements.txt` to ensure everything is installed.

---

## Architecture Notes

```
pipeline/main.py          CLI + daemon scheduler
    └── pipeline/ingest.py    orchestrator (no business logic)
            ├── ingestion/rss.py          RSS fetcher (async, 40 feeds)
            ├── ingestion/newsdata.py     NewsData.io fetcher
            ├── ingestion/googlenews.py   Google News fetcher
            ├── ingestion/normalize.py    RawArticle → Article enrichment
            ├── ingestion/dedup.py        URL + title deduplication
            ├── ingestion/embed.py        OpenAI or local embeddings
            └── db/queries.py             all database operations
                    └── db/client.py      Supabase client singleton

config/settings.py        .env loader (pydantic-settings)
config/sources.py         RSS feed URLs + bias registry
models/schemas.py         shared Pydantic models
db/migrations.py          schema DDL + RPC definitions
```

Data flow: `fetch → normalize → deduplicate → embed → store`

Each stage is independently testable via `python -m <module>`.
