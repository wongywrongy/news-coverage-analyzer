# ClearSignal Backend — Current State (2026-02-06)

## Architecture Overview

```
INGEST → CLUSTER → SCORE

Clustering: assign → discover → split → label → merge
Scoring:    impact → handle outliers → attention → sentiment → timeline → gaps
```

Entry point: `python -m pipeline.main --once`

## Database

- Supabase (Postgres + pgvector)
- ~1152 articles with embeddings
- ~119 active stories with scores
- Stories table columns: id, topic, category, impact_score, attention_score,
  article_count, source_count, avg_bias_score, bias_spread, centroid (vector),
  active, first_seen, last_updated, created_at, impact_scored_at, scored_at_article_count,
  population_affected, category, peak_date, status, trend (jsonb),
  sentiment_left, sentiment_center, sentiment_right
- Articles table: id, url, title, description, body, source_name, source_domain,
  source_bias, source_bias_score, author, published_at, image_url, embedding (vector),
  story_id (FK), sentiment

## Latest Run Output

```
Impact scores computed:     60
Outlier articles flagged:   228
Attention scores computed:  119
Sentiment analyzed:         119
Timelines updated:          119

Buried stories:             21
Overcovered stories:        24
Balanced stories:           74

BURIED (underreported):
  "The assassination of Mr Lincoln" — impact: 95, attention: 35.4, gap: +59.6
  "EU agrees €90B lifeline for cash-strapped Ukraine" — impact: 78, attention: 30.7, gap: +47.3

OVERCOVERED (overreported):
  "US man shares clever AirTag trick" — impact: 12, attention: 77.2, gap: -65.2
  "AI, weight" — impact: 12, attention: 70.3, gap: -58.3
```

## Known Issues

1. **228 outliers from 60 stories** (~3.8 per story) — Haiku may be over-flagging
2. Some story topics are low quality (e.g. "AI, weight") — labeler needs tuning

---

## File: db/queries.py

```python
"""
Database query functions — the ONLY module that touches Supabase tables.

All functions are stateless: no caching, no side-effects beyond the DB.
Every function gets its client via get_client(), logs errors, and uses
typed arguments / return values.

Groups: ARTICLES, STORIES, ANALYSES, VECTORS
"""

import json
import logging
from datetime import datetime, timezone

from db.client import get_client

logger = logging.getLogger(__name__)


def _parse_embeddings(rows: list[dict]) -> list[dict]:
    """Convert embedding fields from JSON strings to list[float] in-place.

    pgvector columns are returned as JSON-encoded strings by Supabase.
    """
    for row in rows:
        emb = row.get("embedding")
        if isinstance(emb, str):
            try:
                row["embedding"] = json.loads(emb)
            except (json.JSONDecodeError, ValueError):
                row["embedding"] = None
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  ARTICLES
# ═══════════════════════════════════════════════════════════════════════════════


def insert_articles(articles: list[dict]) -> int:
    """Bulk-insert articles. Returns count of rows actually inserted."""
    if not articles:
        return 0
    client = get_client()
    inserted = 0
    try:
        result = (
            client.table("articles")
            .upsert(articles, on_conflict="url", ignore_duplicates=True)
            .execute()
        )
        inserted = len(result.data) if result.data else 0
        logger.info("Inserted %d / %d articles", inserted, len(articles))
    except Exception as exc:
        logger.error("insert_articles failed: %s", exc)
    return inserted


def get_existing_urls(urls: list[str]) -> set[str]:
    """Return the subset of urls that already exist in the articles table."""
    if not urls:
        return set()
    client = get_client()
    _BATCH = 50
    found: set[str] = set()
    for i in range(0, len(urls), _BATCH):
        batch = urls[i : i + _BATCH]
        try:
            result = (
                client.table("articles")
                .select("url")
                .in_("url", batch)
                .execute()
            )
            found.update(row["url"] for row in result.data)
        except Exception as exc:
            logger.error("get_existing_urls batch %d failed: %s", i // _BATCH, exc)
    return found


def get_unassigned_articles() -> list[dict]:
    """Return articles not yet assigned to any story (story_id IS NULL)."""
    client = get_client()
    try:
        result = (
            client.table("articles")
            .select("*")
            .is_("story_id", "null")
            .order("published_at", desc=True)
            .execute()
        )
        return _parse_embeddings(result.data or [])
    except Exception as exc:
        logger.error("get_unassigned_articles failed: %s", exc)
        return []


def get_articles_for_story(story_id: int) -> list[dict]:
    """Return all articles belonging to a given story."""
    client = get_client()
    try:
        result = (
            client.table("articles")
            .select("*")
            .eq("story_id", story_id)
            .order("published_at", desc=True)
            .execute()
        )
        return _parse_embeddings(result.data or [])
    except Exception as exc:
        logger.error("get_articles_for_story(%d) failed: %s", story_id, exc)
        return []


def update_article_story(article_id: int, story_id: int | None) -> None:
    """Assign an article to a story, or unassign it (story_id=None)."""
    client = get_client()
    try:
        client.table("articles").update({"story_id": story_id}).eq("id", article_id).execute()
    except Exception as exc:
        logger.error("update_article_story(%d, %d) failed: %s", article_id, story_id, exc)


def update_article_sentiment(article_id: int, sentiment: float) -> None:
    """Set the sentiment score for an article."""
    client = get_client()
    try:
        client.table("articles").update({"sentiment": sentiment}).eq("id", article_id).execute()
    except Exception as exc:
        logger.error("update_article_sentiment(%d) failed: %s", article_id, exc)


def get_articles_without_embeddings(limit: int | None = None) -> list[dict]:
    """Return articles where the embedding column IS NULL."""
    client = get_client()
    try:
        query = (
            client.table("articles")
            .select("id, title, description")
            .is_("embedding", "null")
            .order("id")
        )
        if limit is not None:
            query = query.limit(limit)
        result = query.execute()
        return result.data or []
    except Exception as exc:
        logger.error("get_articles_without_embeddings failed: %s", exc)
        return []


def update_article_embedding(article_id: int, embedding: list[float]) -> bool:
    """Set the embedding vector for a single article."""
    client = get_client()
    try:
        client.table("articles").update(
            {"embedding": embedding}
        ).eq("id", article_id).execute()
        return True
    except Exception as exc:
        logger.error("update_article_embedding(%d) failed: %s", article_id, exc)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  STORIES
# ═══════════════════════════════════════════════════════════════════════════════


def insert_story(data: dict) -> int | None:
    """Insert a new story. Returns the new story id, or None on failure."""
    client = get_client()
    try:
        result = (
            client.table("stories")
            .insert(data)
            .execute()
        )
        if result.data:
            new_id = result.data[0]["id"]
            logger.info("Created story id=%d topic=%s", new_id, data.get("topic", ""))
            return new_id
        return None
    except Exception as exc:
        logger.error("insert_story failed: %s", exc)
        return None


def get_active_stories() -> list[dict]:
    """Return all stories where active = TRUE, ordered by impact descending."""
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select("*")
            .eq("active", True)
            .order("impact_score", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_active_stories failed: %s", exc)
        return []


def get_story_with_articles(story_id: int) -> dict | None:
    """Return a story dict with an embedded 'articles' list, or None."""
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select("*, articles(*)")
            .eq("id", story_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as exc:
        logger.error("get_story_with_articles(%d) failed: %s", story_id, exc)
        return None


def update_story_scores(story_id: int, impact: float, attention: float) -> None:
    """Update the impact and attention scores for a story."""
    client = get_client()
    try:
        client.table("stories").update({
            "impact_score": impact,
            "attention_score": attention,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }).eq("id", story_id).execute()
    except Exception as exc:
        logger.error("update_story_scores(%d) failed: %s", story_id, exc)


def update_story_metadata(story_id: int, **kwargs: object) -> None:
    """Update arbitrary fields on a story row."""
    if not kwargs:
        return
    kwargs["last_updated"] = datetime.now(timezone.utc).isoformat()
    client = get_client()
    try:
        client.table("stories").update(kwargs).eq("id", story_id).execute()
    except Exception as exc:
        logger.error("update_story_metadata(%d) failed: %s", story_id, exc)


def deactivate_story(story_id: int) -> None:
    """Mark a story as inactive (soft-delete)."""
    client = get_client()
    try:
        client.table("stories").update({"active": False}).eq("id", story_id).execute()
        logger.info("Deactivated story id=%d", story_id)
    except Exception as exc:
        logger.error("deactivate_story(%d) failed: %s", story_id, exc)


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYSES
# ═══════════════════════════════════════════════════════════════════════════════


def upsert_analysis(data: dict) -> None:
    """Insert or update an analysis keyed by story_id."""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    client = get_client()
    try:
        client.table("analyses").upsert(data, on_conflict="story_id").execute()
        logger.info("Upserted analysis for story_id=%s", data.get("story_id"))
    except Exception as exc:
        logger.error("upsert_analysis failed: %s", exc)


def get_analysis(story_id: int) -> dict | None:
    """Return the analysis for a story, or None if it doesn't exist."""
    client = get_client()
    try:
        result = (
            client.table("analyses")
            .select("*")
            .eq("story_id", story_id)
            .maybe_single()
            .execute()
        )
        return result.data
    except Exception as exc:
        logger.error("get_analysis(%d) failed: %s", story_id, exc)
        return None


def get_stale_analyses(threshold_hours: float) -> list[int]:
    """Return story_ids whose analysis is older than threshold_hours."""
    client = get_client()
    try:
        cutoff = datetime.now(timezone.utc).timestamp() - (threshold_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        result = (
            client.table("analyses")
            .select("story_id")
            .lt("updated_at", cutoff_iso)
            .execute()
        )
        return [row["story_id"] for row in (result.data or [])]
    except Exception as exc:
        logger.error("get_stale_analyses failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  VECTORS
# ═══════════════════════════════════════════════════════════════════════════════


def find_nearest_story(
    embedding: list[float], threshold: float = 0.82
) -> tuple[int, float] | None:
    """Find the active story whose centroid is closest to embedding."""
    client = get_client()
    try:
        result = client.rpc(
            "match_story_centroid",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": 1,
            },
        ).execute()
        if result.data:
            row = result.data[0]
            return (row["id"], row["similarity"])
        return None
    except Exception as exc:
        logger.error("find_nearest_story failed: %s", exc)
        return None


def get_story_centroids() -> list[dict]:
    """Return id and centroid vector for all active stories."""
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select("id, centroid")
            .eq("active", True)
            .not_.is_("centroid", "null")
            .execute()
        )
        rows = result.data or []
        for row in rows:
            c = row.get("centroid")
            if isinstance(c, str):
                try:
                    row["centroid"] = json.loads(c)
                except (json.JSONDecodeError, ValueError):
                    row["centroid"] = None
        return [r for r in rows if r.get("centroid")]
    except Exception as exc:
        logger.error("get_story_centroids failed: %s", exc)
        return []
```

---

## File: models/schemas.py

```python
"""ClearSignal shared data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawArticle(BaseModel):
    url: str
    title: str
    description: str = ""
    body: str = ""
    source_name: str
    author: str = ""
    published_at: datetime | None = None
    image_url: str = ""
    raw_source: dict[str, Any] = Field(default_factory=dict)


class Article(BaseModel):
    url: str
    title: str
    description: str = ""
    body: str = ""
    source_name: str
    author: str = ""
    published_at: datetime | None = None
    image_url: str = ""
    raw_source: dict[str, Any] = Field(default_factory=dict)
    source_domain: str = ""
    source_bias: str = ""
    source_bias_score: float = 0.0
    embedding: list[float] = Field(default_factory=list)
    sentiment: float = 0.0


class Story(BaseModel):
    id: int | None = None
    topic: str = ""
    category: str = ""
    impact_score: float = 0.0
    attention_score: float = 0.0
    article_count: int = 0
    source_count: int = 0
    avg_bias_score: float = 0.0
    bias_spread: float = 0.0
    centroid: list[float] = Field(default_factory=list)
    active: bool = True
    first_seen: datetime | None = None
    last_updated: datetime | None = None
    created_at: datetime | None = None


class Analysis(BaseModel):
    story_id: int
    headline: str = ""
    dateline: str = ""
    lede: str = ""
    context: str = ""
    contrasts: str = ""
    facts: str = ""
    bottom_line: str = ""
    coverage_note: str = ""


class IngestionResult(BaseModel):
    total_fetched: int = 0
    duplicates_skipped: int = 0
    new_stored: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    per_source: dict[str, dict[str, int]] = Field(default_factory=dict)
```

---

## File: clustering/assign.py

```python
"""Assign unassigned articles to existing story clusters.

Fast path — most new articles belong to stories we already know about.
"""

import logging
import math

from db import queries as db

logger = logging.getLogger(__name__)


def assign_articles_to_stories(
    similarity_threshold: float = 0.72,
) -> dict:
    """Assign unassigned articles to existing stories by embedding similarity.

    Returns: {
        "assigned": int,
        "unassigned": int,
        "stories_updated": int
    }
    """
    articles = db.get_unassigned_articles()
    if not articles:
        logger.info("No unassigned articles to process.")
        return {"assigned": 0, "unassigned": 0, "stories_updated": 0}

    active_stories = db.get_active_stories()
    if not active_stories:
        logger.info("No active stories yet. All %d articles remain unassigned.", len(articles))
        return {"assigned": 0, "unassigned": len(articles), "stories_updated": 0}

    assigned = 0
    updated_stories: set[int] = set()

    for article in articles:
        embedding = article.get("embedding")
        if not embedding:
            continue
        match = db.find_nearest_story(embedding, similarity_threshold)
        if match is None:
            continue
        story_id, similarity = match
        db.update_article_story(article["id"], story_id)
        assigned += 1
        updated_stories.add(story_id)

    for story_id in updated_stories:
        _update_story_after_assignment(story_id)

    unassigned = len(articles) - assigned
    logger.info("Assigned %d articles to %d existing stories. %d remain unassigned.",
                assigned, len(updated_stories), unassigned)
    return {"assigned": assigned, "unassigned": unassigned, "stories_updated": len(updated_stories)}


def _recompute_centroid(story_id: int) -> list[float]:
    """Recompute story centroid as normalized mean of all article embeddings."""
    articles = db.get_articles_for_story(story_id)
    embeddings = [a["embedding"] for a in articles if a.get("embedding")]
    if not embeddings:
        return []
    dim = len(embeddings[0])
    centroid = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            centroid[i] += emb[i]
    n = len(embeddings)
    centroid = [v / n for v in centroid]
    norm = math.sqrt(sum(v * v for v in centroid))
    if norm > 0:
        centroid = [v / norm for v in centroid]
    db.update_story_metadata(story_id, centroid=centroid)
    return centroid


def _update_story_after_assignment(story_id: int) -> None:
    """Recompute article_count, source_count, first_seen, centroid."""
    articles = db.get_articles_for_story(story_id)
    if not articles:
        return
    source_domains = {a["source_domain"] for a in articles if a.get("source_domain")}
    published_dates = [a["published_at"] for a in articles if a.get("published_at")]
    updates: dict = {"article_count": len(articles), "source_count": len(source_domains)}
    if published_dates:
        updates["first_seen"] = min(published_dates)
    db.update_story_metadata(story_id, **updates)
    _recompute_centroid(story_id)
```

---

## File: clustering/discover.py

```python
"""Discover new story clusters from unassigned articles using HDBSCAN.

Runs AFTER assignment — only looks at articles that didn't match any existing story.
"""

import logging
import re
from datetime import datetime, timezone
from collections import defaultdict

import hdbscan
import numpy as np

from db.queries import get_unassigned_articles, insert_story, update_article_story

logger = logging.getLogger(__name__)


def discover_new_clusters(
    min_cluster_size: int = 3,
    max_article_age_hours: int = 72,
) -> dict:
    """Discover new story clusters from unassigned articles.

    Returns: {
        "clusters_found": int,
        "articles_clustered": int,
        "articles_noise": int,
        "new_stories": [{story_id, topic, article_count}],
    }
    """
    result = {
        "clusters_found": 0, "articles_clustered": 0,
        "articles_noise": 0, "new_stories": [],
    }

    articles = get_unassigned_articles()
    if not articles:
        return result

    # Age filter
    cutoff = datetime.now(timezone.utc).timestamp() - (max_article_age_hours * 3600)
    recent: list[dict] = []
    for art in articles:
        pub = art.get("published_at")
        if pub is None:
            continue
        if isinstance(pub, str):
            try:
                ts = datetime.fromisoformat(pub).timestamp()
            except ValueError:
                continue
        else:
            ts = pub.timestamp() if hasattr(pub, "timestamp") else 0
        if ts >= cutoff:
            recent.append(art)

    if len(recent) < min_cluster_size:
        return result

    valid = [a for a in recent if a.get("embedding")]
    if len(valid) < min_cluster_size:
        return result

    embeddings = [a["embedding"] for a in valid]
    labels = _run_hdbscan(embeddings, min_cluster_size=min_cluster_size)

    clusters: dict[int, list[int]] = defaultdict(list)
    noise_count = 0
    for idx, label in enumerate(labels):
        if label == -1:
            noise_count += 1
        else:
            clusters[label].append(idx)

    result["articles_noise"] = noise_count
    if not clusters:
        return result

    articles_clustered = 0
    for label, indices in sorted(clusters.items()):
        cluster_articles = [valid[i] for i in indices]
        cluster_embeddings = [embeddings[i] for i in indices]
        if len(cluster_articles) < min_cluster_size:
            continue

        centroid = _compute_centroid(cluster_embeddings)
        topic = _generate_placeholder_topic(cluster_articles)

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

        source_domains = {a.get("source_domain", "") for a in cluster_articles}
        source_domains.discard("")

        bias_scores = [a["source_bias_score"] for a in cluster_articles if a.get("source_bias_score") is not None]
        avg_bias = sum(bias_scores) / len(bias_scores) if bias_scores else 0.0
        bias_spread = (max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0

        story_data = {
            "topic": topic, "article_count": len(cluster_articles),
            "source_count": len(source_domains),
            "avg_bias_score": round(avg_bias, 3), "bias_spread": round(bias_spread, 3),
            "centroid": centroid, "active": True,
            "first_seen": first_seen, "last_updated": last_updated,
        }

        story_id = insert_story(story_data)
        if story_id is None:
            continue

        for a in cluster_articles:
            update_article_story(a["id"], story_id)

        articles_clustered += len(cluster_articles)
        result["new_stories"].append({
            "story_id": story_id, "topic": topic, "article_count": len(cluster_articles),
        })

    result["clusters_found"] = len(result["new_stories"])
    result["articles_clustered"] = articles_clustered
    return result


def _run_hdbscan(embeddings: list[list[float]], min_cluster_size: int = 3) -> list[int]:
    matrix = np.array(embeddings, dtype=np.float32)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size, min_samples=2,
        metric="euclidean", cluster_selection_epsilon=0.3,
        cluster_selection_method="eom",
    )
    clusterer.fit(matrix)
    return clusterer.labels_.tolist()


def _compute_centroid(embeddings: list[list[float]]) -> list[float]:
    matrix = np.array(embeddings, dtype=np.float64)
    mean = matrix.mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def _generate_placeholder_topic(articles: list[dict]) -> str:
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
    title = re.sub(r"\s*[\-\|—]\s*[A-Z][\w\s.&']+$", "", title)
    return title.strip() or "Untitled cluster"
```

---

## File: clustering/split.py

```python
"""Split oversized story clusters into finer-grained sub-stories.

Uses HDBSCAN with tighter parameters to find natural sub-clusters
within mega-stories (>40 articles).
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone

import hdbscan
import numpy as np

from db import queries as db

logger = logging.getLogger(__name__)


def split_oversized_stories(
    max_articles: int = 40,
    min_sub_cluster: int = 3,
) -> dict:
    """Find stories that are too large and sub-cluster them.

    Returns: {
        "stories_checked": int, "stories_split": int,
        "new_stories_created": int, "articles_reassigned": int,
        "stories_left_intact": int,
    }
    """
    result = {
        "stories_checked": 0, "stories_split": 0,
        "new_stories_created": 0, "articles_reassigned": 0,
        "stories_left_intact": 0,
    }

    all_stories = db.get_active_stories()
    oversized = [s for s in all_stories if (s.get("article_count") or 0) > max_articles]
    if not oversized:
        return result

    result["stories_checked"] = len(oversized)

    for story in oversized:
        story_id = story["id"]
        articles = db.get_articles_for_story(story_id)
        if not articles:
            continue

        valid = [a for a in articles if a.get("embedding")]
        if len(valid) < min_sub_cluster * 2:
            result["stories_left_intact"] += 1
            continue

        sub_clusters = _sub_cluster(valid, min_sub_cluster=min_sub_cluster)
        if not sub_clusters:
            result["stories_left_intact"] += 1
            continue

        clustered_ids = {a["id"] for group in sub_clusters for a in group}
        noise_articles = [a for a in valid if a["id"] not in clustered_ids]
        no_embedding = [a for a in articles if not a.get("embedding")]

        new_ids = _split_story(story_id, sub_clusters, noise_articles=noise_articles + no_embedding)
        result["stories_split"] += 1
        result["new_stories_created"] += len(new_ids)
        largest_size = max(len(group) for group in sub_clusters)
        result["articles_reassigned"] += len(valid) - largest_size

    return result


def _sub_cluster(articles: list[dict], min_sub_cluster: int = 3) -> list[list[dict]]:
    """HDBSCAN with tighter params: epsilon=0.15, method='leaf'."""
    embeddings = [a["embedding"] for a in articles]
    matrix = np.array(embeddings, dtype=np.float32)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_sub_cluster, min_samples=2,
        metric="euclidean", cluster_selection_epsilon=0.15,
        cluster_selection_method="leaf",
    )
    clusterer.fit(matrix)
    labels = clusterer.labels_.tolist()
    groups: dict[int, list[dict]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if label != -1:
            groups[label].append(articles[idx])
    if len(groups) < 2:
        return []
    return list(groups.values())


def _split_story(original_story_id, sub_clusters, noise_articles=None) -> list[int]:
    """Keep largest sub-cluster in original story, create new stories for rest."""
    sorted_clusters = sorted(sub_clusters, key=len, reverse=True)
    smaller = sorted_clusters[1:]
    new_story_ids: list[int] = []

    for cluster_articles in smaller:
        story_data = _build_story_data(cluster_articles)
        new_id = db.insert_story(story_data)
        if new_id is None:
            continue
        for article in cluster_articles:
            db.update_article_story(article["id"], new_id)
        new_story_ids.append(new_id)

    _recompute_story_metadata(original_story_id)
    for new_id in new_story_ids:
        _recompute_story_metadata(new_id)

    return new_story_ids


def _build_story_data(articles):
    centroid = _compute_centroid([a["embedding"] for a in articles if a.get("embedding")])
    pub_dates = []
    for a in articles:
        pub = a.get("published_at")
        if pub and isinstance(pub, str):
            try:
                pub_dates.append(datetime.fromisoformat(pub))
            except ValueError:
                pass
    source_domains = {a.get("source_domain", "") for a in articles}
    source_domains.discard("")
    bias_scores = [a["source_bias_score"] for a in articles if a.get("source_bias_score") is not None]
    avg_bias = sum(bias_scores) / len(bias_scores) if bias_scores else 0.0
    bias_spread = (max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0
    topic = _pick_placeholder_topic(articles)
    return {
        "topic": topic, "article_count": len(articles),
        "source_count": len(source_domains),
        "avg_bias_score": round(avg_bias, 3), "bias_spread": round(bias_spread, 3),
        "centroid": centroid, "active": True,
        "first_seen": min(pub_dates).isoformat() if pub_dates else None,
        "last_updated": max(pub_dates).isoformat() if pub_dates else None,
    }


def _compute_centroid(embeddings):
    matrix = np.array(embeddings, dtype=np.float64)
    mean = matrix.mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def _pick_placeholder_topic(articles):
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


def _recompute_story_metadata(story_id):
    articles = db.get_articles_for_story(story_id)
    if not articles:
        return
    source_domains = {a["source_domain"] for a in articles if a.get("source_domain")}
    published_dates = [a["published_at"] for a in articles if a.get("published_at")]
    updates = {"article_count": len(articles), "source_count": len(source_domains)}
    if published_dates:
        updates["first_seen"] = min(published_dates)
    embeddings = [a["embedding"] for a in articles if a.get("embedding")]
    if embeddings:
        updates["centroid"] = _compute_centroid(embeddings)
    bias_scores = [a["source_bias_score"] for a in articles if a.get("source_bias_score") is not None]
    if bias_scores:
        updates["avg_bias_score"] = round(sum(bias_scores) / len(bias_scores), 3)
        updates["bias_spread"] = round((max(bias_scores) - min(bias_scores)) if len(bias_scores) >= 2 else 0.0, 3)
    db.update_story_metadata(story_id, **updates)
```

---

## File: clustering/label.py

```python
"""Generate concise, neutral topic labels for stories using Claude Haiku.

Cost: ~$0.001 per 20 stories.
"""

import logging
import time

from anthropic import Anthropic

from config.settings import settings
from db import queries as db

logger = logging.getLogger(__name__)

_LABEL_PROMPT = """\
You are a wire-service editor writing a topic slug.
Given these headlines about the same story, generate a concise \
3-8 word neutral topic label. No punctuation. No articles (a, an, the).
Just the factual topic.

Examples of good labels:
- Senate Passes Immigration Reform Bill
- SC Measles Outbreak Reaches 900 Cases
- Federal Reserve Holds Interest Rates
- Ukraine Russia Ceasefire Negotiations

Headlines:
{headlines}

Topic label:"""


def _needs_labeling(story: dict) -> bool:
    topic = (story.get("topic") or "").strip()
    if not topic:
        return True
    if " - " in topic or " | " in topic:
        return True
    if len(topic) > 80:
        return True
    if '"' in topic or "\u2018" in topic or "\u2019" in topic:
        return True
    if "..." in topic:
        return True
    if topic[0].islower():
        return True
    return False


def _generate_label(headlines: list[str]) -> str:
    prompt = _LABEL_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines))
    client = Anthropic(api_key=settings.anthropic_api_key)
    last_error = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            label = response.content[0].text.strip().strip("\"'")
            return label
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    raise last_error


def label_stories(story_ids: list[int] | None = None) -> dict:
    """Generate topic labels for stories that need them.

    Returns: {"labeled": int, "skipped": int, "errors": int, "labels": list[dict]}
    """
    result: dict = {"labeled": 0, "skipped": 0, "errors": 0, "labels": []}

    if story_ids is not None:
        all_stories = db.get_active_stories()
        stories = [s for s in all_stories if s.get("id") in set(story_ids)]
    else:
        all_stories = db.get_active_stories()
        stories = [s for s in all_stories if _needs_labeling(s)]
        result["skipped"] = len(all_stories) - len(stories)

    if not stories:
        return result

    for story in stories:
        story_id = story["id"]
        old_topic = story.get("topic") or ""
        try:
            articles = db.get_articles_for_story(story_id)
            if not articles:
                result["skipped"] += 1
                continue
            seen: set[str] = set()
            headlines: list[str] = []
            for a in articles:
                title = (a.get("title") or "").strip()
                if title and title not in seen:
                    seen.add(title)
                    headlines.append(title)
                if len(headlines) >= 15:
                    break
            if not headlines:
                result["skipped"] += 1
                continue
            new_topic = _generate_label(headlines)
            db.update_story_metadata(story_id, topic=new_topic)
            result["labeled"] += 1
            result["labels"].append({"story_id": story_id, "old_topic": old_topic, "new_topic": new_topic})
        except Exception as exc:
            logger.error("Failed to label story %d: %s", story_id, exc)
            result["errors"] += 1

    return result
```

---

## File: clustering/merge.py

```python
"""Merge story clusters whose centroids have converged over time."""

import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from db.queries import (
    deactivate_story, get_articles_for_story, get_story_centroids,
    update_article_story, update_story_metadata,
)

logger = logging.getLogger(__name__)


def merge_similar_stories(similarity_threshold: float = 0.78) -> dict:
    """Find and merge story pairs whose centroids are too similar.

    Returns: {"pairs_checked": int, "merges_performed": int, "stories_absorbed": list[int]}
    """
    stories = get_story_centroids()
    result: dict = {"pairs_checked": 0, "merges_performed": 0, "stories_absorbed": []}

    if len(stories) < 2:
        return result

    story_ids = [s["id"] for s in stories]
    centroids = np.array([s["centroid"] for s in stories])
    sim_matrix = cosine_similarity(centroids)

    n = len(story_ids)
    merge_candidates: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            result["pairs_checked"] += 1
            if sim_matrix[i, j] > similarity_threshold:
                merge_candidates.append((i, j, float(sim_matrix[i, j])))

    merge_candidates.sort(key=lambda x: x[2], reverse=True)
    absorbed: set[int] = set()

    for i, j, sim in merge_candidates:
        id_a, id_b = story_ids[i], story_ids[j]
        if id_a in absorbed or id_b in absorbed:
            continue

        articles_a = get_articles_for_story(id_a)
        articles_b = get_articles_for_story(id_b)

        if len(articles_a) >= len(articles_b):
            keep_id, absorb_id = id_a, id_b
        else:
            keep_id, absorb_id = id_b, id_a

        _merge_stories(keep_id, absorb_id)
        absorbed.add(absorb_id)
        result["merges_performed"] += 1
        result["stories_absorbed"].append(absorb_id)

    return result


def _merge_stories(keep_id: int, absorb_id: int) -> None:
    articles_to_move = get_articles_for_story(absorb_id)
    for article in articles_to_move:
        update_article_story(article["id"], keep_id)

    all_articles = get_articles_for_story(keep_id)
    article_count = len(all_articles)
    source_count = len({a.get("source_domain", "") for a in all_articles})

    embeddings = [a["embedding"] for a in all_articles if a.get("embedding")]
    centroid = np.mean(embeddings, axis=0).tolist() if embeddings else None

    pub_dates = [a["published_at"] for a in all_articles if a.get("published_at")]
    first_seen = min(pub_dates) if pub_dates else None

    metadata: dict = {"article_count": article_count, "source_count": source_count}
    if centroid is not None:
        metadata["centroid"] = centroid
    if first_seen is not None:
        metadata["first_seen"] = first_seen

    update_story_metadata(keep_id, **metadata)
    deactivate_story(absorb_id)
```

---

## File: scoring/impact.py

```python
"""Score real-world impact of news stories using Claude Haiku.

0-100 impact score based on population affected, policy significance,
lasting consequences, geographic scope, and urgency.
Also validates cluster coherence — flags outlier articles.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

from anthropic import Anthropic

from config.settings import settings
from config.sources import SOURCE_BIAS
from db import queries as db

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024
_MAX_HEADLINES = 50
_RESCORE_HOURS = 6.0
_GROWTH_THRESHOLD = 0.20

_SYSTEM_PROMPT = (
    "You are a news analyst for ClearSignal. You have two jobs:\n"
    "1. Rate the real-world IMPACT of a news story\n"
    "2. Check if all headlines actually belong to the same story\n\n"
    "Be objective. Impact means lasting consequences for real people, "
    "NOT how much media coverage it gets."
)

_BIAS_BUCKETS: dict[str, list[str]] = {
    "LEFT / FAR-LEFT": ["far-left", "left"],
    "LEFT-CENTER": ["left-center"],
    "CENTER": ["center"],
    "RIGHT-CENTER": ["right-center"],
    "RIGHT / FAR-RIGHT": ["right", "far-right"],
}


def _get_bias_label(source_name: str) -> str:
    meta = SOURCE_BIAS.get(source_name)
    if meta:
        return meta["label"]
    return "center"


def _bucket_for_label(label: str) -> str:
    for bucket, labels in _BIAS_BUCKETS.items():
        if label in labels:
            return bucket
    return "CENTER"


def _needs_scoring(story: dict) -> bool:
    score = story.get("impact_score")
    if score is None or score == 0:
        return True
    current_count = story.get("article_count") or 0
    scored_count = story.get("scored_at_article_count") or 0
    if scored_count > 0 and current_count > 0:
        growth = (current_count - scored_count) / scored_count
        if growth > _GROWTH_THRESHOLD:
            return True
    last_scored = story.get("impact_scored_at")
    if last_scored and current_count > scored_count:
        if isinstance(last_scored, str):
            try:
                last_scored = datetime.fromisoformat(last_scored)
            except ValueError:
                return True
        if last_scored.tzinfo is None:
            last_scored = last_scored.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - last_scored).total_seconds() / 3600
        if age_hours > _RESCORE_HOURS:
            return True
    return False


def _build_prompt(story: dict, articles: list[dict]) -> str:
    topic = story.get("topic") or "(unknown topic)"
    article_count = story.get("article_count") or len(articles)
    source_count = story.get("source_count") or 0

    display_articles = articles[:_MAX_HEADLINES]
    buckets: dict[str, list[str]] = {b: [] for b in _BIAS_BUCKETS}
    for a in display_articles:
        source = a.get("source_name") or "unknown"
        title = a.get("title") or "(no title)"
        article_id = a.get("id", "?")
        label = _get_bias_label(source)
        bucket = _bucket_for_label(label)
        buckets[bucket].append(f"- [{source}] {title}  (id:{article_id})")

    sections = []
    for bucket_name, lines in buckets.items():
        if lines:
            sections.append(f"{bucket_name}:\n" + "\n".join(lines))

    headlines_block = "\n\n".join(sections) if sections else "(no headlines)"
    truncation_note = ""
    if len(articles) > _MAX_HEADLINES:
        truncation_note = f"\n(Showing {_MAX_HEADLINES} of {len(articles)} headlines)\n"

    return (
        f"STORY: {topic}\n"
        f"ARTICLES ({article_count} from {source_count} sources):\n"
        f"{truncation_note}\n{headlines_block}\n\n"
        "TASK 1 - IMPACT SCORE:\n"
        "Rate 0-100 using this rubric:\n"
        "- Population affected (0-25)\n"
        "- Policy significance (0-25)\n"
        "- Lasting consequences (0-25)\n"
        "- Geographic scope (0-15)\n"
        "- Urgency (0-10)\n\n"
        "TASK 2 - CLUSTER VALIDATION:\n"
        "Flag article IDs that do NOT belong. Only obvious mismatches.\n\n"
        "Respond in JSON only, no other text.\n"
        "Keep reasoning to 1-2 SHORT sentences. Keep outlier reasons under 10 words.\n\n"
        "{\n"
        '  "impact_score": 82,\n'
        '  "population": "All US immigrants with pending cases (~11M)",\n'
        '  "reasoning": "Federal court order directly affects...",\n'
        '  "category": "politics",\n'
        '  "outliers": [\n'
        '    {"article_id": 4521, "reason": "About Nintendo Switch"},\n'
        '    {"article_id": 4587, "reason": "Unrelated trade policy"}\n'
        "  ]\n"
        "}"
    )


def _call_haiku(prompt: str) -> dict | None:
    client = Anthropic(api_key=settings.anthropic_api_key)
    last_error = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=_HAIKU_MODEL, max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            if response.stop_reason == "max_tokens":
                logger.warning("Haiku response truncated, skipping.")
                return None

            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(raw)

            score = parsed.get("impact_score", 0)
            if not isinstance(score, (int, float)):
                score = 0
            parsed["impact_score"] = max(0, min(100, int(score)))
            if not isinstance(parsed.get("outliers"), list):
                parsed["outliers"] = []
            return parsed

        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)

    logger.error("Claude Haiku call failed after 2 attempts: %s", last_error)
    return None


def score_impacts(story_ids=None, force=False) -> dict:
    """Score impact for active stories using Claude Haiku.

    Returns: {
        "scored": int, "skipped": int, "errors": int,
        "outliers_flagged": int, "scores": list[dict],
        "outlier_articles": list[dict]
    }
    """
    result = {
        "scored": 0, "skipped": 0, "errors": 0,
        "outliers_flagged": 0, "scores": [], "outlier_articles": [],
    }

    all_stories = db.get_active_stories()
    if story_ids is not None:
        stories = [s for s in all_stories if s.get("id") in set(story_ids)]
    elif force:
        stories = all_stories
    else:
        stories = [s for s in all_stories if _needs_scoring(s)]
        result["skipped"] = len(all_stories) - len(stories)

    if not stories:
        return result

    for story in stories:
        story_id = story["id"]
        try:
            articles = db.get_articles_for_story(story_id)
            if not articles:
                result["skipped"] += 1
                continue

            parsed = _call_haiku(_build_prompt(story, articles))
            if parsed is None:
                result["errors"] += 1
                continue

            score = parsed["impact_score"]
            population = parsed.get("population", "")
            category = parsed.get("category", "")
            outliers = parsed.get("outliers", [])

            db.update_story_scores(story_id, impact=float(score),
                                   attention=story.get("attention_score") or 0.0)
            meta_update = {
                "impact_scored_at": datetime.now(timezone.utc).isoformat(),
                "scored_at_article_count": story.get("article_count") or len(articles),
                "population_affected": population,
            }
            if category:
                meta_update["category"] = category
            db.update_story_metadata(story_id, **meta_update)

            result["scored"] += 1
            result["scores"].append({"story_id": story_id, "score": score,
                                     "population": population, "reasoning": parsed.get("reasoning", "")})

            article_ids_in_story = {a["id"] for a in articles}
            for outlier in outliers:
                aid = outlier.get("article_id")
                if aid is None or aid not in article_ids_in_story:
                    continue
                result["outlier_articles"].append({
                    "article_id": aid, "story_id": story_id,
                    "reason": outlier.get("reason", ""),
                })
                result["outliers_flagged"] += 1

        except Exception as exc:
            logger.error("Failed to score story %d: %s", story_id, exc)
            result["errors"] += 1

    return result
```

---

## File: scoring/attention.py

```python
"""
Attention scoring — measures HOW MUCH media coverage a story receives.

Components (weights sum to 1.0):
  article_count  0.35   — raw volume
  source_diversity 0.25 — distinct outlets
  bias_breadth   0.20   — spectrum coverage
  velocity       0.10   — articles per hour in last 24h
  recency_boost  0.10   — decays 4 points per hour since last update
"""

import logging
from datetime import datetime, timezone

from db.queries import get_active_stories, get_articles_for_story, update_story_metadata

logger = logging.getLogger(__name__)

W_ARTICLE_COUNT = 0.35
W_SOURCE_DIVERSITY = 0.25
W_BIAS_BREADTH = 0.20
W_VELOCITY = 0.10
W_RECENCY = 0.10

BIAS_CATEGORIES = {"far-left", "left", "left-center", "center", "right-center", "right", "far-right"}


def _percentile_rank(value: float, values: list[float]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return ((below + 0.5 * equal) / n) * 100


def _hours_since(dt: datetime | str | None) -> float | None:
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if isinstance(dt, str):
        dt = dt.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600.0)


def _velocity(articles: list[dict]) -> float:
    now = datetime.now(timezone.utc)
    count = 0
    for a in articles:
        pub = a.get("published_at")
        if pub is None:
            continue
        if isinstance(pub, str):
            pub = pub.replace("Z", "+00:00")
            try:
                pub = datetime.fromisoformat(pub)
            except ValueError:
                continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if (now - pub).total_seconds() <= 86_400:
            count += 1
    return float(count)


def _compute_attention(story, all_stories, articles, velocity_values):
    article_counts = [s.get("article_count", 0) for s in all_stories]
    source_counts = [s.get("source_count", 0) for s in all_stories]

    article_pct = _percentile_rank(story.get("article_count", 0), article_counts)
    source_pct = _percentile_rank(story.get("source_count", 0), source_counts)

    distinct_biases = {a.get("source_bias") for a in articles if a.get("source_bias") in BIAS_CATEGORIES}
    bias_breadth = (len(distinct_biases) / len(BIAS_CATEGORIES)) * 100

    vel = _velocity(articles)
    velocity_pct = _percentile_rank(vel, velocity_values)

    hours = _hours_since(story.get("last_updated"))
    recency = max(0.0, 100.0 - hours * 4.0) if hours is not None else 0.0

    score = round(
        article_pct * W_ARTICLE_COUNT + source_pct * W_SOURCE_DIVERSITY
        + bias_breadth * W_BIAS_BREADTH + velocity_pct * W_VELOCITY
        + recency * W_RECENCY, 1,
    )

    breakdown = {
        "article_count_pct": round(article_pct, 1),
        "source_diversity_pct": round(source_pct, 1),
        "bias_breadth": round(bias_breadth, 1),
        "velocity_pct": round(velocity_pct, 1),
        "recency_boost": round(recency, 1),
        "final": score,
    }
    return score, breakdown


def score_attention(story_ids=None) -> dict:
    """Compute attention scores for active stories.

    Returns: {"scored": int, "scores": [{"story_id", "score", "breakdown"}]}
    """
    all_stories = get_active_stories()
    if not all_stories:
        return {"scored": 0, "scores": []}

    targets = all_stories if story_ids is None else [s for s in all_stories if s["id"] in set(story_ids)]
    if not targets:
        return {"scored": 0, "scores": []}

    story_articles = {s["id"]: get_articles_for_story(s["id"]) for s in all_stories}
    velocity_values = [_velocity(story_articles[s["id"]]) for s in all_stories]

    results = []
    for story in targets:
        sid = story["id"]
        articles = story_articles.get(sid, [])
        if not articles and story.get("article_count", 0) == 0:
            score, breakdown = 0.0, {"article_count_pct": 0, "source_diversity_pct": 0,
                                      "bias_breadth": 0, "velocity_pct": 0, "recency_boost": 0, "final": 0}
        else:
            score, breakdown = _compute_attention(story, all_stories, articles, velocity_values)

        results.append({"story_id": sid, "score": score, "breakdown": breakdown})
        update_story_metadata(sid, attention_score=score)

    return {"scored": len(results), "scores": results}
```

---

## File: scoring/sentiment.py

```python
"""Sentiment analysis per story, grouped by political lean.

Uses VADER (no API calls) to score each article headline, then groups
by left/center/right source bias and stores per-group averages.
"""

import logging

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config.sources import SOURCE_BIAS
from db import queries as db

logger = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()

_LEFT_LABELS = {"far-left", "left", "left-center"}
_CENTER_LABELS = {"center"}
_RIGHT_LABELS = {"right-center", "right", "far-right"}


def _get_lean(source_name: str) -> str:
    meta = SOURCE_BIAS.get(source_name)
    if not meta:
        return "center"
    label = meta["label"]
    if label in _LEFT_LABELS:
        return "left"
    if label in _RIGHT_LABELS:
        return "right"
    return "center"


def _score_headline(text: str) -> float:
    return _analyzer.polarity_scores(text)["compound"]


def analyze_sentiment(story_ids=None) -> dict:
    """Compute sentiment breakdown by political lean for each story.

    Returns: {"analyzed": int, "results": [{"story_id", "left", "center", "right"}]}
    """
    if story_ids is not None:
        stories = [{"id": sid} for sid in story_ids]
    else:
        stories = db.get_active_stories()

    analyzed = 0
    results = []

    for story in stories:
        story_id = story["id"]
        articles = db.get_articles_for_story(story_id)
        if not articles:
            continue

        buckets: dict[str, list[float]] = {"left": [], "center": [], "right": []}

        for a in articles:
            title = a.get("title") or ""
            if not title.strip():
                continue
            score = _score_headline(title)
            db.update_article_sentiment(a["id"], score)
            lean = _get_lean(a.get("source_name", ""))
            buckets[lean].append(score)

        avgs = {}
        for lean, scores in buckets.items():
            avgs[lean] = round(sum(scores) / len(scores), 3) if scores else None

        db.update_story_metadata(
            story_id,
            sentiment_left=avgs["left"],
            sentiment_center=avgs["center"],
            sentiment_right=avgs["right"],
        )

        analyzed += 1
        results.append({"story_id": story_id, **avgs})

    return {"analyzed": analyzed, "results": results}
```

---

## File: scoring/timeline.py

```python
"""Story timeline tracking — lifecycle, trend, peak detection, and status."""

import logging
from datetime import datetime, timezone

from db.queries import get_active_stories, get_articles_for_story, update_story_metadata

logger = logging.getLogger(__name__)


def _compute_trend(articles: list[dict]) -> list[dict]:
    """Compute daily article counts from earliest article to today.

    Returns: [{"date": "YYYY-MM-DD", "count": N}, ...]
    """
    dates = []
    for a in articles:
        raw = a.get("published_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            continue
        dates.append(dt)

    if not dates:
        return []

    first_day = min(dates).date()
    today = datetime.now(timezone.utc).date()

    counts: dict[str, int] = {}
    for dt in dates:
        key = dt.date().isoformat()
        counts[key] = counts.get(key, 0) + 1

    trend = []
    current = first_day
    one_day = __import__("datetime").timedelta(days=1)
    while current <= today:
        key = current.isoformat()
        trend.append({"date": key, "count": counts.get(key, 0)})
        current += one_day

    return trend


def _find_peak(trend: list[dict]) -> tuple[int, str]:
    if not trend:
        return 0, ""
    best = max(trend, key=lambda d: d["count"])
    return best["count"], best["date"]


def _determine_status(trend: list[dict], hours_since_last: float) -> str:
    if not trend:
        return "stale"
    total_days = len(trend)
    story_age_hours = (total_days - 1) * 24 + datetime.now(timezone.utc).hour
    if story_age_hours < 4:
        return "breaking"
    if total_days <= 1 and hours_since_last < 24:
        return "developing"
    if hours_since_last >= 24:
        return "stale"
    today_count = trend[-1]["count"]
    yesterday_count = trend[-2]["count"] if len(trend) >= 2 else 0
    if today_count >= yesterday_count and today_count > 0:
        return "peak"
    peak_count = max(d["count"] for d in trend)
    if peak_count > 0 and today_count < peak_count * 0.5:
        return "fading"
    return "developing"


def update_timelines(story_ids=None) -> dict:
    """Update timeline data for active stories.

    Returns: {"updated": int, "results": [{"story_id", "status", "days_active", "trend", "peak_date"}]}
    """
    stories = [{"id": sid} for sid in story_ids] if story_ids else get_active_stories()
    results = []

    for story in stories:
        story_id = story["id"]
        try:
            articles = get_articles_for_story(story_id)
            if not articles:
                continue
            trend = _compute_trend(articles)
            if not trend:
                continue

            peak_count, peak_date = _find_peak(trend)

            pub_dates = [datetime.fromisoformat(a["published_at"]) for a in articles if a.get("published_at")]
            latest = max(pub_dates)
            hours_since_last = (datetime.now(timezone.utc) - latest.replace(tzinfo=timezone.utc)).total_seconds() / 3600

            status = _determine_status(trend, hours_since_last)
            earliest = min(pub_dates)

            update_story_metadata(
                story_id,
                trend=[{"date": d["date"], "count": d["count"]} for d in trend],
                peak_date=peak_date, status=status,
                first_seen=earliest.isoformat(),
            )

            results.append({
                "story_id": story_id, "status": status,
                "days_active": len(trend), "trend": trend, "peak_date": peak_date,
            })
        except Exception as exc:
            logger.error("Timeline update failed for story %d: %s", story_id, exc)

    return {"updated": len(results), "results": results}
```

---

## File: scoring/gaps.py

```python
"""Attention-gap detection — the core value proposition of ClearSignal.

Compares impact_score against attention_score to identify buried
(underreported) and overcovered (overreported) stories.
"""

import logging

from db.queries import get_active_stories

logger = logging.getLogger(__name__)

GAP_THRESHOLD = 30


def _classify_story(impact: float, attention: float) -> tuple[str, float]:
    gap = impact - attention
    if gap >= GAP_THRESHOLD:
        return ("buried", gap)
    if gap <= -GAP_THRESHOLD:
        return ("overcovered", gap)
    return ("balanced", gap)


def _explain_gap(classification: str, gap: float) -> str:
    if classification == "buried":
        return "Critical story receiving almost no coverage" if gap > 60 else "High-impact story receiving minimal coverage"
    if classification == "overcovered":
        return "Minor story dominating news coverage" if gap < -60 else "Low-impact story receiving disproportionate coverage"
    return "Coverage roughly matches significance"


def detect_gaps(story_ids=None) -> dict:
    """Detect attention gaps across all active stories.

    Returns: {"total_stories": int, "buried": list[dict], "overcovered": list[dict], "balanced": list[dict]}
    """
    stories = get_active_stories()
    if story_ids is not None:
        stories = [s for s in stories if s["id"] in set(story_ids)]

    buried, overcovered, balanced = [], [], []

    for story in stories:
        impact = story.get("impact_score")
        attention = story.get("attention_score")
        if not impact or not attention:
            continue

        classification, gap = _classify_story(impact, attention)
        entry = {
            "story_id": story["id"], "topic": story.get("topic", "Unknown"),
            "impact_score": impact, "attention_score": attention,
            "gap": gap, "classification": classification,
            "explanation": _explain_gap(classification, gap),
        }

        if classification == "buried":
            buried.append(entry)
        elif classification == "overcovered":
            overcovered.append(entry)
        else:
            balanced.append(entry)

    buried.sort(key=lambda s: s["gap"], reverse=True)
    overcovered.sort(key=lambda s: s["gap"])

    return {
        "total_stories": len(buried) + len(overcovered) + len(balanced),
        "buried": buried, "overcovered": overcovered, "balanced": balanced,
    }
```

---

## File: pipeline/process.py

```python
"""Wire clustering and scoring modules together.

Full pipeline order:
    INGEST -> CLUSTER -> SCORE
    Clustering: assign -> discover -> split -> label -> merge
    Scoring:    impact -> handle outliers -> attention -> sentiment -> timeline -> gaps
"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from clustering.assign import assign_articles_to_stories
from clustering.discover import discover_new_clusters
from clustering.label import label_stories
from clustering.merge import merge_similar_stories
from clustering.split import split_oversized_stories
from db import queries as db
from scoring.attention import score_attention
from scoring.gaps import detect_gaps
from scoring.impact import score_impacts
from scoring.sentiment import analyze_sentiment
from scoring.timeline import update_timelines

logger = logging.getLogger(__name__)
console = Console()


def run_clustering() -> dict:
    console.rule("[bold cyan]Clustering[/bold cyan]")
    assign_result = assign_articles_to_stories()
    discover_result = discover_new_clusters()
    split_result = split_oversized_stories()
    label_result = label_stories()
    merge_result = merge_similar_stories()

    active_stories = db.get_active_stories()
    return {
        "assign": assign_result, "discover": discover_result,
        "split": split_result, "label": label_result,
        "merge": merge_result, "active_stories": len(active_stories),
    }


def run_scoring() -> dict:
    console.rule("[bold magenta]Scoring[/bold magenta]")

    impact_result = score_impacts()

    outliers = impact_result.get("outlier_articles", [])
    for outlier in outliers:
        db.update_article_story(outlier["article_id"], None)

    attention_result = score_attention()
    sentiment_result = analyze_sentiment()
    timeline_result = update_timelines()
    gap_result = detect_gaps()

    return {
        "impact": impact_result, "outliers_handled": len(outliers),
        "attention": attention_result, "sentiment": sentiment_result,
        "timeline": timeline_result, "gaps": gap_result,
    }
```

---

## File: pipeline/main.py

```python
"""ClearSignal pipeline — CLI entry point and daemon scheduler.

Usage:
    python -m pipeline.main --once       # single run
    python -m pipeline.main --dry-run    # fetch only
    python -m pipeline.main              # daemon mode (every 15 min)
"""

from pipeline.ingest import run_ingestion
from pipeline.process import run_clustering, run_scoring


def run_once(dry_run=False):
    result = run_ingestion(dry_run=dry_run)
    if not dry_run and result.new_stored > 0:
        run_clustering()
        run_scoring()
```
