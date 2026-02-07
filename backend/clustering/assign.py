"""Assign unassigned articles to existing story clusters.

This is the fast path in every clustering cycle — most new articles
belong to stories we already know about. Articles that don't match
any existing story are left unassigned for the discovery step.
"""

import logging
import math

from db import queries as db

logger = logging.getLogger(__name__)


def assign_articles_to_stories(
    similarity_threshold: float = 0.72,
) -> dict:
    """Assign unassigned articles to existing stories by embedding similarity.

    For each article where story_id IS NULL:
      1. Query pgvector for nearest story centroid
      2. If similarity >= threshold, assign article to that story
      3. Update story metadata (article_count, source_count,
         last_updated, centroid recomputation)

    Returns: {
        "assigned": int,       # articles assigned to existing stories
        "unassigned": int,     # articles still without a story
        "stories_updated": int # stories that received new articles
    }
    """
    articles = db.get_unassigned_articles()
    if not articles:
        logger.info("No unassigned articles to process.")
        return {"assigned": 0, "unassigned": 0, "stories_updated": 0}

    # If no active stories exist, nothing to assign to
    active_stories = db.get_active_stories()
    if not active_stories:
        logger.info(
            "No active stories yet. All %d articles remain unassigned.",
            len(articles),
        )
        return {"assigned": 0, "unassigned": len(articles), "stories_updated": 0}

    assigned = 0
    updated_stories: set[int] = set()

    for article in articles:
        embedding = article.get("embedding")
        if not embedding:
            logger.warning(
                "Article id=%s has no embedding — skipping.", article.get("id")
            )
            continue

        match = db.find_nearest_story(embedding, similarity_threshold)
        if match is None:
            continue

        story_id, similarity = match

        db.update_article_story(article["id"], story_id)
        assigned += 1
        updated_stories.add(story_id)

    # Batch-update metadata for each story that received new articles
    for story_id in updated_stories:
        _update_story_after_assignment(story_id)

    unassigned = len(articles) - assigned

    logger.info(
        "Assigned %d articles to %d existing stories. %d remain unassigned.",
        assigned,
        len(updated_stories),
        unassigned,
    )

    return {
        "assigned": assigned,
        "unassigned": unassigned,
        "stories_updated": len(updated_stories),
    }


def _recompute_centroid(story_id: int) -> list[float]:
    """Recompute story centroid as normalized mean of all article embeddings.

    Fetch all articles for the story, average their embeddings,
    L2-normalize the result. Update the story's centroid in DB.
    Returns the new centroid.
    """
    articles = db.get_articles_for_story(story_id)
    embeddings = [a["embedding"] for a in articles if a.get("embedding")]

    if not embeddings:
        logger.warning("Story %d has no articles with embeddings.", story_id)
        return []

    dim = len(embeddings[0])
    centroid = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            centroid[i] += emb[i]

    n = len(embeddings)
    centroid = [v / n for v in centroid]

    # L2-normalize
    norm = math.sqrt(sum(v * v for v in centroid))
    if norm > 0:
        centroid = [v / norm for v in centroid]

    db.update_story_metadata(story_id, centroid=centroid)
    return centroid


def _update_story_after_assignment(story_id: int) -> None:
    """Update story metadata after new articles are assigned.

    Fetches ALL articles for the story and recomputes:
    - article_count (total articles in story)
    - source_count (distinct source_domains)
    - first_seen (earliest published_at)
    - centroid (normalized mean of embeddings)
    - last_updated (set automatically by update_story_metadata)
    """
    articles = db.get_articles_for_story(story_id)
    if not articles:
        return

    source_domains = {a["source_domain"] for a in articles if a.get("source_domain")}
    published_dates = [a["published_at"] for a in articles if a.get("published_at")]

    updates: dict = {
        "article_count": len(articles),
        "source_count": len(source_domains),
    }

    if published_dates:
        updates["first_seen"] = min(published_dates)

    db.update_story_metadata(story_id, **updates)
    _recompute_centroid(story_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  __main__ — standalone test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    result = assign_articles_to_stories()
    print(f"\nAssigned:        {result['assigned']}")
    print(f"Still unassigned: {result['unassigned']}")
    print(f"Stories updated:  {result['stories_updated']}")
