"""
ClearSignal configuration — loads all settings from .env via pydantic-settings.

Usage:
    from config.settings import settings
    print(settings.supabase_url)
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────
    supabase_url: str
    supabase_key: str

    # ── AI providers ──────────────────────────────────────
    openai_api_key: str
    anthropic_api_key: str

    # ── News data ─────────────────────────────────────────
    newsdata_api_key: str = ""

    # ── Embedding mode ────────────────────────────────────
    embedding_mode: Literal["openai", "local"] = "openai"

    # ── Models ──────────────────────────────────────────
    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-sonnet-4-20250514"
    haiku_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "text-embedding-3-small"

    # ── Analysis ─────────────────────────────────────────
    analysis_batch_size: int = 10
    min_significance_score: int = 45
    max_analysis_tokens: int = 8000
    current_analysis_version: int = 2

    # ── Editorial selection ────────────────────────────
    max_stories_per_analysis_cycle: int = 8
    selection_enabled: bool = True

    # ── Logging ───────────────────────────────────────────
    log_level: str = "INFO"


settings = Settings()

logger = logging.getLogger(__name__)
logger.info("Settings loaded  |  embedding_mode=%s  log_level=%s", settings.embedding_mode, settings.log_level)


if __name__ == "__main__":
    from rich import print as rprint

    rprint("[bold green]ClearSignal Settings[/bold green]")
    rprint(f"  supabase_url   = {settings.supabase_url[:30]}…")
    rprint(f"  embedding_mode = {settings.embedding_mode}")
    rprint(f"  log_level      = {settings.log_level}")
