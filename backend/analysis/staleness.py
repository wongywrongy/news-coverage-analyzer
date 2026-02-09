"""Determine which stories need new or updated analyses.

Called by the generator to decide what to regenerate.
Lightweight — no API calls, just DB reads and math.
"""

import logging
from datetime import datetime, timezone

from config.settings import settings
from config.sources import SOURCE_BIAS
from db.queries import get_active_stories, get_analysis, get_articles_for_story

logger = logging.getLogger(__name__)


def _lean_diversity_score(story_id: int) -> float:
    """Score 0-1 based on how many different political leans cover this story.

    More diverse coverage = better contrasts in analysis.
    Maps source bias labels to three buckets (left/center/right).
    """
    articles = get_articles_for_story(story_id)
    leans: set[str] = set()
    for a in articles:
        domain = a.get("source_domain", "")
        bias_info = SOURCE_BIAS.get(domain)
        label = (bias_info["label"] if bias_info else "").lower()
        if "left" in label:
            leans.add("left")
        if "center" in label:
            leans.add("center")
        if "right" in label:
            leans.add("right")

    # 0 leans = 0, 1 lean = 0.2, 2 leans = 0.6, 3 leans = 1.0
    return {0: 0.0, 1: 0.2, 2: 0.6, 3: 1.0}.get(len(leans), 0.0)


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


def analysis_priority(story: dict) -> float:
    """Compute priority score for a story.

    Returns 0 for stories below significance threshold.
    Higher score = higher priority for analysis.
    """
    sig = story.get("significance_score") or 0
    if sig > 0 and sig < settings.min_significance_score:
        return 0.0

    cat = (story.get("category") or "").strip()
    cat_weight = {
        # Full category names (new format)
        "Politics & Law": 1.0,
        "World & Security": 0.9,
        "Science & Health": 0.8,
        "Economy & Business": 0.6,
        # Legacy uppercase keys (backward compat)
        "POLITICS": 1.0, "LAW": 1.0,
        "WORLD": 0.9, "MILITARY": 0.9,
        "HEALTH": 0.8, "SCIENCE": 0.8,
        "BUSINESS": 0.6, "ECONOMY": 0.6,
    }.get(cat, 0.1)

    diversity = _lean_diversity_score(story["id"])
    impact = (story.get("impact_score") or 0) / 100.0

    # Staleness tier
    analysis = get_analysis(story["id"])
    has_analysis = analysis is not None
    article_count = story.get("article_count") or 0

    if not has_analysis and (story.get("impact_score") or 0) >= 50:
        tier = 0
    elif not has_analysis and article_count >= 10:
        tier = 1
    elif has_analysis:
        tier = 2
    else:
        tier = 3
    staleness = 1.0 - (tier / 3.0)

    return impact * 0.3 + diversity * 0.3 + cat_weight * 0.2 + staleness * 0.2


def get_stories_needing_analysis(max_results: int = 10) -> list[int]:
    """Return story IDs that need analysis, ordered by priority.

    Uses the new priority formula with significance threshold,
    category weight, diversity, impact, and staleness.

    Excludes:
    - Stories with < 3 articles (not enough for meaningful analysis)
    - Stories below significance threshold (if scored)
    - Stories with status "stale" and impact < 20 (dying stories)

    Returns: list of story_ids, max max_results items
    """
    stories = get_active_stories()
    logger.info("Evaluating %d active stories for analysis needs", len(stories))

    MIN_ARTICLES = 3
    candidates: list[tuple[int, float]] = []  # (story_id, priority)

    for story in stories:
        story_id = story["id"]
        article_count = story.get("article_count") or 0
        impact = story.get("impact_score") or 0.0
        status = story.get("status", "")

        # Exclusions — hard floor on article count
        if article_count < MIN_ARTICLES:
            continue
        # Verify actual article count
        actual = len(get_articles_for_story(story_id))
        if actual < MIN_ARTICLES:
            logger.debug(
                "Skipping story #%d: article_count=%d but actual=%d",
                story_id, article_count, actual,
            )
            continue
        if status == "stale" and impact < 20:
            continue

        # Check if analysis is stale
        analysis = get_analysis(story_id)
        if not _analysis_is_stale(story, analysis):
            continue

        # Compute priority
        priority = analysis_priority(story)
        if priority > 0:
            candidates.append((story_id, priority))

    # Sort by priority descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    result = [sid for sid, _ in candidates[:max_results]]

    logger.info("Stories needing analysis: %d candidates, returning top %d",
                len(candidates), len(result))
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
