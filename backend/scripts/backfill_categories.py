"""Backfill categories for existing stories.

Two-pass approach:
1. Keyword matching (free, instant) — classifies based on topic text
2. AI classification (cheap) — for stories where keywords didn't match well

Usage:
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_categories
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_categories --keywords-only
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_categories --ai-only
"""

import logging
import sys

from clustering.label import (
    categorize_stories_by_keywords,
    label_stories,
    _validate_category,
)
from db.queries import get_active_stories

logging.basicConfig(level="INFO", format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def backfill(keywords_only: bool = False, ai_only: bool = False):
    all_stories = get_active_stories()
    uncategorized = [
        s for s in all_stories
        if _validate_category((s.get("category") or "").strip()) is None
    ]
    logger.info(
        "%d active stories, %d need categories",
        len(all_stories), len(uncategorized),
    )

    if not uncategorized:
        logger.info("All stories already have valid categories.")
        return

    # Pass 1: keyword matching
    if not ai_only:
        logger.info("Pass 1: Keyword classification...")
        kw_result = categorize_stories_by_keywords(
            story_ids=[s["id"] for s in uncategorized],
        )
        logger.info(
            "  Keyword-classified: %d, skipped: %d",
            kw_result["categorized"], kw_result["skipped"],
        )

    if keywords_only:
        logger.info("Done (keywords only).")
        return

    # Pass 2: AI classification for remaining uncategorized
    # Re-fetch to see which are still uncategorized
    all_stories = get_active_stories()
    still_uncategorized = [
        s for s in all_stories
        if _validate_category((s.get("category") or "").strip()) is None
    ]

    if still_uncategorized:
        logger.info("Pass 2: AI classification for %d remaining stories...", len(still_uncategorized))
        ai_result = label_stories(story_ids=[s["id"] for s in still_uncategorized])
        logger.info(
            "  AI labeled: %d, categorized: %d, errors: %d",
            ai_result["labeled"], ai_result["categorized"], ai_result["errors"],
        )
    else:
        logger.info("All stories categorized by keywords, no AI pass needed.")

    # Summary
    all_stories = get_active_stories()
    by_cat: dict[str, int] = {}
    for s in all_stories:
        cat = (s.get("category") or "uncategorized").strip() or "uncategorized"
        by_cat[cat] = by_cat.get(cat, 0) + 1

    logger.info("Final category distribution:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        logger.info("  %-25s %d stories", cat, count)


if __name__ == "__main__":
    kw_only = "--keywords-only" in sys.argv
    ai_only = "--ai-only" in sys.argv
    backfill(keywords_only=kw_only, ai_only=ai_only)
