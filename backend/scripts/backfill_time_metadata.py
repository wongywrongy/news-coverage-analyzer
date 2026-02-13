"""One-time backfill of time metadata for existing stories.

Computes first_seen, last_article_at, story status, and coverage_velocity
from article timestamps for all active stories.

Usage:
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_time_metadata
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from db.queries import get_active_stories, get_articles_for_story, update_story_metadata

logging.basicConfig(level="INFO", format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _determine_status(age_hours: float, hours_since_last: float) -> str:
    if age_hours < 6:
        return "breaking"
    if hours_since_last < 24:
        return "developing"
    if hours_since_last < 72:
        return "ongoing"
    return "stale"


def backfill():
    stories = get_active_stories()
    logger.info("Backfilling time metadata for %d active stories", len(stories))

    updated = 0
    skipped = 0

    for story in stories:
        story_id = story["id"]
        articles = get_articles_for_story(story_id)

        if not articles:
            skipped += 1
            continue

        pub_dates = []
        for a in articles:
            raw = a.get("published_at")
            if not raw:
                continue
            try:
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                pub_dates.append(dt)
            except (ValueError, TypeError):
                continue

        if not pub_dates:
            skipped += 1
            continue

        now = datetime.now(UTC)
        earliest = min(pub_dates)
        latest = max(pub_dates)

        age_hours = (now - earliest).total_seconds() / 3600
        hours_since_last = (now - latest).total_seconds() / 3600
        age_days = max(age_hours / 24, 0.1)

        article_count = story.get("article_count") or len(articles)
        coverage_velocity = round(article_count / age_days, 2) if article_count > 1 else None

        status = _determine_status(age_hours, hours_since_last)

        update_story_metadata(
            story_id,
            first_seen=earliest.isoformat(),
            last_article_at=latest.isoformat(),
            status=status,
            coverage_velocity=coverage_velocity,
        )

        updated += 1
        logger.info(
            "  Story #%d: status=%s, velocity=%s, age=%.1fh, last=%.1fh ago",
            story_id, status, coverage_velocity, age_hours, hours_since_last,
        )

    logger.info("Backfill complete: %d updated, %d skipped", updated, skipped)


if __name__ == "__main__":
    backfill()
