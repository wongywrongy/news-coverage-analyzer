"""NewsData.io fetcher for ClearSignal ingestion pipeline.

Pulls the latest articles from the NewsData.io /latest endpoint, one
request per category. Free tier allows 200 credits/day (1 credit per
request, up to 10 results each). Credit usage is tracked per call and
capped by ``max_credits``.

API docs: https://newsdata.io/documentation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from config.settings import settings
from models.schemas import RawArticle

logger = logging.getLogger(__name__)

_BASE_URL = "https://newsdata.io/api/1/latest"
_TIMEOUT = 20.0
_DEFAULT_CATEGORIES: list[str] = [
    "politics",
    "health",
    "science",
    "technology",
    "business",
    "world",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso_date(value: str | None) -> datetime | None:
    """Parse an ISO-8601 date string into a timezone-aware UTC datetime.

    NewsData.io returns dates like ``"2025-05-15 14:30:00"`` (no tz) or
    full ISO strings. Returns ``None`` on any parse failure.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _extract_domain(url: str) -> str:
    """Extract the bare domain from a URL (strips ``www.`` prefix)."""
    try:
        host = urlparse(url).netloc
        return host.removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


def _article_from_result(item: dict[str, Any], category: str) -> RawArticle | None:
    """Convert a single NewsData.io result dict into a RawArticle.

    Returns ``None`` if the result lacks a usable link.
    """
    link: str = item.get("link") or ""
    if not link:
        return None

    creators = item.get("creator") or []
    author = ", ".join(creators) if isinstance(creators, list) else ""

    return RawArticle(
        url=link,
        title=item.get("title") or "",
        description=item.get("description") or "",
        body=item.get("content") or "",
        source_name=_extract_domain(link),
        author=author,
        published_at=_parse_iso_date(item.get("pubDate")),
        image_url=item.get("image_url") or "",
        raw_source={
            "type": "newsdata",
            "category": category,
            "source_id": item.get("source_id", ""),
        },
    )


# ---------------------------------------------------------------------------
# Core fetcher
# ---------------------------------------------------------------------------

async def _fetch_category(
    client: httpx.AsyncClient,
    api_key: str,
    category: str,
) -> list[RawArticle]:
    """Fetch a single category from the NewsData.io /latest endpoint.

    Args:
        client: Shared ``httpx.AsyncClient``.
        api_key: NewsData.io API key.
        category: Category slug (e.g. ``"politics"``).

    Returns:
        List of :class:`RawArticle` for this category. Empty on error.
    """
    params: dict[str, str] = {
        "apikey": api_key,
        "language": "en",
        "country": "us",
        "category": category,
    }

    try:
        response = await client.get(_BASE_URL, params=params)

        if response.status_code == 429:
            logger.warning("NewsData rate-limited (429) on category=%s", category)
            return []
        if response.status_code == 401:
            logger.warning("NewsData auth failed (401) — check API key")
            return []

        response.raise_for_status()
        data = response.json()

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "NewsData HTTP %s for category=%s: %s",
            exc.response.status_code, category, exc,
        )
        return []
    except httpx.RequestError as exc:
        logger.warning("NewsData request error for category=%s: %s", category, exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("NewsData unexpected error for category=%s: %s", category, exc)
        return []

    if data.get("status") != "success":
        logger.warning(
            "NewsData non-success response for category=%s: %s",
            category, data.get("results", {}).get("message", data.get("status")),
        )
        return []

    results: list[dict[str, Any]] = data.get("results") or []
    articles: list[RawArticle] = []
    for item in results:
        article = _article_from_result(item, category)
        if article is not None:
            articles.append(article)

    logger.info("NewsData category=%s → %d articles", category, len(articles))
    return articles


async def fetch_newsdata(
    categories: list[str] | None = None,
    max_credits: int = 6,
) -> list[RawArticle]:
    """Fetch latest articles from NewsData.io across multiple categories.

    Each category costs 1 API credit and returns up to 10 articles.
    Requests are made sequentially to respect the free-tier rate limit
    and to stop as soon as ``max_credits`` is reached.

    Args:
        categories: Category slugs to query. Defaults to
            ``_DEFAULT_CATEGORIES``.
        max_credits: Maximum number of API credits (requests) to spend
            in this call.

    Returns:
        Flat list of :class:`RawArticle` from all successfully fetched
        categories. Returns ``[]`` if no API key is configured.
    """
    api_key = settings.newsdata_api_key
    if not api_key:
        logger.info("NewsData API key not configured — skipping")
        return []

    cats = categories if categories is not None else _DEFAULT_CATEGORIES
    if max_credits < 1:
        logger.info("max_credits=%d — nothing to fetch", max_credits)
        return []

    all_articles: list[RawArticle] = []
    credits_used = 0

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(_TIMEOUT),
        headers={"User-Agent": "ClearSignal/1.0 (news aggregator)"},
    ) as client:
        for category in cats:
            if credits_used >= max_credits:
                logger.info(
                    "Credit cap reached (%d/%d) — stopping",
                    credits_used, max_credits,
                )
                break

            articles = await _fetch_category(client, api_key, category)
            credits_used += 1
            all_articles.extend(articles)

    logger.info(
        "NewsData ingestion complete: %d articles, %d/%d credits used",
        len(all_articles), credits_used, max_credits,
    )
    return all_articles


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "backend" not in sys.path[0]:
        sys.path.insert(0, ".")

    async def _main() -> None:
        articles = await fetch_newsdata(max_credits=5)
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
