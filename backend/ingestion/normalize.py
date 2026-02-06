"""Article normalizer for ClearSignal ingestion pipeline.

Converts a batch of :class:`RawArticle` objects into fully normalized
:class:`Article` objects by:

1. Extracting and lowercasing the source domain from the article URL.
2. Looking up editorial-bias metadata from the static registry.
3. Stripping residual HTML from text fields.
4. Parsing dates from multiple formats into timezone-aware UTC datetimes.
5. Skipping articles that lack a title or URL.

This module is intentionally synchronous — it performs no I/O.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse, parse_qs, urlencode

from dateutil import parser as dateutil_parser

from config.sources import SOURCE_BIAS
from models.schemas import Article, RawArticle

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_DEFAULT_BIAS_LABEL = "center"
_DEFAULT_BIAS_SCORE = 0.0


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def extract_domain(url: str) -> str:
    """Extract the bare, lowercased domain from a URL.

    Strips the ``www.`` prefix so that ``https://www.nytimes.com/article``
    and ``https://nytimes.com/article`` both resolve to ``nytimes.com``.

    >>> extract_domain("https://www.NPR.org/2025/article")
    'npr.org'
    >>> extract_domain("")
    ''
    """
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
        return host.removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "source", "ref", "fbclid", "gclid", "mc_cid", "mc_eid",
}

_INDEX_SUFFIXES = ("/index.html", "/index.htm", "/index.php")


def normalize_url(url: str) -> str:
    """Normalize URL to canonical form for dedup comparison.

    Steps:
      1. Lowercase scheme and domain (preserves path case).
      2. Strip ``www.`` prefix from domain.
      3. Strip fragment.
      4. Strip known tracking query params; if only tracking params
         remain the query string is removed entirely.  Unknown params
         are kept to preserve article identity (e.g. ``?id=123``).
      5. Strip trailing slash.
      6. Remove common index suffixes (``/index.html``, etc.).

    Returns an empty string for empty/None input.
    """
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""

    # Ensure scheme exists so urlparse handles it correctly
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001
        return url

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path  # preserve case

    # Strip known tracking params, keep everything else
    query = ""
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
        if cleaned:
            # All non-tracking params survive — rebuild query string
            query = "?" + urlencode(cleaned, doseq=True)

    # Remove trailing slash
    if path.endswith("/"):
        path = path.rstrip("/")

    # Remove common index suffixes
    for suffix in _INDEX_SUFFIXES:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    return f"{scheme}://{netloc}{path}{query}"


def lookup_bias(domain: str) -> tuple[str, float]:
    """Look up editorial-bias metadata for a source domain.

    Returns:
        A ``(label, score)`` tuple.  Falls back to
        ``("center", 0.0)`` for unknown domains.

    >>> lookup_bias("foxnews.com")
    ('right-center', 0.4)
    >>> lookup_bias("unknown-blog.com")
    ('center', 0.0)
    """
    entry = SOURCE_BIAS.get(domain)
    if entry is not None:
        return (entry["label"], entry["score"])
    return (_DEFAULT_BIAS_LABEL, _DEFAULT_BIAS_SCORE)


def clean_html(text: str) -> str:
    """Strip HTML tags and decode HTML entities.

    Uses a simple regex — no heavy dependencies like BeautifulSoup.

    >>> clean_html("<p>Hello &amp; welcome</p>")
    'Hello & welcome'
    >>> clean_html("")
    ''
    """
    if not text:
        return ""
    return unescape(_HTML_TAG_RE.sub("", text)).strip()


def parse_date(raw: str | datetime | None) -> datetime:
    """Parse a date value into a timezone-aware UTC datetime.

    Handles ISO 8601, RFC 2822, and common variants via
    ``python-dateutil``.  If *raw* is already a :class:`datetime`,
    it is returned directly (with UTC attached when naive).

    Falls back to ``datetime.now(UTC)`` when parsing fails entirely.

    >>> parse_date("2025-05-15T14:30:00Z")
    datetime.datetime(2025, 5, 15, 14, 30, tzinfo=datetime.timezone.utc)
    >>> isinstance(parse_date(None), datetime)
    True
    """
    if raw is None:
        return datetime.now(timezone.utc)

    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw

    if not isinstance(raw, str) or not raw.strip():
        return datetime.now(timezone.utc)

    try:
        dt = dateutil_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, OverflowError):
        logger.debug("Unparseable date %r — using current time", raw)
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Core normalizer
# ---------------------------------------------------------------------------

def normalize(articles: list[RawArticle]) -> list[Article]:
    """Normalize a batch of raw articles into enriched Article objects.

    For each :class:`RawArticle`:

    * Skips entries with an empty ``url`` or ``title`` (logged as warnings).
    * Extracts the source domain from the URL.
    * Looks up bias label and score from the static registry.
    * Cleans HTML from ``description`` and ``body``.
    * Parses ``published_at`` into a UTC-aware datetime.

    Embedding and sentiment fields are left at their defaults (``[]``
    and ``0.0``) — those are filled by later pipeline stages.

    Args:
        articles: Raw articles from any ingestion source (RSS, NewsData,
            Google News, etc.).

    Returns:
        List of :class:`Article` objects, excluding any that were skipped.
    """
    normalized: list[Article] = []
    skipped_no_url = 0
    skipped_no_title = 0

    for raw in articles:
        if not raw.url or not raw.url.strip():
            skipped_no_url += 1
            continue
        if not raw.title or not raw.title.strip():
            skipped_no_title += 1
            continue

        clean_url = normalize_url(raw.url)
        domain = extract_domain(clean_url)
        bias_label, bias_score = lookup_bias(domain)

        normalized.append(
            Article(
                url=clean_url,
                title=raw.title.strip(),
                description=clean_html(raw.description),
                body=clean_html(raw.body),
                source_name=raw.source_name or domain,
                author=raw.author.strip() if raw.author else "",
                published_at=parse_date(raw.published_at),
                image_url=raw.image_url.strip() if raw.image_url else "",
                raw_source=raw.raw_source,
                source_domain=domain,
                source_bias=bias_label,
                source_bias_score=bias_score,
            )
        )

    total_skipped = skipped_no_url + skipped_no_title
    if total_skipped:
        logger.warning(
            "Skipped %d articles: %d empty URL, %d empty title",
            total_skipped, skipped_no_url, skipped_no_title,
        )

    logger.info(
        "Normalized %d / %d articles", len(normalized), len(articles),
    )
    return normalized


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

    # ── URL normalization tests ────────────────────────────────────────────
    print("Running normalize_url() tests...")
    assert normalize_url("https://www.CNN.com/path/?utm_source=rss") == "https://cnn.com/path"
    assert normalize_url("https://cnn.com/path/index.html") == "https://cnn.com/path"
    assert normalize_url("https://cnn.com/path/") == "https://cnn.com/path"
    assert normalize_url("https://reuters.com/article?id=123") == "https://reuters.com/article?id=123"
    assert normalize_url("") == ""
    assert normalize_url("https://cnn.com/path#section") == "https://cnn.com/path"
    assert normalize_url("https://www.CNN.com/2026/02/06/politics/vote/?utm_source=rss&ref=homepage") == "https://cnn.com/2026/02/06/politics/vote"
    assert normalize_url("https://cnn.com/path?fbclid=abc123&gclid=xyz") == "https://cnn.com/path"
    assert normalize_url("https://cnn.com/path?page=2&utm_source=rss") == "https://cnn.com/path?page=2"
    assert normalize_url("cnn.com/path") == "https://cnn.com/path"
    print("All URL normalization tests passed!\n")

    # ── Article normalization tests ────────────────────────────────────────
    fixtures: list[RawArticle] = [
        RawArticle(
            url="https://www.nytimes.com/2025/05/15/politics/story.html",
            title="Senate Passes Major Climate Bill",
            description="<p>The Senate voted 52-48 on a &ldquo;landmark&rdquo; bill.</p>",
            body="",
            source_name="nytimes.com",
            published_at=datetime(2025, 5, 15, 14, 30),
            raw_source={"type": "rss"},
        ),
        RawArticle(
            url="https://www.foxnews.com/politics/border-crisis-update",
            title="Border Crisis Worsens as Crossings Hit Record",
            description="Agents report a <b>surge</b> in illegal crossings.",
            body="<div>Full body text here.</div>",
            source_name="foxnews.com",
            raw_source={"type": "rss"},
        ),
        RawArticle(
            url="https://apnews.com/article/economy-growth-2025",
            title="US Economy Grows 3.1% in Q1",
            description="Growth exceeded expectations.",
            source_name="AP News",
            published_at=datetime(2025, 5, 14, 10, 0, tzinfo=timezone.utc),
            raw_source={"type": "googlenews"},
        ),
        # Should be SKIPPED — empty title
        RawArticle(
            url="https://example.com/no-title",
            title="",
            source_name="example.com",
            raw_source={"type": "rss"},
        ),
        # Should be SKIPPED — empty URL
        RawArticle(
            url="",
            title="Ghost Article",
            source_name="ghost.com",
            raw_source={"type": "newsdata"},
        ),
    ]

    results = normalize(fixtures)
    print(f"\n{'='*60}")
    print(f"Normalized: {len(results)} / {len(fixtures)} articles")
    print(f"{'='*60}")
    for art in results:
        print(f"  [{art.source_domain}] {art.title}")
        print(f"    bias={art.source_bias} ({art.source_bias_score:+.1f})")
        print(f"    desc={art.description[:60]}...")
        print(f"    date={art.published_at}")
        print()
