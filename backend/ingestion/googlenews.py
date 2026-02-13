"""Google News RSS fetcher for ClearSignal ingestion pipeline.

Google News provides free, unlimited RSS feeds for top stories and
topic-specific sections. Each entry is a story cluster — the primary
headline links through a ``news.google.com`` redirect whose Base64 path
encodes the real publisher URL in a protobuf blob.

Feed reference:
    Top stories : https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en
    Topic feed  : https://news.google.com/rss/topics/{TOPIC_ID}?hl=en-US&gl=US&ceid=US:en
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from calendar import timegm
from datetime import UTC, datetime
from html import unescape
from time import struct_time
from urllib.parse import urlparse

import feedparser
import httpx
from googlenewsdecoder import gnewsdecoder

from models.schemas import RawArticle

logger = logging.getLogger(__name__)

_BASE_URL = "https://news.google.com/rss"
_LOCALE_PARAMS = "hl=en-US&gl=US&ceid=US:en"
_TIMEOUT = 20.0
_MAX_CONCURRENCY = 5
_MAX_ENTRIES = 30
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Google News topic names for the headlines/section/topic/ URL format.
# This is more stable than the opaque Base64 topic IDs which can break.
_TOPIC_NAMES: dict[str, str] = {
    "us": "NATION",
    "world": "WORLD",
    "business": "BUSINESS",
    "technology": "TECHNOLOGY",
    "science": "SCIENCE",
    "health": "HEALTH",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    return unescape(_HTML_TAG_RE.sub("", text)).strip()


def _parse_date(entry: dict) -> datetime | None:
    """Extract a timezone-aware UTC datetime from a feedparser entry."""
    for field in ("published_parsed", "updated_parsed"):
        value: struct_time | None = entry.get(field)
        if value is not None:
            try:
                return datetime.fromtimestamp(timegm(value), tz=UTC)
            except (ValueError, OverflowError, OSError):
                continue
    return None


def _split_title(title: str) -> tuple[str, str]:
    """Split a Google News title into (headline, source_name).

    Google News titles follow ``"Headline text - Source Name"`` format.
    We split from the *right* on `` - `` so headlines containing dashes
    are preserved.  If no separator is found, the full title is returned
    with an empty source name.
    """
    if not title:
        return ("", "")
    parts = title.rsplit(" - ", maxsplit=1)
    if len(parts) == 2:
        return (parts[0].strip(), parts[1].strip())
    return (title.strip(), "")


def _extract_source_name(entry: dict, title_source: str) -> str:
    """Get the publisher name, preferring the ``<source>`` element.

    Falls back to the source name parsed from the title suffix.
    """
    # feedparser exposes <source> as entry.source with .value and .href
    source_obj = entry.get("source")
    if source_obj:
        name = getattr(source_obj, "value", "") or source_obj.get("value", "")
        if name:
            return name
    return title_source


def _decode_google_url_b64(google_url: str) -> str | None:
    """Attempt legacy Base64/protobuf decode of a Google News redirect URL.

    Works for older ``CBMi``-format URLs where the real URL is embedded
    as a plain ``http`` string.  Returns ``None`` for newer ``AU_yqL``
    payloads that use opaque article IDs.
    """
    marker = "/rss/articles/"
    idx = google_url.find(marker)
    if idx == -1:
        return None

    b64_segment = google_url[idx + len(marker):].split("?")[0]

    try:
        padding = 4 - len(b64_segment) % 4
        if padding != 4:
            b64_segment += "=" * padding
        decoded = base64.urlsafe_b64decode(b64_segment)

        decoded_str = decoded.decode("latin-1")
        http_idx = decoded_str.find("http")
        if http_idx == -1:
            return None

        url_chars: list[str] = []
        for ch in decoded_str[http_idx:]:
            if 0x20 < ord(ch) < 0x7F:
                url_chars.append(ch)
            else:
                break

        candidate = "".join(url_chars)
        if candidate.startswith(("http://", "https://")):
            return candidate

    except Exception as exc:  # noqa: BLE001
        logger.debug("Legacy b64 decode failed for: %s: %s", google_url, exc)

    return None


def _decode_google_url_api(google_url: str) -> str | None:
    """Decode a Google News URL via the googlenewsdecoder package.

    Uses Google's internal ``batchexecute`` API endpoint.  This is the
    only reliable method for the current ``AU_yqL`` URL format.

    Returns the real publisher URL, or ``None`` on failure.
    """
    try:
        result = gnewsdecoder(google_url, interval=None)
        if result and result.get("status"):
            return result["decoded_url"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("API decode failed for: %s: %s", google_url, exc)
    return None


def _extract_domain(url: str) -> str:
    """Extract the bare domain from a URL (strips ``www.`` prefix)."""
    try:
        host = urlparse(url).netloc
        return host.removeprefix("www.")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to extract domain from URL: %s", exc)
        return ""


def _build_topic_url(topic_name: str) -> str:
    """Build a full Google News RSS topic URL using the section format."""
    return f"{_BASE_URL}/headlines/section/topic/{topic_name}?{_LOCALE_PARAMS}"


# ---------------------------------------------------------------------------
# Core fetchers
# ---------------------------------------------------------------------------

async def _fetch_topic_feed(
    client: httpx.AsyncClient,
    feed_url: str,
    topic_label: str,
    semaphore: asyncio.Semaphore,
) -> list[RawArticle]:
    """Fetch and parse a single Google News topic RSS feed.

    Args:
        client: Shared ``httpx.AsyncClient``.
        feed_url: Full Google News RSS URL.
        topic_label: Human-readable label (e.g. ``"top_stories"``).
        semaphore: Concurrency limiter.

    Returns:
        Up to ``_MAX_ENTRIES`` :class:`RawArticle` objects.  Returns an
        empty list on any error.
    """
    try:
        async with semaphore:
            response = await client.get(feed_url)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Google News HTTP %s for topic=%s: %s",
            exc.response.status_code, topic_label, exc,
        )
        return []
    except httpx.RequestError as exc:
        logger.warning(
            "Google News request error for topic=%s: %s", topic_label, exc,
        )
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google News unexpected error for topic=%s: %s", topic_label, exc,
        )
        return []

    articles: list[RawArticle] = []
    for entry in feed.entries[:_MAX_ENTRIES]:
        google_link: str = entry.get("link", "")
        if not google_link:
            continue

        real_url = google_link  # resolved in batch after all feeds are fetched
        headline, title_source = _split_title(entry.get("title", ""))
        source_name = _extract_source_name(entry, title_source)

        articles.append(
            RawArticle(
                url=real_url,
                title=headline,
                description=_strip_html(
                    entry.get("summary", entry.get("description", ""))
                ),
                body="",
                source_name=source_name or _extract_domain(real_url),
                author="",
                published_at=_parse_date(entry),
                image_url="",
                raw_source={
                    "type": "googlenews",
                    "topic": topic_label,
                    "google_url": google_link,
                },
            )
        )

    logger.info(
        "Google News topic=%s → %d articles", topic_label, len(articles),
    )
    return articles


def _is_google_news_url(url: str) -> bool:
    """Check if a URL is still a Google News redirect."""
    return "news.google.com" in url


_RESOLVE_CONCURRENCY = 5


async def _resolve_single_url(
    article: RawArticle,
    semaphore: asyncio.Semaphore,
    loop: asyncio.AbstractEventLoop,
) -> bool:
    """Resolve one article's Google News URL. Returns True on success."""
    # Try legacy b64 first (instant, no network)
    real_url = _decode_google_url_b64(article.url)
    if not real_url:
        # Fall back to API decode (synchronous — run in thread pool)
        async with semaphore:
            real_url = await loop.run_in_executor(
                None, _decode_google_url_api, article.url,
            )
    if real_url and not _is_google_news_url(real_url):
        article.url = real_url
        # Always set source_name to the domain so it matches SOURCE_BIAS
        # keys and RSS-based naming (e.g. "nytimes.com" not "The New York Times")
        domain = _extract_domain(real_url)
        if domain:
            article.source_name = domain
        return True
    return False


async def _resolve_google_urls(articles: list[RawArticle]) -> int:
    """Batch-resolve unresolved Google News URLs to real publisher URLs.

    Uses ``googlenewsdecoder`` (via Google's batchexecute API) with
    concurrent thread-pool execution.  Updates each article's ``url``
    (and ``source_name`` when generic) in place.

    Returns the number of successfully resolved URLs.
    """
    unresolved = [a for a in articles if _is_google_news_url(a.url)]
    if not unresolved:
        return 0

    loop = asyncio.get_running_loop()
    semaphore = asyncio.Semaphore(_RESOLVE_CONCURRENCY)

    tasks = [
        _resolve_single_url(article, semaphore, loop)
        for article in unresolved
    ]
    results = await asyncio.gather(*tasks)
    resolved = sum(1 for r in results if r)

    logger.info(
        "URL resolution: %d/%d Google News URLs decoded to real publisher URLs",
        resolved, len(unresolved),
    )
    return resolved


async def fetch_google_news(
    topics: list[str] | None = None,
) -> list[RawArticle]:
    """Fetch articles from Google News RSS feeds.

    Always fetches the **top stories** feed, plus one feed for each
    requested topic section.

    Args:
        topics: Topic keys to fetch (see ``_TOPIC_NAMES`` for valid keys:
            ``us``, ``world``, ``business``, ``technology``, ``science``,
            ``health``).  Pass ``None`` to fetch all available topics.

    Returns:
        Flat list of :class:`RawArticle` from all successfully fetched
        feeds.
    """
    # Build list of (feed_url, label) pairs — always include top stories
    feeds: list[tuple[str, str]] = [
        (f"{_BASE_URL}?{_LOCALE_PARAMS}", "top_stories"),
    ]

    selected = topics if topics is not None else list(_TOPIC_NAMES.keys())
    for key in selected:
        topic_name = _TOPIC_NAMES.get(key)
        if topic_name is None:
            logger.warning(
                "Unknown Google News topic %r — skipping (valid: %s)",
                key, ", ".join(_TOPIC_NAMES),
            )
            continue
        feeds.append((_build_topic_url(topic_name), key))

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(_TIMEOUT),
        follow_redirects=True,
        headers={"User-Agent": "ClearSignal/1.0 (news aggregator)"},
    ) as client:
        tasks = [
            _fetch_topic_feed(client, url, label, semaphore)
            for url, label in feeds
        ]
        results = await asyncio.gather(*tasks)

    articles = [article for batch in results for article in batch]

    # Resolve any remaining Google News redirect URLs to real publisher URLs
    still_google = sum(1 for a in articles if _is_google_news_url(a.url))
    if still_google:
        logger.info(
            "Resolving %d/%d Google News redirect URLs…",
            still_google, len(articles),
        )
        resolved = await _resolve_google_urls(articles)
        final_google = sum(1 for a in articles if _is_google_news_url(a.url))
        logger.info(
            "Resolved %d/%d Google News URLs to real publisher URLs "
            "(%d still unresolved)",
            resolved, still_google, final_google,
        )

    logger.info(
        "Google News ingestion complete: %d articles from %d feeds",
        len(articles), len(feeds),
    )
    return articles


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from collections import Counter

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "backend" not in sys.path[0]:
        sys.path.insert(0, ".")

    async def _main() -> None:
        articles = await fetch_google_news()

        # URL resolution stats
        google_urls = [a for a in articles if _is_google_news_url(a.url)]
        real_urls = [a for a in articles if not _is_google_news_url(a.url)]

        print(f"\n{'='*60}")
        print(f"Total articles fetched: {len(articles)}")
        print(f"Real publisher URLs:    {len(real_urls)}")
        print(f"Unresolved Google URLs: {len(google_urls)}")
        print(f"{'='*60}")

        # Domain distribution
        domains = Counter(_extract_domain(a.url) for a in articles)
        print("\nTop source domains:")
        for domain, count in domains.most_common(15):
            print(f"  {domain:30s} {count}")

        # Sample articles
        print("\nSample resolved articles:")
        for art in real_urls[:5]:
            date_str = (
                art.published_at.strftime("%Y-%m-%d %H:%M")
                if art.published_at
                else "no date"
            )
            domain = _extract_domain(art.url)
            google_url = art.raw_source.get("google_url", "")
            print(f"  [{art.source_name}] {art.title}")
            print(f"    BEFORE: {google_url[:70]}...")
            print(f"    AFTER:  {art.url[:70]}")
            print(f"    domain: {domain}  ({date_str})")
            print()

        if google_urls:
            print("Sample UNRESOLVED articles:")
            for art in google_urls[:3]:
                print(f"  [{art.source_name}] {art.title}")
                print(f"    URL: {art.url[:70]}...")
                print()

    asyncio.run(_main())
