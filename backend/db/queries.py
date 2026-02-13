"""
Database query functions — the ONLY module that touches Supabase tables.

All functions are stateless: no caching, no side-effects beyond the DB.
Every function gets its client via get_client(), logs errors, and uses
typed arguments / return values.

Groups: ARTICLES, STORIES, ANALYSES, VECTORS
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

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
    """Bulk-insert articles. Returns count of rows actually inserted.

    Skips duplicates silently (url has a UNIQUE constraint).
    """
    if not articles:
        return 0
    client = get_client()
    inserted = 0
    try:
        # Supabase upsert with ignoreDuplicates skips conflict on url
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
    """Return the subset of *urls* that already exist in the articles table.

    Queries in batches of 50 to stay within Supabase's URL length limit
    (long URLs like PBS paths can exceed the limit even at 200 per batch).
    Each batch is error-isolated so a single failure doesn't lose all results.
    """
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
    """Assign an article to a story, or unassign it (story_id=None).

    Also updates story_daily_counts: decrements the old story's count
    for the article's publish date and increments the new story's count.
    """
    client = get_client()
    try:
        # Fetch article's current story_id and published_at for daily-count tracking
        art = (
            client.table("articles")
            .select("story_id, published_at")
            .eq("id", article_id)
            .execute()
        )
        old_story_id = None
        pub_date = None
        if art.data:
            old_story_id = art.data[0].get("story_id")
            raw_pub = art.data[0].get("published_at")
            if raw_pub:
                try:
                    pub_date = datetime.fromisoformat(raw_pub).date().isoformat()
                except (ValueError, TypeError):
                    pub_date = None

        # Update the article's story_id
        client.table("articles").update({"story_id": story_id}).eq("id", article_id).execute()

        # Update daily counts if we have a publish date
        if pub_date:
            if old_story_id and old_story_id != story_id:
                _adjust_daily_count(old_story_id, pub_date, -1)
            if story_id and story_id != old_story_id:
                _adjust_daily_count(story_id, pub_date, 1)

    except Exception as exc:
        logger.error("update_article_story(%d, %s) failed: %s", article_id, story_id, exc)


def update_article_sentiment(article_id: int, sentiment: float) -> None:
    """Set the sentiment score for an article."""
    client = get_client()
    try:
        client.table("articles").update({"sentiment": sentiment}).eq("id", article_id).execute()
    except Exception as exc:
        logger.error("update_article_sentiment(%d) failed: %s", article_id, exc)


def get_articles_without_embeddings(limit: int | None = None) -> list[dict]:
    """Return articles where the embedding column IS NULL.

    Each dict contains ``id``, ``title``, and ``description`` — the
    minimum fields needed to generate an embedding.

    Args:
        limit: Max rows to return.  ``None`` means all.
    """
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
    """Set the embedding vector for a single article.

    Returns True on success, False on failure.
    """
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
            "last_updated": datetime.now(UTC).isoformat(),
        }).eq("id", story_id).execute()
    except Exception as exc:
        logger.error("update_story_scores(%d) failed: %s", story_id, exc)


def update_story_metadata(story_id: int, **kwargs: object) -> None:
    """Update arbitrary fields on a story row.

    Example: update_story_metadata(42, topic="Election", article_count=15)
    """
    if not kwargs:
        return
    kwargs["last_updated"] = datetime.now(UTC).isoformat()
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
#  STORY DAILY COUNTS
# ═══════════════════════════════════════════════════════════════════════════════


def _adjust_daily_count(story_id: int, date_str: str, delta: int) -> None:
    """Atomically adjust the article count for a (story, date) pair.

    Uses the ``upsert_daily_count`` RPC for a single atomic operation.
    Falls back to a read-then-write if the RPC is unavailable.
    """
    client = get_client()
    try:
        client.rpc("upsert_daily_count", {
            "p_story_id": story_id,
            "p_date": date_str,
            "p_delta": delta,
        }).execute()
    except Exception as exc:
        # Fallback: read-then-write (safe for single-threaded pipeline)
        logger.debug("RPC upsert_daily_count unavailable, falling back: %s", exc)
        try:
            result = (
                client.table("story_daily_counts")
                .select("article_count")
                .eq("story_id", story_id)
                .eq("date", date_str)
                .execute()
            )
            if result.data:
                new_count = max(result.data[0]["article_count"] + delta, 0)
                (
                    client.table("story_daily_counts")
                    .update({"article_count": new_count})
                    .eq("story_id", story_id)
                    .eq("date", date_str)
                    .execute()
                )
            elif delta > 0:
                (
                    client.table("story_daily_counts")
                    .insert({"story_id": story_id, "date": date_str, "article_count": delta})
                    .execute()
                )
        except Exception as exc:
            logger.error("_adjust_daily_count(%d, %s, %d) failed: %s", story_id, date_str, delta, exc)


def get_daily_counts(story_id: int) -> list[dict]:
    """Return daily article counts for a story, sorted by date ascending.

    Returns list of ``{"date": "YYYY-MM-DD", "article_count": N}``.
    """
    client = get_client()
    try:
        result = (
            client.table("story_daily_counts")
            .select("date, article_count")
            .eq("story_id", story_id)
            .order("date")
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_daily_counts(%d) failed: %s", story_id, exc)
        return []


def recalculate_daily_counts(story_id: int) -> int:
    """Recompute daily counts for a story from the articles table.

    Deletes existing rows and re-inserts from scratch.  Used after
    merge/split operations or as a periodic consistency check.

    Returns the number of date rows written.
    """
    client = get_client()
    try:
        # Delete existing counts for this story
        client.table("story_daily_counts").delete().eq("story_id", story_id).execute()

        # Fetch all articles for this story with published_at
        result = (
            client.table("articles")
            .select("published_at")
            .eq("story_id", story_id)
            .not_.is_("published_at", "null")
            .execute()
        )
        articles = result.data or []
        if not articles:
            return 0

        # Group by date
        counts: dict[str, int] = {}
        for a in articles:
            try:
                dt = datetime.fromisoformat(a["published_at"])
                key = dt.date().isoformat()
                counts[key] = counts.get(key, 0) + 1
            except (ValueError, TypeError):
                continue

        if not counts:
            return 0

        # Bulk insert
        rows = [
            {"story_id": story_id, "date": date_str, "article_count": count}
            for date_str, count in sorted(counts.items())
        ]
        client.table("story_daily_counts").insert(rows).execute()
        return len(rows)
    except Exception as exc:
        logger.error("recalculate_daily_counts(%d) failed: %s", story_id, exc)
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYSES
# ═══════════════════════════════════════════════════════════════════════════════


def upsert_analysis(data: dict) -> None:
    """Insert or update an analysis keyed by story_id."""
    data["updated_at"] = datetime.now(UTC).isoformat()
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
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        row = rows[0]
        # JSON array fields may come back as strings if column is TEXT
        for field in ("contrasts", "facts", "source_framings", "body"):
            val = row.get(field)
            if isinstance(val, str):
                try:
                    row[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    row[field] = []
        return row
    except Exception as exc:
        logger.error("get_analysis(%d) failed: %s", story_id, exc)
        return None


def get_stale_analyses(threshold_hours: float) -> list[int]:
    """Return story_ids whose analysis is older than *threshold_hours*.

    Used by the scheduler to decide which stories need re-analysis.
    """
    client = get_client()
    try:
        cutoff = datetime.now(UTC).timestamp() - (threshold_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=UTC).isoformat()
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
    embedding: list[float], threshold: float = 0.72
) -> tuple[int, float] | None:
    """Find the active story whose centroid is closest to *embedding*.

    Returns (story_id, similarity) if similarity >= threshold, else None.
    Uses a Supabase RPC wrapping pgvector cosine distance.
    """
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
    """Return id and centroid vector for all active stories.

    Used for local clustering when an RPC is not available.
    """
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


# ═══════════════════════════════════════════════════════════════════════════════
#  EDITORIAL SELECTION
# ═══════════════════════════════════════════════════════════════════════════════


def get_selection_candidates() -> list[dict]:
    """Return active stories with scored metadata + analysis staleness info.

    Single query joining stories + analyses (left join).
    Returns: id, topic, category, impact_score, coverage_score, article_count,
    source_count, status, last_article_at, has_analysis, analysis generated_at,
    article_count_at_gen.
    """
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select(
                "id, topic, category, impact_score, coverage_score, "
                "article_count, source_count, status, last_article_at, "
                "significance_score, "
                "analyses(generated_at, article_count_at_gen)"
            )
            .eq("active", True)
            .order("impact_score", desc=True)
            .execute()
        )
        rows = result.data or []
        # Flatten the joined analyses data
        candidates = []
        for row in rows:
            analyses = row.pop("analyses", None)
            if isinstance(analyses, list) and analyses:
                analysis = analyses[0]
                row["has_analysis"] = True
                row["analysis_generated_at"] = analysis.get("generated_at")
                row["article_count_at_gen"] = analysis.get("article_count_at_gen", 0)
            elif isinstance(analyses, dict) and analyses:
                row["has_analysis"] = True
                row["analysis_generated_at"] = analyses.get("generated_at")
                row["article_count_at_gen"] = analyses.get("article_count_at_gen", 0)
            else:
                row["has_analysis"] = False
                row["analysis_generated_at"] = None
                row["article_count_at_gen"] = 0
            candidates.append(row)
        return candidates
    except Exception as exc:
        logger.error("get_selection_candidates failed: %s", exc)
        return []


def mark_stories_selected(selections: list[dict]) -> None:
    """Batch update: set selected_for_analysis, selection_reason,
    selection_priority, last_selected_at on each story.

    Each dict must have: story_id, reason, priority
    """
    client = get_client()
    now = datetime.now(UTC).isoformat()
    for sel in selections:
        try:
            client.table("stories").update({
                "selected_for_analysis": True,
                "selection_reason": sel.get("reason", ""),
                "selection_priority": sel.get("priority"),
                "last_selected_at": now,
            }).eq("id", sel["story_id"]).execute()
        except Exception as exc:
            logger.error("mark_stories_selected(%d) failed: %s", sel["story_id"], exc)


def clear_selection_flags() -> None:
    """Reset all selected_for_analysis = FALSE at start of each cycle."""
    client = get_client()
    try:
        client.table("stories").update({
            "selected_for_analysis": False,
            "selection_reason": "",
            "selection_priority": None,
        }).eq("selected_for_analysis", True).execute()
    except Exception as exc:
        logger.error("clear_selection_flags failed: %s", exc)


def get_selected_story_ids() -> list[int]:
    """Return IDs where selected_for_analysis = TRUE."""
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select("id")
            .eq("selected_for_analysis", True)
            .execute()
        )
        return [row["id"] for row in (result.data or [])]
    except Exception as exc:
        logger.error("get_selected_story_ids failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  INSIGHTS CACHE
# ═══════════════════════════════════════════════════════════════════════════════


def get_cached_insights() -> list[dict]:
    """Return the cached insights array from insights_cache table."""
    client = get_client()
    try:
        result = (
            client.table("insights_cache")
            .select("insights, computed_at")
            .eq("id", 1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            insights = row.get("insights", [])
            if isinstance(insights, str):
                try:
                    insights = json.loads(insights)
                except (json.JSONDecodeError, ValueError):
                    insights = []
            return insights if isinstance(insights, list) else []
        return []
    except Exception as exc:
        logger.error("get_cached_insights failed: %s", exc)
        return []


def set_cached_insights(insights: list[dict]) -> None:
    """Overwrite the cached insights (singleton row id=1)."""
    client = get_client()
    try:
        client.table("insights_cache").upsert({
            "id": 1,
            "insights": insights,
            "computed_at": datetime.now(UTC).isoformat(),
        }).execute()
        logger.info("Cached %d insights", len(insights))
    except Exception as exc:
        logger.error("set_cached_insights failed: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTITY GRAPH
# ═══════════════════════════════════════════════════════════════════════════════


def upsert_entity(
    canonical_name: str,
    entity_type: str,
    aliases: list[str] | None = None,
) -> int | None:
    """Insert or update an entity by canonical_name. Returns entity id.

    If the entity exists, merges new aliases into the existing alias list
    and bumps last_seen_at. If not, creates a new entity.
    """
    client = get_client()
    try:
        # Check for exact canonical match
        result = (
            client.table("entities")
            .select("id, aliases")
            .eq("canonical_name", canonical_name)
            .execute()
        )
        if result.data:
            row = result.data[0]
            entity_id = row["id"]
            existing_aliases = row.get("aliases") or []
            if isinstance(existing_aliases, str):
                try:
                    existing_aliases = json.loads(existing_aliases)
                except (json.JSONDecodeError, ValueError):
                    existing_aliases = []
            # Merge new aliases
            merged = list(set(existing_aliases + (aliases or [])))
            client.table("entities").update({
                "aliases": merged,
                "last_seen_at": datetime.now(UTC).isoformat(),
            }).eq("id", entity_id).execute()
            return entity_id

        # No exact match — create new entity
        insert_data = {
            "canonical_name": canonical_name,
            "entity_type": entity_type,
            "aliases": aliases or [],
            "first_seen_at": datetime.now(UTC).isoformat(),
            "last_seen_at": datetime.now(UTC).isoformat(),
        }
        result = client.table("entities").insert(insert_data).execute()
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception as exc:
        logger.error("upsert_entity(%s) failed: %s", canonical_name, exc)
        return None


def find_entity_by_alias(alias: str, entity_type: str) -> int | None:
    """Search for an entity whose aliases array contains the given alias.

    Returns entity id if found, None otherwise.
    """
    client = get_client()
    try:
        result = (
            client.table("entities")
            .select("id")
            .eq("entity_type", entity_type)
            .contains("aliases", [alias])
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception as exc:
        logger.error("find_entity_by_alias(%s) failed: %s", alias, exc)
        return None


def link_topic_entity(
    topic_id: int, entity_id: int, relevance: str = "secondary"
) -> None:
    """Create a topic ↔ entity link. Skips if already exists."""
    client = get_client()
    try:
        client.table("topic_entities").upsert(
            {
                "topic_id": topic_id,
                "entity_id": entity_id,
                "relevance": relevance,
                "extracted_at": datetime.now(UTC).isoformat(),
            },
            on_conflict="topic_id,entity_id",
            ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        logger.error("link_topic_entity(%d, %d) failed: %s", topic_id, entity_id, exc)


def get_entities_for_topic(topic_id: int) -> list[dict]:
    """Return entities linked to a topic with their full entity data."""
    client = get_client()
    try:
        result = (
            client.table("topic_entities")
            .select("relevance, entities(id, canonical_name, entity_type, importance, topic_count, aliases)")
            .eq("topic_id", topic_id)
            .execute()
        )
        rows = result.data or []
        entities = []
        for row in rows:
            entity_data = row.get("entities")
            if isinstance(entity_data, dict):
                entity_data["relevance"] = row.get("relevance", "secondary")
                entities.append(entity_data)
            elif isinstance(entity_data, list) and entity_data:
                entity_data[0]["relevance"] = row.get("relevance", "secondary")
                entities.append(entity_data[0])
        return entities
    except Exception as exc:
        logger.error("get_entities_for_topic(%d) failed: %s", topic_id, exc)
        return []


def get_topics_for_entity(entity_id: int) -> list[int]:
    """Return list of topic (story) IDs linked to an entity."""
    client = get_client()
    try:
        result = (
            client.table("topic_entities")
            .select("topic_id")
            .eq("entity_id", entity_id)
            .execute()
        )
        return [row["topic_id"] for row in (result.data or [])]
    except Exception as exc:
        logger.error("get_topics_for_entity(%d) failed: %s", entity_id, exc)
        return []


def upsert_entity_relationship(entity_a_id: int, entity_b_id: int) -> None:
    """Create or increment a relationship edge between two entities.

    Ensures entity_a_id < entity_b_id to maintain the CHECK constraint.
    """
    a, b = min(entity_a_id, entity_b_id), max(entity_a_id, entity_b_id)
    if a == b:
        return
    client = get_client()
    now = datetime.now(UTC).isoformat()
    try:
        # Check if relationship exists
        result = (
            client.table("entity_relationships")
            .select("id, co_occurrence")
            .eq("entity_a_id", a)
            .eq("entity_b_id", b)
            .execute()
        )
        if result.data:
            row = result.data[0]
            client.table("entity_relationships").update({
                "co_occurrence": row["co_occurrence"] + 1,
                "last_linked_at": now,
            }).eq("id", row["id"]).execute()
        else:
            client.table("entity_relationships").insert({
                "entity_a_id": a,
                "entity_b_id": b,
                "co_occurrence": 1,
                "strength": 0.0,
                "first_linked_at": now,
                "last_linked_at": now,
            }).execute()
    except Exception as exc:
        logger.error("upsert_entity_relationship(%d, %d) failed: %s", a, b, exc)


def get_entity_relationships(entity_id: int) -> list[dict]:
    """Return all relationship edges involving an entity."""
    client = get_client()
    try:
        # Entity can be on either side of the edge
        result_a = (
            client.table("entity_relationships")
            .select("entity_b_id, co_occurrence, strength, last_linked_at")
            .eq("entity_a_id", entity_id)
            .execute()
        )
        result_b = (
            client.table("entity_relationships")
            .select("entity_a_id, co_occurrence, strength, last_linked_at")
            .eq("entity_b_id", entity_id)
            .execute()
        )
        edges = []
        for row in (result_a.data or []):
            edges.append({
                "neighbor_id": row["entity_b_id"],
                "co_occurrence": row["co_occurrence"],
                "strength": row["strength"],
                "last_linked_at": row["last_linked_at"],
            })
        for row in (result_b.data or []):
            edges.append({
                "neighbor_id": row["entity_a_id"],
                "co_occurrence": row["co_occurrence"],
                "strength": row["strength"],
                "last_linked_at": row["last_linked_at"],
            })
        return edges
    except Exception as exc:
        logger.error("get_entity_relationships(%d) failed: %s", entity_id, exc)
        return []


def get_all_entities() -> list[dict]:
    """Return all entities, ordered by importance descending."""
    client = get_client()
    try:
        result = (
            client.table("entities")
            .select("*")
            .order("importance", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_all_entities failed: %s", exc)
        return []


def get_all_entity_relationships() -> list[dict]:
    """Return all relationship edges."""
    client = get_client()
    try:
        result = (
            client.table("entity_relationships")
            .select("*")
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_all_entity_relationships failed: %s", exc)
        return []


def update_entity_importance(entity_id: int, importance: float, topic_count: int) -> None:
    """Update an entity's computed importance score and topic count."""
    client = get_client()
    try:
        client.table("entities").update({
            "importance": importance,
            "topic_count": topic_count,
        }).eq("id", entity_id).execute()
    except Exception as exc:
        logger.error("update_entity_importance(%d) failed: %s", entity_id, exc)


def update_relationship_strength(rel_id: int, strength: float) -> None:
    """Update the computed strength of a relationship edge."""
    client = get_client()
    try:
        client.table("entity_relationships").update({
            "strength": strength,
        }).eq("id", rel_id).execute()
    except Exception as exc:
        logger.error("update_relationship_strength(%d) failed: %s", rel_id, exc)


def get_topics_with_entities(entity_ids: list[int]) -> list[dict]:
    """Return topic_entities rows for a set of entity IDs (for co-occurrence lookups)."""
    if not entity_ids:
        return []
    client = get_client()
    try:
        result = (
            client.table("topic_entities")
            .select("topic_id, entity_id")
            .in_("entity_id", entity_ids)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_topics_with_entities failed: %s", exc)
        return []


def get_extracted_topic_ids() -> set[int]:
    """Return set of topic IDs that already have entity extractions."""
    client = get_client()
    try:
        result = (
            client.table("topic_entities")
            .select("topic_id")
            .execute()
        )
        return {row["topic_id"] for row in (result.data or [])}
    except Exception as exc:
        logger.error("get_extracted_topic_ids failed: %s", exc)
        return set()


def get_top_connected_entities(entity_id: int, limit: int = 3) -> list[dict]:
    """Return the top N entities connected to a given entity by strength."""
    edges = get_entity_relationships(entity_id)
    edges.sort(key=lambda e: e.get("strength", 0), reverse=True)
    top_edges = edges[:limit]
    if not top_edges:
        return []
    client = get_client()
    neighbor_ids = [e["neighbor_id"] for e in top_edges]
    try:
        result = (
            client.table("entities")
            .select("id, canonical_name, entity_type, importance")
            .in_("id", neighbor_ids)
            .execute()
        )
        name_map = {r["id"]: r for r in (result.data or [])}
        connected = []
        for edge in top_edges:
            nid = edge["neighbor_id"]
            info = name_map.get(nid, {})
            connected.append({
                "id": nid,
                "name": info.get("canonical_name", f"entity-{nid}"),
                "type": info.get("entity_type", ""),
                "importance": info.get("importance", 0),
                "strength": edge.get("strength", 0),
            })
        return connected
    except Exception as exc:
        logger.error("get_top_connected_entities(%d) failed: %s", entity_id, exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  __main__ — smoke test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from rich import print as rprint

    logging.basicConfig(level="INFO")

    rprint("[bold]db.queries smoke test[/bold]\n")

    # 1) Check existing URLs (should be empty set on fresh DB)
    urls = get_existing_urls(["https://example.com/not-real"])
    rprint(f"  existing urls check: {urls}")

    # 2) Active stories
    stories = get_active_stories()
    rprint(f"  active stories: {len(stories)}")

    # 3) Unassigned articles
    unassigned = get_unassigned_articles()
    rprint(f"  unassigned articles: {len(unassigned)}")

    # 4) Stale analyses (24h)
    stale = get_stale_analyses(24.0)
    rprint(f"  stale analyses (>24h): {len(stale)}")

    rprint("\n[bold green]All queries executed successfully.[/bold green]")
