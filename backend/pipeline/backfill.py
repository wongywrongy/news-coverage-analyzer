"""Backfill missing embeddings for articles in the database.

Idempotent — only processes articles WHERE embedding IS NULL, so it is
safe to run multiple times.  Useful whenever articles were stored without
embeddings (e.g., OpenAI key wasn't configured, or the API was
temporarily unreachable during ingestion).

Usage:
    python -m pipeline.backfill              # backfill all
    python -m pipeline.backfill --limit 100  # first 100 only
    python -m pipeline.backfill --dry-run    # count without embedding
    python -m pipeline.backfill --batch-size 25 --limit 200
"""

from __future__ import annotations

import argparse
import logging
import time

from config.settings import settings
from db.queries import get_articles_without_embeddings, update_article_embedding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Text preparation (mirrors ingestion/embed.py:_prepare_text)
# ---------------------------------------------------------------------------

def _prepare_text(row: dict) -> str:
    """Build the embedding input from a DB row's title + description."""
    title = (row.get("title") or "").strip()
    desc = (row.get("description") or "").strip()[:200]
    if desc:
        return f"{title}. {desc}"
    return title


# ---------------------------------------------------------------------------
# Embedding backend (reuses the same logic as ingestion/embed.py)
# ---------------------------------------------------------------------------

def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured backend.

    Returns a list of vectors positionally matching *texts*.
    Failed items get an empty list.
    """
    mode = settings.embedding_mode

    if mode == "openai":
        from ingestion.embed import _embed_openai
        return _embed_openai(texts)

    if mode == "local":
        from ingestion.embed import _embed_local
        return _embed_local(texts)

    logger.error("Unknown embedding_mode %r", mode)
    return [[] for _ in texts]


# ---------------------------------------------------------------------------
# Core backfill
# ---------------------------------------------------------------------------

def backfill_embeddings(
    batch_size: int = 50,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    """Fetch articles without embeddings, generate them, and update the DB.

    Processes in batches to manage memory and respect API rate limits.
    Partial failures within a batch are skipped — remaining articles
    still get processed.

    Args:
        batch_size: Number of articles per embedding API call.
        limit: Maximum total articles to process (``None`` = all).
        dry_run: If True, only count articles and return without
            generating any embeddings.

    Returns:
        Total number of articles successfully updated.
    """
    rows = get_articles_without_embeddings(limit=limit)
    total = len(rows)

    if total == 0:
        logger.info("No articles need embedding backfill.")
        return 0

    if dry_run:
        logger.info("Dry run: %d articles need embeddings (no work done).", total)
        return 0

    num_batches = (total + batch_size - 1) // batch_size
    logger.info(
        "Backfilling embeddings for %d articles in %d batches (batch_size=%d, mode=%s)",
        total, num_batches, batch_size, settings.embedding_mode,
    )

    updated = 0
    skipped = 0
    overall_start = time.monotonic()

    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_rows = rows[batch_start : batch_start + batch_size]

        texts = [_prepare_text(row) for row in batch_rows]
        t0 = time.monotonic()
        embeddings = _embed_batch(texts)
        elapsed = time.monotonic() - t0

        batch_ok = 0
        for row, emb in zip(batch_rows, embeddings):
            if not emb:
                logger.warning("Empty embedding for article id=%d, skipping", row["id"])
                skipped += 1
                continue
            success = update_article_embedding(row["id"], emb)
            if success:
                batch_ok += 1
            else:
                skipped += 1

        updated += batch_ok
        logger.info(
            "Batch %d/%d: embedded %d articles (%.1fs)",
            batch_idx + 1, num_batches, batch_ok, elapsed,
        )

    total_time = time.monotonic() - overall_start
    logger.info(
        "Backfilled %d articles in %.1fs (%d skipped)",
        updated, total_time, skipped,
    )
    return updated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill missing article embeddings.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Articles per embedding API call (default: 50)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max articles to process (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count articles needing embeddings without processing them",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    count = backfill_embeddings(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        print(f"\nDone — {count} articles updated.")


if __name__ == "__main__":
    main()
