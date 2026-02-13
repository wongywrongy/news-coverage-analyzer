"""
Static registry of RSS feeds and their editorial-bias metadata.

RSS_FEEDS : feed URL → source domain
SOURCE_BIAS: source domain → {"label": str, "score": float}

Bias scores follow the AllSides / Ad Fontes scale mapped to [-1, 1]:
  -1.0  far left
  -0.6  left
  -0.3  left-center
   0.0  center
   0.3  right-center
   0.6  right
   1.0  far right

Consumed by: ingestion pipeline, bias-annotation step, analysis prompts.
"""

from __future__ import annotations

# ── RSS Feeds ─────────────────────────────────────────────────────────────────
# ~40 feeds spanning the full political spectrum.

RSS_FEEDS: dict[str, str] = {
    # ── Far Left ──────────────────────────────────────────
    "https://www.democracynow.org/democracynow.rss": "democracynow.org",
    "https://jacobin.com/feed": "jacobin.com",
    "https://theintercept.com/feed/?rss": "theintercept.com",

    # ── Left ──────────────────────────────────────────────
    "https://www.motherjones.com/feed/": "motherjones.com",
    "https://www.thenation.com/feed/": "thenation.com",
    "https://slate.com/feeds/all.rss": "slate.com",
    "https://www.vox.com/rss/index.xml": "vox.com",
    "https://www.msnbc.com/feeds/latest": "msnbc.com",

    # ── Left-Center ───────────────────────────────────────
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml": "nytimes.com",
    "https://feeds.washingtonpost.com/rss/national": "washingtonpost.com",
    "https://www.theguardian.com/us-news/rss": "theguardian.com",
    "https://feeds.nbcnews.com/nbcnews/public/news": "nbcnews.com",
    "https://feeds.abcnews.com/abcnews/topstories": "abcnews.go.com",
    "https://www.cbsnews.com/latest/rss/main": "cbsnews.com",
    "https://feeds.npr.org/1001/rss.xml": "npr.org",
    # Politico: direct RSS returns 403, OpenRSS times out
    # OpenRSS fallback: https://openrss.org/politico.com/
    "https://news.google.com/rss/search?q=when:24h+allinurl:politico.com&ceid=US:en&hl=en-US&gl=US": "politico.com",
    "https://time.com/feed/": "time.com",
    # Bloomberg: old site.xml feeds are dead; use feeds.bloomberg.com
    "https://feeds.bloomberg.com/markets/news.rss": "bloomberg.com",
    "https://feeds.bloomberg.com/politics/news.rss": "bloomberg.com",

    # ── Center ────────────────────────────────────────────
    # Reuters: official RSS killed June 2020
    # OpenRSS proxy: https://openrss.org/reuters.com/world/ (use if Google stops working)
    "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US": "reuters.com",
    "https://feeds.bbci.co.uk/news/world/rss.xml": "bbc.com",
    # AP News: old feeds and .rss suffix all dead
    # RSShub fallback: https://rsshub.app/apnews/topics/ap-top-news (403 from some networks)
    "https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com&ceid=US:en&hl=en-US&gl=US": "apnews.com",
    "https://thehill.com/feed/": "thehill.com",
    "https://www.pbs.org/newshour/feeds/rss/headlines": "pbs.org",
    # csmonitor.com — old /rss/all endpoint dead, use Google News proxy
    "https://news.google.com/rss/search?q=when:24h+allinurl:csmonitor.com&ceid=US:en&hl=en-US&gl=US": "csmonitor.com",
    # usatoday.com — old /rss/ endpoint dead, use Google News proxy
    "https://news.google.com/rss/search?q=when:24h+allinurl:usatoday.com&ceid=US:en&hl=en-US&gl=US": "usatoday.com",

    # ── Right-Center ──────────────────────────────────────
    "https://feeds.foxnews.com/foxnews/latest": "foxnews.com",
    "https://www.aljazeera.com/xml/rss/all.xml": "aljazeera.com",
    "https://www.washingtontimes.com/rss/headlines/news/": "washingtontimes.com",
    # WSJ: old wsj.com/xml feeds are dead; use Dow Jones infrastructure
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml": "wsj.com",
    "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml": "wsj.com",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml": "wsj.com",
    "https://feeds.a.dj.com/rss/RSSWSJD.xml": "wsj.com",
    "https://www.economist.com/united-states/rss.xml": "economist.com",
    "https://www.economist.com/international/rss.xml": "economist.com",
    # Forbes: old /real-time/feed2/ is dead; use new /feed/ paths
    "https://www.forbes.com/business/feed/": "forbes.com",
    "https://www.forbes.com/innovation/feed/": "forbes.com",
    "https://reason.com/feed/": "reason.com",
    "https://reason.com/latest/feed/": "reason.com",

    # ── Right ─────────────────────────────────────────────
    "https://www.nationalreview.com/feed/": "nationalreview.com",
    "https://nypost.com/feed/": "nypost.com",
    "https://www.washingtonexaminer.com/feed": "washingtonexaminer.com",
    "https://www.dailywire.com/feeds/rss.xml": "dailywire.com",
    "https://thefederalist.com/feed/": "thefederalist.com",

    # ── Far Right ─────────────────────────────────────────
    "https://www.breitbart.com/feed/": "breitbart.com",
    # newsmax.com — old RSS times out, use Google News proxy
    "https://news.google.com/rss/search?q=when:24h+allinurl:newsmax.com&ceid=US:en&hl=en-US&gl=US": "newsmax.com",
    "https://www.oann.com/feed/": "oann.com",
    "https://www.dailycaller.com/feed/": "dailycaller.com",
}


# ── Source Bias Metadata ──────────────────────────────────────────────────────

SOURCE_BIAS: dict[str, dict] = {
    # Far left (-1.0)
    "democracynow.org":      {"label": "far-left",      "score": -1.0, "region": "us",            "primary": True},
    "jacobin.com":           {"label": "far-left",      "score": -1.0, "region": "us",            "primary": False},
    "theintercept.com":      {"label": "far-left",      "score": -0.9, "region": "us",            "primary": True},

    # Left (-0.6)
    "motherjones.com":       {"label": "left",          "score": -0.7, "region": "us",            "primary": True},
    "thenation.com":         {"label": "left",          "score": -0.7, "region": "us",            "primary": False},
    "slate.com":             {"label": "left",          "score": -0.6, "region": "us",            "primary": True},
    "vox.com":               {"label": "left",          "score": -0.6, "region": "us",            "primary": True},
    "msnbc.com":             {"label": "left",          "score": -0.7, "region": "us",            "primary": True},

    # Left-center (-0.3)
    "nytimes.com":           {"label": "left-center",   "score": -0.3, "region": "us",            "primary": True},
    "washingtonpost.com":    {"label": "left-center",   "score": -0.3, "region": "us",            "primary": True},
    "theguardian.com":       {"label": "left-center",   "score": -0.4, "region": "international", "primary": True},
    "nbcnews.com":           {"label": "left-center",   "score": -0.2, "region": "us",            "primary": True},
    "abcnews.go.com":        {"label": "left-center",   "score": -0.2, "region": "us",            "primary": True},
    "cbsnews.com":           {"label": "left-center",   "score": -0.2, "region": "us",            "primary": True},
    "npr.org":               {"label": "left-center",   "score": -0.3, "region": "us",            "primary": True},
    "politico.com":          {"label": "left-center",   "score": -0.2, "region": "us",            "primary": True},
    "time.com":              {"label": "left-center",   "score": -0.3, "region": "us",            "primary": True},
    "bloomberg.com":         {"label": "left-center",   "score": -0.2, "region": "us",            "primary": True},

    # Center (0.0)
    "reuters.com":           {"label": "center",        "score":  0.0, "region": "international", "primary": True},
    "bbc.com":               {"label": "center",        "score":  0.0, "region": "international", "primary": True},
    "apnews.com":            {"label": "center",        "score":  0.0, "region": "us",            "primary": True},
    "thehill.com":           {"label": "center",        "score":  0.0, "region": "us",            "primary": True},
    "pbs.org":               {"label": "center",        "score": -0.1, "region": "us",            "primary": True},
    "csmonitor.com":         {"label": "center",        "score":  0.0, "region": "us",            "primary": False},
    "usatoday.com":          {"label": "center",        "score":  0.1, "region": "us",            "primary": True},

    # Right-center (0.3)
    "foxnews.com":           {"label": "right-center",  "score":  0.4, "region": "us",            "primary": True},
    "aljazeera.com":         {"label": "left-center",   "score": -0.2, "region": "international", "primary": False},
    "washingtontimes.com":   {"label": "right-center",  "score":  0.4, "region": "us",            "primary": True},
    "wsj.com":               {"label": "right-center",  "score":  0.3, "region": "us",            "primary": True},
    "economist.com":         {"label": "right-center",  "score":  0.2, "region": "international", "primary": True},
    "forbes.com":            {"label": "right-center",  "score":  0.3, "region": "us",            "primary": True},
    "reason.com":            {"label": "right-center",  "score":  0.4, "region": "us",            "primary": False},

    # Right (0.6)
    "nationalreview.com":    {"label": "right",         "score":  0.6, "region": "us",            "primary": True},
    "nypost.com":            {"label": "right",         "score":  0.6, "region": "us",            "primary": True},
    "washingtonexaminer.com":{"label": "right",         "score":  0.6, "region": "us",            "primary": True},
    "dailywire.com":         {"label": "right",         "score":  0.7, "region": "us",            "primary": True},
    "thefederalist.com":     {"label": "right",         "score":  0.7, "region": "us",            "primary": False},

    # Far right (1.0)
    "breitbart.com":         {"label": "far-right",     "score":  0.9, "region": "us",            "primary": True},
    "newsmax.com":           {"label": "far-right",     "score":  0.8, "region": "us",            "primary": True},
    "oann.com":              {"label": "far-right",     "score":  1.0, "region": "us",            "primary": False},
    "dailycaller.com":       {"label": "far-right",     "score":  0.8, "region": "us",            "primary": True},
}


def get_source_region(domain: str) -> str:
    """Return 'us' or 'international' for a source domain. Defaults to 'us'."""
    return SOURCE_BIAS.get(domain, {}).get("region", "us")


if __name__ == "__main__":
    import asyncio

    import feedparser
    import httpx
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # ── Registry overview ─────────────────────────────────────────────────
    reg_table = Table(title="ClearSignal Source Registry")
    reg_table.add_column("Domain", style="cyan")
    reg_table.add_column("Bias", style="bold")
    reg_table.add_column("Score", justify="right")
    reg_table.add_column("Has Feed", justify="center")

    feed_domains = set(RSS_FEEDS.values())
    for domain in sorted(SOURCE_BIAS):
        meta = SOURCE_BIAS[domain]
        has_feed = "✓" if domain in feed_domains else "✗"
        reg_table.add_row(domain, meta["label"], f"{meta['score']:+.1f}", has_feed)

    console.print(reg_table)
    console.print(
        f"\n[bold]{len(RSS_FEEDS)}[/bold] feeds across "
        f"[bold]{len(SOURCE_BIAS)}[/bold] rated sources\n"
    )

    # ── Feed validation ───────────────────────────────────────────────────
    OPENRSS_FALLBACKS: dict[str, str] = {
        "bloomberg.com": "https://openrss.org/bloomberg.com/markets/",
        "politico.com": "https://openrss.org/politico.com/",
        "economist.com": "https://openrss.org/economist.com/",
    }

    async def _validate_feeds() -> None:
        """HTTP-GET every feed, parse articles, print summary table."""
        results: list[tuple[str, str, str, int]] = []  # (source, url, status, count)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ClearSignal/1.0)",
            },
        ) as client:
            for url, domain in RSS_FEEDS.items():
                short_url = url.replace("https://", "").replace("http://", "")
                if len(short_url) > 50:
                    short_url = short_url[:47] + "..."
                label = f"{domain} ({short_url})"
                try:
                    resp = await client.get(url)
                    code = resp.status_code
                    if 200 <= code < 300:
                        feed = feedparser.parse(resp.text)
                        count = len(feed.entries)
                        status_str = f"[green]✅ {code}[/green]"
                    elif 300 <= code < 400:
                        count = 0
                        loc = resp.headers.get("location", "?")
                        status_str = f"[yellow]⚠️  {code} → {loc}[/yellow]"
                    else:
                        count = 0
                        status_str = f"[red]❌ {code}[/red]"
                except httpx.RequestError as exc:
                    code = 0
                    count = 0
                    status_str = f"[red]❌ {type(exc).__name__}[/red]"

                results.append((label, status_str, str(count), code))

        # Print results table
        val_table = Table(title="Feed Validation Results")
        val_table.add_column("Source / URL", style="cyan", max_width=60)
        val_table.add_column("Status", justify="center")
        val_table.add_column("Articles", justify="right")

        ok = warn = fail = 0
        for label, status_str, count, code in results:
            val_table.add_row(label, status_str, count)
            if 200 <= code < 300:
                ok += 1
            elif 300 <= code < 400:
                warn += 1
            else:
                fail += 1

        console.print(val_table)
        console.print(
            f"\n[bold green]{ok}[/bold green] OK  "
            f"[bold yellow]{warn}[/bold yellow] redirects  "
            f"[bold red]{fail}[/bold red] errors  "
            f"(total: {len(results)} feeds)"
        )

        if fail > 0:
            console.print("\n[bold]OpenRSS fallbacks for broken feeds:[/bold]")
            for label, _, _, code in results:
                if code >= 400 or code == 0:
                    domain = label.split(" (")[0]
                    fallback = OPENRSS_FALLBACKS.get(domain)
                    if fallback:
                        console.print(f"  {domain}: {fallback}")

    asyncio.run(_validate_feeds())
