"""Discover new story clusters from unassigned articles using HDBSCAN.

Runs AFTER the assignment step — only looks at articles that didn't
match any existing story.  Groups them into new clusters, creates Story
rows, and assigns the articles.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime

import hdbscan
import numpy as np

from db.queries import (
    get_unassigned_articles,
    insert_story,
    update_article_story,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────


def discover_new_clusters(
    min_cluster_size: int = 3,
    max_article_age_hours: int = 72,
) -> dict:
    """Discover new story clusters from unassigned articles.

    1. Fetch unassigned articles (story_id IS NULL)
    2. Filter to articles from last *max_article_age_hours*
       (don't cluster very old orphan articles)
    3. Run HDBSCAN on their embeddings
    4. For each valid cluster: create a Story, assign articles
    5. Return summary stats

    Returns:
        {
            "clusters_found": int,
            "articles_clustered": int,
            "articles_noise": int,
            "new_stories": [{story_id, topic, article_count}],
        }
    """
    result = {
        "clusters_found": 0,
        "articles_clustered": 0,
        "articles_noise": 0,
        "new_stories": [],
    }

    # 1. Fetch unassigned articles ----------------------------------------
    articles = get_unassigned_articles()
    if not articles:
        logger.info("No unassigned articles found — nothing to cluster.")
        return result

    # 2. Age filter -------------------------------------------------------
    cutoff = datetime.now(UTC).timestamp() - (max_article_age_hours * 3600)
    recent: list[dict] = []
    for art in articles:
        pub = art.get("published_at")
        if pub is None:
            continue
        # published_at comes from Supabase as ISO-8601 string
        if isinstance(pub, str):
            try:
                ts = datetime.fromisoformat(pub).timestamp()
            except ValueError:
                continue
        else:
            ts = pub.timestamp() if hasattr(pub, "timestamp") else 0
        if ts >= cutoff:
            recent.append(art)

    skipped = len(articles) - len(recent)
    if skipped:
        logger.info(
            "Filtered out %d articles older than %dh — %d remain.",
            skipped,
            max_article_age_hours,
            len(recent),
        )

    if len(recent) < min_cluster_size:
        logger.info(
            "Only %d recent unassigned articles (need %d) — skipping clustering.",
            len(recent),
            min_cluster_size,
        )
        return result

    # 3. Extract embeddings -----------------------------------------------
    # Skip articles that have no embedding (shouldn't happen, but be safe)
    valid: list[dict] = [a for a in recent if a.get("embedding")]
    if len(valid) < min_cluster_size:
        logger.info("Only %d articles with embeddings — skipping.", len(valid))
        return result

    embeddings = [a["embedding"] for a in valid]

    # 4. Run HDBSCAN ------------------------------------------------------
    labels = _run_hdbscan(embeddings, min_cluster_size=min_cluster_size)

    # 5. Group by label ---------------------------------------------------
    clusters: dict[int, list[int]] = defaultdict(list)
    noise_count = 0
    for idx, label in enumerate(labels):
        if label == -1:
            noise_count += 1
        else:
            clusters[label].append(idx)

    result["articles_noise"] = noise_count

    if not clusters:
        logger.info(
            "HDBSCAN found 0 clusters from %d articles (%d noise). "
            "Articles may be too diverse or min_cluster_size=%d too high.",
            len(valid),
            noise_count,
            min_cluster_size,
        )
        return result

    # 6. Create stories for each cluster ----------------------------------
    articles_clustered = 0

    for label, indices in sorted(clusters.items()):
        cluster_articles = [valid[i] for i in indices]
        cluster_embeddings = [embeddings[i] for i in indices]

        if len(cluster_articles) < min_cluster_size:
            # Shouldn't happen with HDBSCAN but guard anyway
            continue

        centroid = _compute_centroid(cluster_embeddings)
        topic = _generate_placeholder_topic(cluster_articles)

        # Timestamps
        pub_dates = []
        for a in cluster_articles:
            pub = a.get("published_at")
            if pub and isinstance(pub, str):
                try:
                    pub_dates.append(datetime.fromisoformat(pub))
                except ValueError:
                    pass
        first_seen = min(pub_dates).isoformat() if pub_dates else None
        last_updated = max(pub_dates).isoformat() if pub_dates else None

        # Source diversity
        source_domains = {a.get("source_domain", "") for a in cluster_articles}
        source_domains.discard("")
        source_count = len(source_domains)

        # Bias stats
        bias_scores = [
            a["source_bias_score"]
            for a in cluster_articles
            if a.get("source_bias_score") is not None
        ]
        avg_bias = sum(bias_scores) / len(bias_scores) if bias_scores else 0.0
        bias_spread = (max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0

        story_data = {
            "topic": topic,
            "article_count": len(cluster_articles),
            "source_count": source_count,
            "avg_bias_score": round(avg_bias, 3),
            "bias_spread": round(bias_spread, 3),
            "centroid": centroid,
            "active": True,
            "first_seen": first_seen,
            "last_updated": last_updated,
        }

        story_id = insert_story(story_data)
        if story_id is None:
            logger.error("Failed to create story for cluster %d — skipping.", label)
            continue

        # Assign articles to the new story
        for a in cluster_articles:
            update_article_story(a["id"], story_id)

        articles_clustered += len(cluster_articles)
        result["new_stories"].append({
            "story_id": story_id,
            "topic": topic,
            "article_count": len(cluster_articles),
        })

    result["clusters_found"] = len(result["new_stories"])
    result["articles_clustered"] = articles_clustered

    logger.info(
        "Discovered %d new clusters from %d unassigned articles. %d noise.",
        result["clusters_found"],
        len(valid),
        noise_count,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _run_hdbscan(
    embeddings: list[list[float]],
    min_cluster_size: int = 3,
) -> list[int]:
    """Run HDBSCAN clustering on embedding matrix.

    Args:
        embeddings: list of 384-dim float vectors.
        min_cluster_size: minimum articles to form a cluster.

    Returns:
        list of cluster labels (-1 = noise).
    """
    matrix = np.array(embeddings, dtype=np.float32)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric="euclidean",
        cluster_selection_epsilon=0.3,
        cluster_selection_method="eom",
    )
    clusterer.fit(matrix)
    return clusterer.labels_.tolist()


def _compute_centroid(embeddings: list[list[float]]) -> list[float]:
    """Compute L2-normalized mean of embedding vectors."""
    matrix = np.array(embeddings, dtype=np.float64)
    mean = matrix.mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def _generate_placeholder_topic(articles: list[dict]) -> str:
    """Pick the title of the most central article as placeholder topic.

    Finds the article whose embedding is closest to the centroid,
    then strips common source suffixes (" - CNN", " | Reuters", etc.).

    This is a PLACEHOLDER.  The label.py module will replace it
    with a Claude-generated label later.
    """
    embeddings = [a["embedding"] for a in articles]
    centroid = _compute_centroid(embeddings)
    centroid_arr = np.array(centroid, dtype=np.float64)

    best_idx = 0
    best_dist = float("inf")
    for i, emb in enumerate(embeddings):
        dist = np.linalg.norm(np.array(emb, dtype=np.float64) - centroid_arr)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    title = articles[best_idx].get("title", "Untitled cluster")
    # Strip common source suffixes:  " - CNN", " | Reuters", " — AP News"
    title = re.sub(r"\s*[\-\|—]\s*[A-Z][\w\s.&']+$", "", title)
    return title.strip() or "Untitled cluster"


# ─────────────────────────────────────────────────────────────────────────────
#  Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = discover_new_clusters()
    print(f"\nClusters found:     {result['clusters_found']}")
    print(f"Articles clustered: {result['articles_clustered']}")
    print(f"Noise points:       {result['articles_noise']}")
    for s in result["new_stories"]:
        print(f"  Story #{s['story_id']}: {s['topic']} ({s['article_count']} articles)")
