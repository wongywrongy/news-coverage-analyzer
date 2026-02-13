"""One-time backfill of article bodies via trafilatura.

Scrapes the full article text for articles that have no body stored.
Rate-limited to 1 request/second to avoid IP bans.

Usage:
    cd backend
    python -m scripts.scrape_backfill               # default 50
    python -m scripts.scrape_backfill --limit 500   # scrape up to 500
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.scrape_backfill",
        description="Backfill article bodies via trafilatura",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max articles to scrape (default: 50)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    console.rule("[bold blue]Article Body Backfill[/bold blue]")
    console.print(f"  Limit: {args.limit}")

    from ingestion.scraper import scrape_missing_bodies

    result = scrape_missing_bodies(limit=args.limit)

    console.print(f"\n  Scraped: [bold green]{result['scraped']}[/bold green]")
    console.print(f"  Failed:  [bold red]{result['failed']}[/bold red]")
    console.print(f"  Skipped: [bold yellow]{result['skipped']}[/bold yellow]")
    console.rule("[bold green]Done[/bold green]")


if __name__ == "__main__":
    main()
