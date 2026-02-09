"""
Idempotent database migrations for ClearSignal.

Creates all tables, enables pgvector, and builds indexes.
Safe to run repeatedly — every statement uses IF NOT EXISTS.

Usage:
    python -m db.migrations
"""

import logging

from db.client import get_client

logger = logging.getLogger(__name__)

# ── SQL Statements ────────────────────────────────────────────────────────────

ENABLE_PGVECTOR = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

CREATE_ARTICLES = """
CREATE TABLE IF NOT EXISTS articles (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    body            TEXT DEFAULT '',
    source_name     TEXT NOT NULL,
    source_domain   TEXT DEFAULT '',
    source_bias     TEXT DEFAULT '',
    source_bias_score FLOAT DEFAULT 0.0,
    author          TEXT DEFAULT '',
    published_at    TIMESTAMPTZ,
    image_url       TEXT DEFAULT '',
    raw_source      JSONB DEFAULT '{}'::jsonb,
    embedding       vector(384),
    sentiment       FLOAT DEFAULT 0.0,
    story_id        BIGINT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
"""

CREATE_STORIES = """
CREATE TABLE IF NOT EXISTS stories (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    topic           TEXT DEFAULT '',
    category        TEXT DEFAULT '',
    impact_score    FLOAT DEFAULT 0.0,
    attention_score FLOAT DEFAULT 0.0,
    article_count   INT DEFAULT 0,
    source_count    INT DEFAULT 0,
    avg_bias_score  FLOAT DEFAULT 0.0,
    bias_spread     FLOAT DEFAULT 0.0,
    centroid        vector(384),
    active          BOOLEAN DEFAULT TRUE,
    first_seen      TIMESTAMPTZ DEFAULT now(),
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);
"""

CREATE_ANALYSES = """
CREATE TABLE IF NOT EXISTS analyses (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    story_id             BIGINT NOT NULL UNIQUE REFERENCES stories(id) ON DELETE CASCADE,
    headline             TEXT DEFAULT '',
    dateline             VARCHAR(128) DEFAULT '',
    lede                 TEXT DEFAULT '',
    context              TEXT DEFAULT '',
    contrasts            JSONB DEFAULT '[]'::jsonb,
    facts                JSONB DEFAULT '[]'::jsonb,
    bottom_line          TEXT DEFAULT '',
    coverage_note        TEXT DEFAULT '',
    generated_at         TIMESTAMPTZ DEFAULT now(),
    article_count_at_gen INT DEFAULT 0,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);
"""

# ── Indexes ───────────────────────────────────────────────────────────────────

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_articles_url          ON articles (url);
CREATE INDEX IF NOT EXISTS idx_articles_story_id     ON articles (story_id);
CREATE INDEX IF NOT EXISTS idx_articles_source       ON articles (source_domain);
CREATE INDEX IF NOT EXISTS idx_articles_published    ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_unassigned   ON articles (published_at DESC) WHERE story_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_stories_active        ON stories (active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_stories_impact        ON stories (impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_story_id     ON analyses (story_id);
"""

# Vector similarity indexes (IVFFlat — good for datasets up to ~1M rows)
CREATE_VECTOR_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_articles_embedding
    ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_stories_centroid
    ON stories USING ivfflat (centroid vector_cosine_ops) WITH (lists = 50);
"""

# RPC for vector similarity matching against story centroids
CREATE_MATCH_RPC = """
CREATE OR REPLACE FUNCTION match_story_centroid(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.82,
    match_count int DEFAULT 1
)
RETURNS TABLE(id bigint, similarity float)
LANGUAGE sql STABLE
AS $$
    SELECT
        s.id,
        1 - (s.centroid <=> query_embedding) AS similarity
    FROM stories s
    WHERE s.active = TRUE
      AND s.centroid IS NOT NULL
      AND 1 - (s.centroid <=> query_embedding) >= match_threshold
    ORDER BY s.centroid <=> query_embedding
    LIMIT match_count;
$$;
"""

# Foreign key from articles → stories (added separately so table order doesn't matter)
ADD_FK_ARTICLES_STORY = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_articles_story'
    ) THEN
        ALTER TABLE articles
            ADD CONSTRAINT fk_articles_story
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE SET NULL;
    END IF;
END $$;
"""

# ── Analyses table schema upgrade (idempotent) ───────────────────────────────

UPGRADE_ANALYSES = """
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS article_count_at_gen INT DEFAULT 0;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ DEFAULT now();

DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analyses' AND column_name = 'contrasts' AND data_type = 'text'
    ) THEN
        ALTER TABLE analyses ALTER COLUMN contrasts DROP DEFAULT;
        ALTER TABLE analyses
            ALTER COLUMN contrasts TYPE JSONB USING COALESCE(contrasts::jsonb, '[]'::jsonb);
        ALTER TABLE analyses ALTER COLUMN contrasts SET DEFAULT '[]'::jsonb;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analyses' AND column_name = 'facts' AND data_type = 'text'
    ) THEN
        ALTER TABLE analyses ALTER COLUMN facts DROP DEFAULT;
        ALTER TABLE analyses
            ALTER COLUMN facts TYPE JSONB USING COALESCE(facts::jsonb, '[]'::jsonb);
        ALTER TABLE analyses ALTER COLUMN facts SET DEFAULT '[]'::jsonb;
    END IF;
END $$;
"""

# ── Stories + Analyses schema upgrades (5-factor scoring + guardrails) ────────

UPGRADE_STORIES_SCORING = """
-- 5-factor significance scoring columns
ALTER TABLE stories ADD COLUMN IF NOT EXISTS significance_score INT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS significance_factors JSONB;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS confidence TEXT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS caveats TEXT[];
ALTER TABLE stories ADD COLUMN IF NOT EXISTS population_affected TEXT DEFAULT '';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS impact_scored_at TIMESTAMPTZ;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS scored_at_article_count INT DEFAULT 0;

-- Story metadata columns (may already exist)
ALTER TABLE stories ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'developing';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS peak_date TEXT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS trend JSONB DEFAULT '[]'::jsonb;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS sentiment_left FLOAT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS sentiment_center FLOAT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS sentiment_right FLOAT;
"""

UPGRADE_STORIES_TIME_METADATA = """
-- Time metadata for story lifecycle tracking
ALTER TABLE stories ADD COLUMN IF NOT EXISTS last_article_at TIMESTAMPTZ;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS coverage_velocity FLOAT;
"""

UPGRADE_ANALYSES_GUARDRAILS = """
-- Analysis guardrail columns
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS framing_check TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS source_framings JSONB DEFAULT '[]'::jsonb;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS spectrum TEXT DEFAULT '';
"""

# ── Daily article counts per story ───────────────────────────────────────────

CREATE_STORY_DAILY_COUNTS = """
CREATE TABLE IF NOT EXISTS story_daily_counts (
    story_id      BIGINT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    date          DATE NOT NULL,
    article_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (story_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_counts_story ON story_daily_counts (story_id);
"""

ADD_COVERAGE_SCORE = """
ALTER TABLE stories ADD COLUMN IF NOT EXISTS coverage_score FLOAT DEFAULT 0.0;
"""

ADD_CATEGORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_stories_category ON stories (category) WHERE active = TRUE;
"""

ADD_RANK_SCORE = """
ALTER TABLE stories ADD COLUMN IF NOT EXISTS rank_score FLOAT DEFAULT 0.0;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS featured_reason TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_stories_rank ON stories (rank_score DESC) WHERE active = TRUE;
"""

ADD_SELECTION_COLUMNS = """
ALTER TABLE stories ADD COLUMN IF NOT EXISTS selected_for_analysis BOOLEAN DEFAULT FALSE;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS selection_reason TEXT DEFAULT '';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS selection_priority INT;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS last_selected_at TIMESTAMPTZ;
"""

CREATE_INSIGHTS_CACHE = """
CREATE TABLE IF NOT EXISTS insights_cache (
    id              INT PRIMARY KEY DEFAULT 1,
    insights        JSONB DEFAULT '[]'::jsonb,
    computed_at     TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT insights_cache_singleton CHECK (id = 1)
);
INSERT INTO insights_cache (id, insights) VALUES (1, '[]'::jsonb)
ON CONFLICT (id) DO NOTHING;
"""

CREATE_UPSERT_DAILY_COUNT_RPC = """
CREATE OR REPLACE FUNCTION upsert_daily_count(
    p_story_id bigint,
    p_date date,
    p_delta int DEFAULT 1
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO story_daily_counts (story_id, date, article_count)
    VALUES (p_story_id, p_date, GREATEST(p_delta, 0))
    ON CONFLICT (story_id, date)
    DO UPDATE SET article_count = GREATEST(story_daily_counts.article_count + p_delta, 0);
END;
$$;
"""

# ── Migration runner ──────────────────────────────────────────────────────────

MIGRATION_STEPS: list[tuple[str, str]] = [
    ("Enable pgvector extension",       ENABLE_PGVECTOR),
    ("Create articles table",           CREATE_ARTICLES),
    ("Create stories table",            CREATE_STORIES),
    ("Create analyses table",           CREATE_ANALYSES),
    ("Create standard indexes",         CREATE_INDEXES),
    ("Create vector similarity indexes", CREATE_VECTOR_INDEXES),
    ("Create match_story_centroid RPC", CREATE_MATCH_RPC),
    ("Add articles → stories FK",       ADD_FK_ARTICLES_STORY),
    ("Upgrade analyses table schema",   UPGRADE_ANALYSES),
    ("Upgrade stories for 5-factor scoring", UPGRADE_STORIES_SCORING),
    ("Upgrade analyses for guardrails", UPGRADE_ANALYSES_GUARDRAILS),
    ("Upgrade stories for time metadata", UPGRADE_STORIES_TIME_METADATA),
    ("Create story_daily_counts table", CREATE_STORY_DAILY_COUNTS),
    ("Create upsert_daily_count RPC",   CREATE_UPSERT_DAILY_COUNT_RPC),
    ("Add coverage_score to stories",   ADD_COVERAGE_SCORE),
    ("Add category index on stories",   ADD_CATEGORY_INDEX),
    ("Add rank_score to stories",        ADD_RANK_SCORE),
    ("Create insights cache table",      CREATE_INSIGHTS_CACHE),
    ("Add selection columns to stories", ADD_SELECTION_COLUMNS),
]


def get_full_schema_sql() -> str:
    """Return all migration SQL concatenated, for manual execution."""
    return "\n".join(sql for _, sql in MIGRATION_STEPS)


def run_migrations() -> None:
    """Execute all migration steps in order. Idempotent.

    Uses Supabase's postgrest-py HTTP interface.  If the ``exec_sql``
    RPC is not available, prints the full SQL for manual execution in
    the Supabase SQL Editor.
    """
    client = get_client()
    logger.info("Running %d migration steps …", len(MIGRATION_STEPS))

    for label, sql in MIGRATION_STEPS:
        try:
            client.rpc("exec_sql", {"query": sql}).execute()
            logger.info("  ✓ %s", label)
        except Exception as exc:
            logger.error("  ✗ %s — %s", label, exc)
            logger.error(
                "The 'exec_sql' RPC may not exist in your Supabase project.\n"
                "Run the SQL manually in the Supabase SQL Editor instead.\n"
                "Use:  python -m db.migrations --print-sql"
            )
            raise

    logger.info("All migrations complete.")


if __name__ == "__main__":
    import sys

    from rich.console import Console

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    console = Console()

    if "--print-sql" in sys.argv:
        console.print("[bold]Full ClearSignal schema SQL[/bold]\n")
        console.print("Copy-paste this into the Supabase SQL Editor:\n")
        print(get_full_schema_sql())
        sys.exit(0)

    console.print("[bold]ClearSignal DB Migrations[/bold]\n")
    try:
        run_migrations()
        console.print("\n[bold green]All migrations applied successfully.[/bold green]")
    except Exception as exc:
        console.print(f"\n[bold red]Migration failed:[/bold red] {exc}")
        console.print(
            "\n[yellow]Tip:[/yellow] Run with [bold]--print-sql[/bold] to get the "
            "full SQL for manual execution in the Supabase SQL Editor."
        )
        sys.exit(1)
