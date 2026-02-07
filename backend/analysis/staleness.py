"""Determine which stories need new or updated analyses.

Called by the generator to decide what to regenerate.
Lightweight — no API calls, just DB reads and math.
"""

import logging
from datetime import datetime, timezone

from db.queries import get_active_stories, get_analysis, get_articles_for_story

logger = logging.getLogger(__name__)


def _analysis_is_stale(story: dict, analysis: dict | None) -> bool:
    """Check if an existing analysis needs regeneration.

    Stale if:
    - analysis is None (doesn't exist)
    - story.article_count > analysis.article_count_at_gen * 1.3
      (30% growth since last generation)
    - analysis.updated_at is older than 12 hours AND
      story.last_updated is more recent than analysis.updated_at
    """
    if analysis is None:
        return True

    # 30% article growth since last generation
    gen_count = analysis.get("article_count_at_gen") or 0
    current_count = story.get("article_count") or 0
    if gen_count > 0 and current_count > gen_count * 1.3:
        return True

    # Older than 12 hours + story has newer updates
    updated_at_raw = analysis.get("updated_at")
    if updated_at_raw:
        if isinstance(updated_at_raw, str):
            updated_at = datetime.fromisoformat(updated_at_raw)
        else:
            updated_at = updated_at_raw
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
        if age_hours > 12:
            story_updated_raw = story.get("last_updated")
            if story_updated_raw:
                if isinstance(story_updated_raw, str):
                    story_updated = datetime.fromisoformat(story_updated_raw)
                else:
                    story_updated = story_updated_raw
                if story_updated.tzinfo is None:
                    story_updated = story_updated.replace(tzinfo=timezone.utc)

                if story_updated > updated_at:
                    return True

    return False


def get_stories_needing_analysis(max_results: int = 10) -> list[int]:
    """Return story IDs that need analysis, ordered by priority.

    Priority:
    1. No analysis exists + impact >= 50
    2. No analysis exists + article_count >= 10
    3. Analysis stale (article count grew >30% since generation)
    4. Analysis older than 12 hours + story has new articles

    Excludes:
    - Stories with < 3 articles (not enough for meaningful analysis)
    - Stories with status "stale" and impact < 20 (dying stories)

    Returns: list of story_ids, max max_results items
    """
    stories = get_active_stories()
    logger.info("Evaluating %d active stories for analysis needs", len(stories))

    no_analysis_high_impact: list[int] = []
    no_analysis_high_coverage: list[int] = []
    stale_analysis: list[int] = []

    MIN_ARTICLES = 3

    for story in stories:
        story_id = story["id"]
        article_count = story.get("article_count") or 0
        impact = story.get("impact_score") or 0.0
        status = story.get("status", "")

        # Exclusions — hard floor on article count
        if article_count < MIN_ARTICLES:
            continue
        # stories.article_count can be wildly stale (e.g. claimed=30, actual=1)
        # Always verify against actual DB to avoid wasting API calls
        actual = len(get_articles_for_story(story_id))
        if actual < MIN_ARTICLES:
            logger.debug(
                "Skipping story #%d: article_count=%d but actual=%d",
                story_id, article_count, actual,
            )
            continue
        if status == "stale" and impact < 20:
            continue

        analysis = get_analysis(story_id)
        stale = _analysis_is_stale(story, analysis)

        if not stale:
            continue

        if analysis is None:
            if impact >= 50:
                no_analysis_high_impact.append(story_id)
            elif article_count >= 10:
                no_analysis_high_coverage.append(story_id)
            else:
                # Has enough articles (>=3) but doesn't meet high thresholds —
                # still needs analysis, treat as lower priority stale
                stale_analysis.append(story_id)
        else:
            stale_analysis.append(story_id)

    # Combine in priority order, deduplicate
    seen: set[int] = set()
    result: list[int] = []
    for sid in no_analysis_high_impact + no_analysis_high_coverage + stale_analysis:
        if sid not in seen:
            seen.add(sid)
            result.append(sid)
        if len(result) >= max_results:
            break

    logger.info(
        "Stories needing analysis: %d (high_impact=%d, high_coverage=%d, stale=%d)",
        len(result),
        len(no_analysis_high_impact),
        len(no_analysis_high_coverage),
        len(stale_analysis),
    )
    return result


if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(name)s | %(message)s")

    ids = get_stories_needing_analysis()
    print(f"\nStories needing analysis: {len(ids)}")
    for sid in ids:
        print(f"  Story #{sid}")

    if not ids:
        print("  (none — all stories are up to date)")
