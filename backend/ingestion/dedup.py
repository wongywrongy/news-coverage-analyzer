"""Article deduplication for ClearSignal ingestion pipeline.

Removes duplicate articles in two passes:

1. **URL dedup** — exact match on lowercased URL, also filtering against
   an optional set of URLs already stored in the database.
2. **Title dedup** — Jaccard similarity on word sets (threshold > 0.85).
   When two articles are near-duplicates (common with AP/Reuters
   syndication), the one with the longer description is kept.

This module is synchronous and requires no I/O — the caller is
responsible for supplying ``existing_urls`` from the database when
needed.
"""

from __future__ import annotations

import logging

from ingestion.normalize import normalize_url
from models.schemas import Article

logger = logging.getLogger(__name__)

_JACCARD_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_set(text: str) -> set[str]:
    """Lowercase a string and split into a set of words."""
    return set(text.lower().split())


def title_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between the word sets of two titles.

    Returns a float in ``[0.0, 1.0]``.  Returns ``0.0`` when both
    titles are empty.

    >>> title_similarity("Senate Passes Climate Bill", "Senate Passes Major Climate Bill")
    0.8
    >>> title_similarity("Completely Different", "Nothing In Common Here")
    0.0
    >>> title_similarity("", "")
    0.0
    """
    words_a = _word_set(a)
    words_b = _word_set(b)
    if not words_a and not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Core deduplicator
# ---------------------------------------------------------------------------

def deduplicate(
    articles: list[Article],
    existing_urls: set[str] | None = None,
) -> list[Article]:
    """Remove duplicate articles from a batch.

    Args:
        articles: Normalized articles from the current ingestion run.
        existing_urls: Optional set of lowercased URLs already in the
            database.  When provided, any article whose URL matches is
            dropped.  Pass ``None`` to skip the DB-URL check entirely
            (useful for testing or when the caller handles it).

    Returns:
        De-duplicated list of :class:`Article` objects, preserving
        original order for the survivors.
    """
    incoming_count = len(articles)

    # ── Pass 1: URL dedup ────────────────────────────────────────────────
    # Normalize DB URLs so that messy stored URLs match clean incoming ones
    normalized_existing: set[str] | None = None
    if existing_urls is not None:
        normalized_existing = {normalize_url(u) for u in existing_urls}

    db_url_dupes = 0
    batch_url_dupes = 0
    seen_urls: set[str] = set()
    url_unique: list[Article] = []

    for art in articles:
        norm_url = normalize_url(art.url)

        # Check against DB URLs first
        if normalized_existing is not None and norm_url in normalized_existing:
            db_url_dupes += 1
            continue

        # Check within current batch
        if norm_url in seen_urls:
            batch_url_dupes += 1
            continue

        seen_urls.add(norm_url)
        url_unique.append(art)

    total_url_dupes = db_url_dupes + batch_url_dupes
    if total_url_dupes:
        logger.info(
            "URL dedup: removed %d (%d DB, %d batch)",
            total_url_dupes, db_url_dupes, batch_url_dupes,
        )

    # ── Pass 2: Title dedup (within batch only) ──────────────────────────
    title_dupes = 0
    kept: list[Article] = []

    for candidate in url_unique:
        is_dup = False
        for i, existing in enumerate(kept):
            sim = title_similarity(candidate.title, existing.title)
            if sim > _JACCARD_THRESHOLD:
                title_dupes += 1
                is_dup = True
                # Keep the article with the longer description
                if len(candidate.description) > len(existing.description):
                    kept[i] = candidate
                break

        if not is_dup:
            kept.append(candidate)

    if title_dupes:
        logger.info(
            "Title dedup: removed %d near-duplicates (Jaccard > %.2f)",
            title_dupes, _JACCARD_THRESHOLD,
        )

    logger.info(
        "Dedup complete: %d → %d articles (%d URL dupes, %d title dupes)",
        incoming_count, len(kept), total_url_dupes, title_dupes,
    )
    return kept


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "backend" not in sys.path[0]:
        sys.path.insert(0, ".")

    def _make(url: str, title: str, desc: str = "", source: str = "test.com") -> Article:
        return Article(url=url, title=title, description=desc, source_name=source)

    fixtures: list[Article] = [
        # 1. Unique article
        _make(
            "https://nytimes.com/article-1",
            "Senate Passes Major Climate Bill in Late Night Vote",
            "The Senate voted 52-48 on a landmark climate bill.",
        ),
        # 2. Exact URL dupe of #1 (different case)
        _make(
            "https://NYTIMES.COM/article-1",
            "Senate Passes Major Climate Bill in Late Night Vote",
            "Short desc.",
        ),
        # 3. Near-duplicate title of #1 (AP syndication)
        _make(
            "https://apnews.com/article-1",
            "Senate Passes Major Climate Bill in Late-Night Vote",
            "WASHINGTON — The Senate voted 52-48 to pass a sweeping climate bill.",
        ),
        # 4. Completely different article
        _make(
            "https://foxnews.com/border-update",
            "Border Crossings Hit Record High in April",
            "Agents report a surge in illegal crossings.",
        ),
        # 5. DB URL dupe (simulated)
        _make(
            "https://reuters.com/economy-q1",
            "US Economy Grows 3.1% in Q1 2025",
            "Growth exceeded expectations.",
        ),
        # 6. Another unique
        _make(
            "https://bbc.com/tech-ai-2025",
            "AI Regulation Framework Proposed by EU Commission",
            "The European Commission unveiled new AI rules.",
        ),
    ]

    # Simulate DB already having one URL
    db_urls = {"https://reuters.com/economy-q1"}

    results = deduplicate(fixtures, existing_urls=db_urls)

    print(f"\n{'='*60}")
    print(f"Input: {len(fixtures)} articles")
    print(f"Output: {len(results)} unique articles")
    print(f"{'='*60}")

    # Show title similarity between #1 and #3 for demo
    sim = title_similarity(fixtures[0].title, fixtures[2].title)
    print("\nTitle similarity demo:")
    print(f"  A: {fixtures[0].title!r}")
    print(f"  B: {fixtures[2].title!r}")
    print(f"  Jaccard = {sim:.3f}  (threshold = {_JACCARD_THRESHOLD})")

    print("\nSurviving articles:")
    for art in results:
        print(f"  [{art.url}]")
        print(f"    {art.title}")
        print(f"    desc length = {len(art.description)}")
        print()
