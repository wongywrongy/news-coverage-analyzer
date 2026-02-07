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
        ALTER TABLE analyses
            ALTER COLUMN contrasts TYPE JSONB USING COALESCE(contrasts::jsonb, '[]'::jsonb);
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analyses' AND column_name = 'facts' AND data_type = 'text'
    ) THEN
        ALTER TABLE analyses
            ALTER COLUMN facts TYPE JSONB USING COALESCE(facts::jsonb, '[]'::jsonb);
    END IF;
END $$;
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
