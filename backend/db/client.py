"""
Supabase client singleton.

Every database operation in the project goes through get_client().
No other module should import supabase directly.

Usage:
    from db.client import get_client
    client = get_client()
    client.table("articles").select("*").execute()
"""

from __future__ import annotations

import logging

from supabase import Client, create_client

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Return the shared Supabase client, creating it on first call."""
    global _client
    if _client is None:
        logger.info("Initialising Supabase client → %s", settings.supabase_url)
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


if __name__ == "__main__":
    from rich import print as rprint

    logging.basicConfig(level="DEBUG")
    client = get_client()
    rprint(f"[bold green]Connected[/bold green] → {settings.supabase_url}")
    # Quick smoke test: list tables via a harmless query
    result = client.table("articles").select("count", count="exact").execute()
    rprint(f"  articles row count: {result.count}")
