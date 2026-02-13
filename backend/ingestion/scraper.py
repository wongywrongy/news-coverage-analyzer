"""Article body extraction via trafilatura.

Fetches the full text of an article from its URL using trafilatura,
which handles boilerplate removal, paywall fragments, and encoding.

Used by the pipeline to enrich articles that only have headlines/descriptions.
"""

from __future__ import annotations

import logging
import time

from db.client import get_client

logger = logging.getLogger(__name__)

# Domains known to block scrapers or require authentication
SKIP_DOMAINS = frozenset({
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "washingtonpost.com",
    "theathletic.com",
    "economist.com",
    "barrons.com",
    "news.google.com",
    "politico.com",
    "axios.com",
})

# Max characters to keep from scraped body (≈300 words)
MAX_BODY_CHARS = 2000


def scrape_article_body(url: str) -> str:
    """Fetch and extract article body text. Returns "" on failure."""
    import trafilatura
    from trafilatura.settings import use_config

    config = use_config()
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", "10")

    try:
        downloaded = trafilatura.fetch_url(url, config=config)
        if not downloaded:
            return ""
        text = trafilatura.extract(downloaded)
        if not text:
            return ""
        return text[:MAX_BODY_CHARS]
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        logger.debug("Scrape failed for %s: %s", url, exc, exc_info=True)
        return ""


def _should_skip(url: str) -> bool:
    """Check if URL belongs to a domain known to block scrapers."""
    for domain in SKIP_DOMAINS:
        if domain in url:
            return True
    return False


def scrape_missing_bodies(
    limit: int = 50,
    selected_story_ids: list[int] | None = None,
) -> dict:
    """Fetch bodies for articles where body is empty.

    Args:
        limit: Max articles to scrape.
        selected_story_ids: If provided, only scrape articles belonging to
            these stories.  If None, scrape all articles with empty bodies.

    Returns {"scraped": int, "failed": int, "skipped": int}
    """
    client = get_client()
    stats = {"scraped": 0, "failed": 0, "skipped": 0}

    # Query articles with empty or null body
    query = (
        client.table("articles")
        .select("id, url")
        .or_("body.is.null,body.eq.")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if selected_story_ids is not None and selected_story_ids:
        query = query.in_("story_id", selected_story_ids)
    resp = query.execute()
    articles = resp.data or []

    if not articles:
        logger.info("No articles need body scraping")
        return stats

    logger.info("Scraping bodies for %d articles", len(articles))

    for article in articles:
        url = article.get("url", "")

        if _should_skip(url):
            stats["skipped"] += 1
            continue

        body = scrape_article_body(url)

        if body:
            try:
                client.table("articles").update({"body": body}).eq(
                    "id", article["id"]
                ).execute()
                stats["scraped"] += 1
            except Exception as exc:
                logger.warning("Failed to update body for article %d: %s", article["id"], exc)
                stats["failed"] += 1
        else:
            stats["failed"] += 1

        # Rate limit: 1 second between requests
        time.sleep(1)

    logger.info(
        "Scraping complete: scraped=%d, failed=%d, skipped=%d",
        stats["scraped"],
        stats["failed"],
        stats["skipped"],
    )
    return stats


if __name__ == "__main__":
    import sys

    logging.basicConfig(level="INFO", format="%(name)s | %(message)s")

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    result = scrape_missing_bodies(limit=limit)
    print(f"\nScraped: {result['scraped']}")
    print(f"Failed:  {result['failed']}")
    print(f"Skipped: {result['skipped']}")
