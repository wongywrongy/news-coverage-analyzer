"""
Ingestion orchestrator — calls other modules, contains no business logic.

Runs the full fetch → normalize → deduplicate → embed → store pipeline
and returns an IngestionResult with timing and per-source statistics.
"""

import asyncio
import logging
import time
from collections import defaultdict

from rich.console import Console
from rich.table import Table

from config.sources import SOURCE_BIAS
from db import queries as db
from ingestion.newsdata import fetch_newsdata
from ingestion.rss import fetch_all_feeds
from models.schemas import Article, IngestionResult, RawArticle

logger = logging.getLogger(__name__)
console = Console()


# ── Optional modules — pipeline degrades gracefully without them ──────────

try:
    from ingestion.googlenews import fetch_google_news
except ImportError:
    fetch_google_news = None  # type: ignore[assignment]

try:
    from ingestion.normalize import normalize
except ImportError:
    normalize = None  # type: ignore[assignment]

try:
    from ingestion.dedup import deduplicate
except ImportError:
    deduplicate = None  # type: ignore[assignment]

try:
    from ingestion.embed import embed_articles
except ImportError:
    embed_articles = None  # type: ignore[assignment]


# ── Internal helpers ──────────────────────────────────────────────────────


async def _fetch_all() -> tuple[list[RawArticle], int]:
    """Run all available fetchers concurrently.

    Returns:
        Tuple of (combined article list, number of fetcher errors).
    """
    coros = []
    labels = []

    labels.append("RSS feeds")
    coros.append(fetch_all_feeds())

    labels.append("NewsData.io")
    coros.append(fetch_newsdata())

    if fetch_google_news is not None:
        labels.append("Google News")
        coros.append(fetch_google_news())

    articles: list[RawArticle] = []
    errors = 0

    outcomes = await asyncio.gather(*coros, return_exceptions=True)

    for label, outcome in zip(labels, outcomes):
        if isinstance(outcome, Exception):
            logger.error("Fetcher '%s' failed: %s", label, outcome)
            errors += 1
        else:
            logger.info("Fetcher '%s' returned %d articles", label, len(outcome))
            articles.extend(outcome)

    return articles, errors


def _normalize_fallback(raw_articles: list[RawArticle]) -> list[Article]:
    """Minimal RawArticle → Article conversion with SOURCE_BIAS lookup."""
    result: list[Article] = []
    for raw in raw_articles:
        data = raw.model_dump()
        bias = SOURCE_BIAS.get(raw.source_name, {})
        data["source_domain"] = raw.source_name
        data["source_bias"] = bias.get("label", "")
        data["source_bias_score"] = bias.get("score", 0.0)
        result.append(Article.model_validate(data))
    return result


def _deduplicate_fallback(
    articles: list[Article], existing_urls: set[str],
) -> list[Article]:
    """Remove articles whose URL already exists in the DB or in this batch."""
    seen: set[str] = set()
    unique: list[Article] = []
    for article in articles:
        if article.url not in existing_urls and article.url not in seen:
            seen.add(article.url)
            unique.append(article)
    return unique


def _build_per_source(
    fetched: list[RawArticle],
    new_articles: list[Article],
) -> dict[str, dict[str, int]]:
    """Build per-source stats: {source: {fetched, new, errors}}."""
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"fetched": 0, "new": 0, "errors": 0},
    )
    for a in fetched:
        stats[a.source_name]["fetched"] += 1
    for a in new_articles:
        stats[a.source_name]["new"] += 1
    return dict(stats)


def _print_summary(result: IngestionResult, embedded_count: int) -> None:
    """Print a rich table with per-source breakdown and totals."""
    table = Table(title="Ingestion Summary")
    table.add_column("Source", style="cyan")
    table.add_column("Bias", style="bold")
    table.add_column("Fetched", justify="right")
    table.add_column("New", justify="right", style="green")
    table.add_column("Errors", justify="right", style="red")

    for source in sorted(result.per_source):
        counts = result.per_source[source]
        bias = SOURCE_BIAS.get(source, {})
        table.add_row(
            source,
            bias.get("label", "unknown"),
            str(counts.get("fetched", 0)),
            str(counts.get("new", 0)),
            str(counts.get("errors", 0)),
        )

    console.print(table)
    deduped = result.total_fetched - result.duplicates_skipped
    console.print(
        f"\n[bold]Totals:[/bold] {result.total_fetched} fetched "
        f"-> {deduped} deduped -> {embedded_count} embedded "
        f"-> {result.new_stored} stored "
        f"[dim]({result.duration_seconds:.1f}s)[/dim]",
    )


# ── Public API ────────────────────────────────────────────────────────────


def run_ingestion(dry_run: bool = False) -> IngestionResult:
    """Execute the full ingestion pipeline.

    Pipeline: fetch → normalize → deduplicate → embed → store.

    Args:
        dry_run: If True, skip the final database insert.

    Returns:
        IngestionResult with timing and per-source statistics.
    """
    start = time.monotonic()
    fetch_errors = 0

    # ── 1. Fetch from all sources concurrently ────────────────────────────
    logger.info("Starting ingestion pipeline (dry_run=%s)", dry_run)
    try:
        raw_articles, fetch_errors = asyncio.run(_fetch_all())
    except Exception as exc:
        logger.error("All fetchers failed: %s", exc)
        raw_articles = []
        fetch_errors = 1

    logger.info(
        "Fetched %d raw articles (%d fetch errors)",
        len(raw_articles), fetch_errors,
    )

    if not raw_articles:
        result = IngestionResult(
            errors=fetch_errors,
            duration_seconds=time.monotonic() - start,
        )
        _print_summary(result, embedded_count=0)
        return result

    # ── 2. Normalize: RawArticle → Article ────────────────────────────────
    try:
        if normalize is not None:
            articles = normalize(raw_articles)
        else:
            articles = _normalize_fallback(raw_articles)
        logger.info("Normalized %d articles", len(articles))
    except Exception as exc:
        logger.error("Normalize failed, using fallback: %s", exc)
        articles = _normalize_fallback(raw_articles)

    # ── 3. Deduplicate against existing DB URLs ───────────────────────────
    try:
        existing_urls = db.get_existing_urls([a.url for a in articles])
    except Exception as exc:
        logger.error("get_existing_urls failed, skipping dedup: %s", exc)
        existing_urls = set()

    try:
        if deduplicate is not None:
            new_articles = deduplicate(articles, existing_urls)
        else:
            new_articles = _deduplicate_fallback(articles, existing_urls)
    except Exception as exc:
        logger.error("Deduplicate failed, using fallback: %s", exc)
        new_articles = _deduplicate_fallback(articles, existing_urls)

    duplicates_skipped = len(articles) - len(new_articles)
    logger.info(
        "Deduplicated: %d → %d (%d skipped)",
        len(articles), len(new_articles), duplicates_skipped,
    )

    # ── 4. Embed articles ─────────────────────────────────────────────────
    embedded_articles = new_articles
    embedded_count = 0
    if new_articles:
        try:
            if embed_articles is not None:
                embedded_articles = embed_articles(new_articles)
                embedded_count = sum(
                    1 for a in embedded_articles if a.embedding
                )
                logger.info(
                    "Embedded %d / %d articles",
                    embedded_count, len(new_articles),
                )
            else:
                logger.debug("embed_articles not available — skipping embeddings")
        except Exception as exc:
            logger.error(
                "Embedding failed — storing without embeddings: %s", exc,
            )
            embedded_articles = new_articles

    # ── 5. Store in database (skip if dry_run) ────────────────────────────
    stored_count = 0
    if dry_run:
        stored_count = len(embedded_articles)
        logger.info("Dry run — would store %d articles", stored_count)
    elif embedded_articles:
        try:
            rows = [a.model_dump(mode="json") for a in embedded_articles]
            # Strip empty embeddings to avoid storing zero-length vectors
            for row in rows:
                if not row.get("embedding"):
                    row.pop("embedding", None)
            stored_count = db.insert_articles(rows)
            logger.info("Stored %d articles", stored_count)
        except Exception as exc:
            logger.error("insert_articles failed: %s", exc)
            fetch_errors += 1

    # ── 6. Build and return result ────────────────────────────────────────
    per_source = _build_per_source(raw_articles, new_articles)

    result = IngestionResult(
        total_fetched=len(raw_articles),
        duplicates_skipped=duplicates_skipped,
        new_stored=stored_count,
        errors=fetch_errors,
        duration_seconds=time.monotonic() - start,
        per_source=per_source,
    )

    _print_summary(result, embedded_count=embedded_count)
    return result


# ── CLI entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="ClearSignal ingestion pipeline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and process without storing to database",
    )
    args = parser.parse_args()

    result = run_ingestion(dry_run=args.dry_run)
    console.print(f"\n[bold]Result:[/bold] {result.model_dump_json(indent=2)}")
