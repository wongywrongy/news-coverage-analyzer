"""
ClearSignal shared data models.

All pipeline stages communicate through these Pydantic models.
Serialisation is handled by Pydantic v2's .model_dump() / .model_validate().
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Raw Article ───────────────────────────────────────────────────────────────

class RawArticle(BaseModel):
    """Raw article straight from an RSS feed or news API.

    Producer: ingestion/fetcher  →  Consumer: ingestion/deduplicator, storage
    """
    url: str
    title: str
    description: str = ""
    body: str = ""
    source_name: str
    author: str = ""
    published_at: datetime | None = None
    image_url: str = ""
    raw_source: dict[str, Any] = Field(default_factory=dict)


# ── Enriched Article ──────────────────────────────────────────────────────────

class Article(BaseModel):
    """Article enriched with bias metadata, embedding, and sentiment.

    Producer: enrichment pipeline  →  Consumer: clustering, storage, API
    """
    # ── fields inherited from RawArticle ──
    url: str
    title: str
    description: str = ""
    body: str = ""
    source_name: str
    author: str = ""
    published_at: datetime | None = None
    image_url: str = ""
    raw_source: dict[str, Any] = Field(default_factory=dict)

    # ── enrichment fields ──
    source_domain: str = ""
    source_bias: str = ""
    source_bias_score: float = 0.0
    embedding: list[float] = Field(default_factory=list)
    sentiment: float = 0.0  # -1.0 negative … +1.0 positive


# ── Story (cluster of articles) ──────────────────────────────────────────────

class Story(BaseModel):
    """A cluster of articles covering the same underlying event or topic.

    Producer: clustering pipeline  →  Consumer: analysis, scoring, API
    """
    id: int | None = None
    topic: str = ""
    category: str = ""
    impact_score: float = 0.0
    attention_score: float = 0.0
    article_count: int = 0
    source_count: int = 0
    avg_bias_score: float = 0.0
    bias_spread: float = 0.0        # max - min bias score in cluster
    population_affected: str = ""
    sentiment_left: float | None = None
    sentiment_center: float | None = None
    sentiment_right: float | None = None
    first_seen: datetime | None = None
    last_updated: datetime | None = None
    peak_date: str | None = None
    status: str = "developing"
    centroid: list[float] = Field(default_factory=list)
    trend: list[dict] = Field(default_factory=list)
    active: bool = True
    created_at: datetime | None = None
    significance_score: int | None = None
    significance_factors: dict[str, Any] | None = None
    confidence: str = ""
    caveats: list[str] = Field(default_factory=list)
    last_article_at: datetime | None = None
    coverage_velocity: float | None = None
    impact_scored_at: datetime | None = None
    scored_at_article_count: int = 0


# ── AI Analysis ──────────────────────────────────────────────────────────────

class Analysis(BaseModel):
    """Claude-generated editorial analysis of a Story.

    Producer: analysis/analyzer (Claude)  →  Consumer: API, frontend
    """
    story_id: int
    headline: str = ""
    dateline: str = ""
    lede: str = ""
    body: list[dict] = Field(default_factory=list)
    context: str = ""
    source_framings: list[dict] = Field(default_factory=list)
    contrasts: list[dict] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    bottom_line: str = ""
    coverage_note: str = ""
    spectrum: str = ""
    framing_check: str = ""
    generated_at: datetime | None = None
    article_count_at_gen: int = 0
    analysis_version: int = 1


# ── Ingestion Result ─────────────────────────────────────────────────────────

class IngestionResult(BaseModel):
    """Summary returned after a single ingestion run.

    Producer: ingestion pipeline  →  Consumer: scheduler, dashboard
    """
    total_fetched: int = 0
    duplicates_skipped: int = 0
    new_stored: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    per_source: dict[str, dict[str, int]] = Field(default_factory=dict)


if __name__ == "__main__":
    from rich import print as rprint

    # Demo: round-trip a RawArticle
    sample = RawArticle(
        url="https://example.com/article",
        title="Demo Article",
        source_name="example.com",
        published_at=datetime.now(),
    )
    rprint("[bold green]RawArticle round-trip[/bold green]")
    rprint(sample.model_dump())

    # Demo: Story with defaults
    story = Story(id=1, topic="Test Topic", article_count=5, source_count=3)
    rprint("\n[bold green]Story defaults[/bold green]")
    rprint(story.model_dump())

    # Demo: IngestionResult
    result = IngestionResult(
        total_fetched=120,
        duplicates_skipped=30,
        new_stored=85,
        errors=5,
        duration_seconds=12.4,
        per_source={"nytimes.com": {"fetched": 20, "stored": 18}},
    )
    rprint("\n[bold green]IngestionResult[/bold green]")
    rprint(result.model_dump())
