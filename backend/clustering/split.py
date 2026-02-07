"""Split oversized story clusters into finer-grained sub-stories.

When a story absorbs too many articles (e.g. 367 articles about
"Trump Deportation Policy"), the articles often cover editorially
distinct sub-topics.  This module uses HDBSCAN with *tighter*
parameters to find natural sub-clusters within mega-stories and
split them into separate story rows.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone

import hdbscan
import numpy as np

from db import queries as db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────


def split_oversized_stories(
    max_articles: int = 40,
    min_sub_cluster: int = 3,
) -> dict:
    """Find stories that are too large and sub-cluster them.

    1. Find all active stories where article_count > max_articles
    2. For each: run HDBSCAN on that story's article embeddings
       to find natural sub-clusters within the mega-cluster
    3. If HDBSCAN finds 2+ sub-clusters: split into separate stories
    4. If HDBSCAN finds only 1 cluster: leave it alone

    Returns: {
        "stories_checked": int,
        "stories_split": int,
        "new_stories_created": int,
        "articles_reassigned": int,
        "stories_left_intact": int,
    }
    """
    result = {
        "stories_checked": 0,
        "stories_split": 0,
        "new_stories_created": 0,
        "articles_reassigned": 0,
        "stories_left_intact": 0,
    }

    # 1. Find oversized stories
    all_stories = db.get_active_stories()
    oversized = [
        s for s in all_stories
        if (s.get("article_count") or 0) > max_articles
    ]

    if not oversized:
        logger.info("No oversized stories (threshold=%d).", max_articles)
        return result

    result["stories_checked"] = len(oversized)
    logger.info(
        "Found %d stories exceeding %d articles.",
        len(oversized),
        max_articles,
    )

    # 2. Process each oversized story
    for story in oversized:
        story_id = story["id"]
        articles = db.get_articles_for_story(story_id)

        if not articles:
            logger.warning("Story %d has no articles — skipping split.", story_id)
            continue

        # Filter to articles with embeddings
        valid = [a for a in articles if a.get("embedding")]
        if len(valid) < min_sub_cluster * 2:
            logger.info(
                "Story %d: only %d articles with embeddings, too few to split.",
                story_id,
                len(valid),
            )
            result["stories_left_intact"] += 1
            continue

        # 3. Run sub-clustering
        sub_clusters = _sub_cluster(valid, min_sub_cluster=min_sub_cluster)

        if not sub_clusters:
            logger.info(
                "Story #%d (%d articles) is genuinely one cluster — not splitting.",
                story_id,
                len(articles),
            )
            result["stories_left_intact"] += 1
            continue

        # 4. Split the story
        # Include noise articles (those not in any sub-cluster)
        clustered_ids = {a["id"] for group in sub_clusters for a in group}
        noise_articles = [a for a in valid if a["id"] not in clustered_ids]
        # Also include articles without embeddings — they stay with original
        no_embedding = [a for a in articles if not a.get("embedding")]

        new_ids = _split_story(
            story_id, sub_clusters,
            noise_articles=noise_articles + no_embedding,
        )
        result["stories_split"] += 1
        result["new_stories_created"] += len(new_ids)
        # Articles reassigned = total minus the largest sub-cluster (which stays)
        largest_size = max(len(group) for group in sub_clusters)
        result["articles_reassigned"] += len(valid) - largest_size

        logger.info(
            "Split story #%d (%d articles) into %d sub-stories.",
            story_id,
            len(articles),
            len(sub_clusters),
        )

    logger.info(
        "Split complete: %d checked, %d split, %d new stories, %d reassigned, %d intact.",
        result["stories_checked"],
        result["stories_split"],
        result["new_stories_created"],
        result["articles_reassigned"],
        result["stories_left_intact"],
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _sub_cluster(
    articles: list[dict],
    min_sub_cluster: int = 3,
) -> list[list[dict]]:
    """Run HDBSCAN on articles within a single story to find sub-clusters.

    Uses TIGHTER parameters than the initial discovery clustering:
    - cluster_selection_epsilon: 0.15 (vs 0.3) — pickier about differences
    - cluster_selection_method: 'leaf' (vs 'eom') — more granular clusters

    Returns: list of article groups (each group = one sub-cluster).
    Empty list if only 0-1 clusters found (no split needed).
    """
    embeddings = [a["embedding"] for a in articles]
    matrix = np.array(embeddings, dtype=np.float32)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_sub_cluster,
        min_samples=2,
        metric="euclidean",
        cluster_selection_epsilon=0.15,
        cluster_selection_method="leaf",
    )
    clusterer.fit(matrix)
    labels = clusterer.labels_.tolist()

    # Group articles by cluster label
    groups: dict[int, list[dict]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if label != -1:
            groups[label].append(articles[idx])

    # Need at least 2 clusters for a split to make sense
    if len(groups) < 2:
        return []

    return list(groups.values())


def _split_story(
    original_story_id: int,
    sub_clusters: list[list[dict]],
    noise_articles: list[dict] | None = None,
) -> list[int]:
    """Split a story into multiple new stories.

    1. Keep the original story for the LARGEST sub-cluster
       (preserves the story ID for continuity)
    2. Create NEW stories for each smaller sub-cluster
    3. Reassign articles from smaller sub-clusters to new stories
    4. Recompute metadata for all affected stories
    5. Noise articles stay assigned to the original story

    Returns: list of new story IDs created
    """
    if not sub_clusters:
        return []

    # Sort by size descending — largest stays with original story
    sorted_clusters = sorted(sub_clusters, key=len, reverse=True)
    largest = sorted_clusters[0]
    smaller = sorted_clusters[1:]

    new_story_ids: list[int] = []

    # Create new stories for each smaller sub-cluster
    for cluster_articles in smaller:
        story_data = _build_story_data(cluster_articles)
        new_id = db.insert_story(story_data)
        if new_id is None:
            logger.error("Failed to create sub-story — skipping sub-cluster.")
            continue

        # Reassign articles to the new story
        for article in cluster_articles:
            db.update_article_story(article["id"], new_id)

        new_story_ids.append(new_id)

    # Recompute metadata for the original story (now only has largest cluster + noise)
    _recompute_story_metadata(original_story_id)

    # Recompute metadata for each new story
    for new_id in new_story_ids:
        _recompute_story_metadata(new_id)

    return new_story_ids


def _build_story_data(articles: list[dict]) -> dict:
    """Build a story insert dict from a group of articles."""
    centroid = _compute_centroid([a["embedding"] for a in articles if a.get("embedding")])

    # Timestamps
    pub_dates: list[datetime] = []
    for a in articles:
        pub = a.get("published_at")
        if pub and isinstance(pub, str):
            try:
                pub_dates.append(datetime.fromisoformat(pub))
            except ValueError:
                pass

    first_seen = min(pub_dates).isoformat() if pub_dates else None
    last_updated = max(pub_dates).isoformat() if pub_dates else None

    # Source diversity
    source_domains = {a.get("source_domain", "") for a in articles}
    source_domains.discard("")

    # Bias stats
    bias_scores = [
        a["source_bias_score"]
        for a in articles
        if a.get("source_bias_score") is not None
    ]
    avg_bias = sum(bias_scores) / len(bias_scores) if bias_scores else 0.0
    bias_spread = (max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0

    # Use most-central article title as placeholder topic
    topic = _pick_placeholder_topic(articles)

    return {
        "topic": topic,
        "article_count": len(articles),
        "source_count": len(source_domains),
        "avg_bias_score": round(avg_bias, 3),
        "bias_spread": round(bias_spread, 3),
        "centroid": centroid,
        "active": True,
        "first_seen": first_seen,
        "last_updated": last_updated,
    }


def _compute_centroid(embeddings: list[list[float]]) -> list[float]:
    """Compute L2-normalized mean of embedding vectors."""
    matrix = np.array(embeddings, dtype=np.float64)
    mean = matrix.mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def _pick_placeholder_topic(articles: list[dict]) -> str:
    """Pick the most central article's title as a placeholder topic."""
    valid = [a for a in articles if a.get("embedding")]
    if not valid:
        return "Untitled sub-cluster"

    centroid = _compute_centroid([a["embedding"] for a in valid])
    centroid_arr = np.array(centroid, dtype=np.float64)

    best_idx = 0
    best_dist = float("inf")
    for i, a in enumerate(valid):
        dist = np.linalg.norm(np.array(a["embedding"], dtype=np.float64) - centroid_arr)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    title = valid[best_idx].get("title", "Untitled sub-cluster")
    title = re.sub(r"\s*[\-\|—]\s*[A-Z][\w\s.&']+$", "", title)
    return title.strip() or "Untitled sub-cluster"


def _recompute_story_metadata(story_id: int) -> None:
    """Recompute all derived metadata for a story from its current articles."""
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

    # Recompute centroid
    embeddings = [a["embedding"] for a in articles if a.get("embedding")]
    if embeddings:
        updates["centroid"] = _compute_centroid(embeddings)

    # Bias stats
    bias_scores = [
        a["source_bias_score"]
        for a in articles
        if a.get("source_bias_score") is not None
    ]
    if bias_scores:
        updates["avg_bias_score"] = round(sum(bias_scores) / len(bias_scores), 3)
        updates["bias_spread"] = round(
            (max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0,
            3,
        )

    db.update_story_metadata(story_id, **updates)


# ─────────────────────────────────────────────────────────────────────────────
#  Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    result = split_oversized_stories()
    print(f"\nStories checked:      {result['stories_checked']}")
    print(f"Stories split:        {result['stories_split']}")
    print(f"New stories created:  {result['new_stories_created']}")
    print(f"Articles reassigned:  {result['articles_reassigned']}")
    print(f"Stories left intact:  {result['stories_left_intact']}")
