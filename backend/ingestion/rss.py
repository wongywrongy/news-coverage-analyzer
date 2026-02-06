"""RSS feed fetcher for ClearSignal ingestion pipeline.

Fetches articles from configured RSS feeds concurrently using httpx and
feedparser. Enforces a concurrency limit, per-feed entry cap, and
graceful error handling so a single broken feed never crashes the pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import re
from calendar import timegm
from datetime import datetime, timezone
from html import unescape
from time import struct_time

import feedparser
import httpx

from config.sources import RSS_FEEDS
from models.schemas import RawArticle

logger = logging.getLogger(__name__)

_TIMEOUT = 20.0
_MAX_CONCURRENCY = 5
_MAX_ENTRIES = 25
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_SUFFIX_RE = re.compile(r"\s*[-–—|]\s*[^-–—|]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    return unescape(_HTML_TAG_RE.sub("", text)).strip()


def _clean_title(title: str) -> str:
    """Strip trailing ' - SourceName' style suffixes from a title."""
    if not title:
        return ""
    return _TITLE_SUFFIX_RE.sub("", title).strip()


def _parse_date(entry: dict) -> datetime | None:
    """Extract a timezone-aware datetime from a feedparser entry.

    Tries ``published_parsed`` first, then ``updated_parsed``.  Returns
    ``None`` when neither field is usable.
    """
    for field in ("published_parsed", "updated_parsed"):
        value: struct_time | None = entry.get(field)
        if value is not None:
            try:
                return datetime.fromtimestamp(timegm(value), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
    return None


# ---------------------------------------------------------------------------
# Core fetchers
# ---------------------------------------------------------------------------

async def fetch_single_feed(
    client: httpx.AsyncClient,
    feed_url: str,
    source_domain: str,
    semaphore: asyncio.Semaphore | None = None,
) -> list[RawArticle]:
    """Fetch and parse a single RSS feed into a list of RawArticles.

    Args:
        client: Shared ``httpx.AsyncClient`` for connection pooling.
        feed_url: URL of the RSS/Atom feed.
        source_domain: Canonical domain tag for the source (e.g. ``"nytimes.com"``).
        semaphore: Optional concurrency limiter. When provided the HTTP
            request is made inside the semaphore context.

    Returns:
        Up to ``_MAX_ENTRIES`` :class:`RawArticle` objects. Returns an
        empty list on any error instead of raising.
    """
    try:
        if semaphore is not None:
            async with semaphore:
                response = await client.get(feed_url)
        else:
            response = await client.get(feed_url)

        response.raise_for_status()
        feed = feedparser.parse(response.text)

        articles: list[RawArticle] = []
        for entry in feed.entries[:_MAX_ENTRIES]:
            link: str = entry.get("link", "")
            if not link:
                continue

            articles.append(
                RawArticle(
                    url=link,
                    title=_clean_title(entry.get("title", "")),
                    description=_strip_html(
                        entry.get("summary", entry.get("description", ""))
                    ),
                    body="",  # RSS feeds rarely carry full text
                    source_name=source_domain,
                    author=entry.get("author", ""),
                    published_at=_parse_date(entry),
                    image_url=_extract_image(entry),
                    raw_source={"type": "rss", "feed_url": feed_url},
                )
            )

        logger.info(
            "Fetched %d articles from %s", len(articles), source_domain
        )
        return articles

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %s from %s: %s", exc.response.status_code, feed_url, exc
        )
    except httpx.RequestError as exc:
        logger.warning("Request error for %s: %s", feed_url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error parsing %s: %s", feed_url, exc)

    return []


def _extract_image(entry: dict) -> str:
    """Best-effort extraction of a thumbnail / media image URL."""
    # media_thumbnail (common in RSS 2.0 with media namespace)
    thumbnails = entry.get("media_thumbnail", [])
    if thumbnails and isinstance(thumbnails, list):
        url = thumbnails[0].get("url", "")
        if url:
            return url

    # media_content
    media = entry.get("media_content", [])
    if media and isinstance(media, list):
        url = media[0].get("url", "")
        if url:
            return url

    # enclosure (podcasts / image feeds)
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image/"):
            return link.get("href", "")

    return ""


async def fetch_all_feeds() -> list[RawArticle]:
    """Fetch all configured RSS feeds concurrently.

    Uses a shared ``httpx.AsyncClient`` with a 20-second timeout and an
    ``asyncio.Semaphore`` to cap concurrency at 5 simultaneous requests.

    Returns:
        A flat list of :class:`RawArticle` from every successfully fetched
        feed.
    """
    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(_TIMEOUT),
        follow_redirects=True,
        headers={"User-Agent": "ClearSignal/1.0 (news aggregator)"},
    ) as client:
        tasks = [
            fetch_single_feed(client, url, domain, semaphore)
            for url, domain in RSS_FEEDS.items()
        ]
        results = await asyncio.gather(*tasks)

    articles = [article for batch in results for article in batch]
    logger.info(
        "RSS ingestion complete: %d articles from %d feeds",
        len(articles),
        len(RSS_FEEDS),
    )
    return articles


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Allow running from project root: python -m ingestion.rss
    # or directly: python ingestion/rss.py
    if "backend" not in sys.path[0]:
        sys.path.insert(0, ".")

    async def _main() -> None:
        articles = await fetch_all_feeds()
        print(f"\n{'='*60}")
        print(f"Total articles fetched: {len(articles)}")
        print(f"{'='*60}")
        for art in articles[:5]:
            date_str = (
                art.published_at.strftime("%Y-%m-%d %H:%M")
                if art.published_at
                else "no date"
            )
            print(f"  [{art.source_name}] {art.title}  ({date_str})")

    asyncio.run(_main())
