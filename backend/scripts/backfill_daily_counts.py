"""One-time backfill of story_daily_counts from existing articles.

Groups all assigned articles by (story_id, DATE(published_at)) and
populates the story_daily_counts table.  Safe to run repeatedly —
uses recalculate_daily_counts which deletes + re-inserts per story.

Usage:
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_daily_counts
"""

from __future__ import annotations

import logging

from db.queries import get_active_stories, recalculate_daily_counts

logging.basicConfig(level="INFO", format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def backfill():
    stories = get_active_stories()
    logger.info("Backfilling daily counts for %d active stories", len(stories))

    updated = 0
    skipped = 0

    for story in stories:
        story_id = story["id"]
        rows_written = recalculate_daily_counts(story_id)

        if rows_written > 0:
            updated += 1
            logger.info("  Story #%d: %d date rows", story_id, rows_written)
        else:
            skipped += 1

    logger.info("Backfill complete: %d stories updated, %d skipped (no articles)", updated, skipped)


if __name__ == "__main__":
    backfill()
