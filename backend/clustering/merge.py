"""Merge story clusters whose centroids have converged over time.

Two stories may be created in different ingestion cycles but converge
as more articles arrive.  This module detects those near-duplicates
and folds the smaller cluster into the larger one.
"""

import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from db.queries import (
    deactivate_story,
    get_articles_for_story,
    get_story_centroids,
    update_article_story,
    update_story_metadata,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════


def merge_similar_stories(similarity_threshold: float = 0.78) -> dict:
    """Find and merge story pairs whose centroids are too similar.

    1. Fetch all active story centroids
    2. Compute pairwise cosine similarity matrix
    3. For each pair above threshold: merge smaller into larger
    4. Return summary

    Returns: {
        "pairs_checked": int,
        "merges_performed": int,
        "stories_absorbed": list[int]  # IDs of stories that were merged away
    }
    """
    stories = get_story_centroids()  # [{id, centroid}, ...]

    result: dict = {
        "pairs_checked": 0,
        "merges_performed": 0,
        "stories_absorbed": [],
    }

    if len(stories) < 2:
        logger.info("Fewer than 2 active stories -- nothing to merge")
        return result

    # Build N×384 centroid matrix
    story_ids = [s["id"] for s in stories]
    centroids = np.array([s["centroid"] for s in stories])

    # Pairwise cosine similarity (N×N, symmetric, diagonal = 1.0)
    sim_matrix = cosine_similarity(centroids)

    # Collect upper-triangle pairs above threshold
    n = len(story_ids)
    merge_candidates: list[tuple[int, int, float]] = []

    for i in range(n):
        for j in range(i + 1, n):
            result["pairs_checked"] += 1
            if sim_matrix[i, j] > similarity_threshold:
                merge_candidates.append((i, j, float(sim_matrix[i, j])))

    # Most similar first — greedily merge the tightest pairs
    merge_candidates.sort(key=lambda x: x[2], reverse=True)

    logger.info(
        "Checked %d pairs, found %d above threshold %.2f",
        result["pairs_checked"],
        len(merge_candidates),
        similarity_threshold,
    )

    # Track absorbed stories so we never merge an already-absorbed story
    absorbed: set[int] = set()

    for i, j, sim in merge_candidates:
        id_a = story_ids[i]
        id_b = story_ids[j]

        # Skip if either side was already absorbed in this run
        if id_a in absorbed or id_b in absorbed:
            continue

        # Keep the story with more articles; absorb the smaller one
        articles_a = get_articles_for_story(id_a)
        articles_b = get_articles_for_story(id_b)

        if len(articles_a) >= len(articles_b):
            keep_id, absorb_id = id_a, id_b
        else:
            keep_id, absorb_id = id_b, id_a

        logger.info(
            "Merging story #%d (%d articles) into #%d (%d articles) -- similarity %.3f",
            absorb_id,
            min(len(articles_a), len(articles_b)),
            keep_id,
            max(len(articles_a), len(articles_b)),
            sim,
        )

        _merge_stories(keep_id, absorb_id)

        absorbed.add(absorb_id)
        result["merges_performed"] += 1
        result["stories_absorbed"].append(absorb_id)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _merge_stories(keep_id: int, absorb_id: int) -> None:
    """Merge absorb_id story into keep_id story.

    1. Reassign all articles from absorb_id to keep_id
    2. Recompute keep_id's metadata (article_count, source_count,
       centroid, first_seen)
    3. Deactivate absorb_id
    """
    # --- 1. Reassign articles ---
    articles_to_move = get_articles_for_story(absorb_id)
    for article in articles_to_move:
        update_article_story(article["id"], keep_id)

    logger.info(
        "Reassigned %d articles from story #%d -> #%d",
        len(articles_to_move),
        absorb_id,
        keep_id,
    )

    # --- 2. Recompute metadata for the surviving story ---
    all_articles = get_articles_for_story(keep_id)

    article_count = len(all_articles)
    source_count = len({a.get("source_domain", "") for a in all_articles})

    # New centroid = mean of all article embeddings
    embeddings = [a["embedding"] for a in all_articles if a.get("embedding")]
    centroid = np.mean(embeddings, axis=0).tolist() if embeddings else None

    # first_seen = earliest published_at across all articles
    pub_dates = [a["published_at"] for a in all_articles if a.get("published_at")]
    first_seen = min(pub_dates) if pub_dates else None

    metadata: dict = {
        "article_count": article_count,
        "source_count": source_count,
    }
    if centroid is not None:
        metadata["centroid"] = centroid
    if first_seen is not None:
        metadata["first_seen"] = first_seen

    update_story_metadata(keep_id, **metadata)

    # --- 3. Deactivate the absorbed story ---
    deactivate_story(absorb_id)

    logger.info("Merged story #%d into #%d", absorb_id, keep_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  Standalone test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    )

    result = merge_similar_stories()
    print(f"\nPairs checked: {result['pairs_checked']}")
    print(f"Merges: {result['merges_performed']}")
    for sid in result["stories_absorbed"]:
        print(f"  Story #{sid} absorbed")
