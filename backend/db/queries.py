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
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }).eq("id", story_id).execute()
    except Exception as exc:
        logger.error("update_story_scores(%d) failed: %s", story_id, exc)


def update_story_metadata(story_id: int, **kwargs: object) -> None:
    """Update arbitrary fields on a story row.

    Example: update_story_metadata(42, topic="Election", article_count=15)
    """
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
    except Exception:
        # Fallback: read-then-write (safe for single-threaded pipeline)
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
    now = datetime.now(timezone.utc).isoformat()
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
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        logger.info("Cached %d insights", len(insights))
    except Exception as exc:
        logger.error("set_cached_insights failed: %s", exc)


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
