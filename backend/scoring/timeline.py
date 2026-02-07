"""Story timeline tracking — lifecycle, trend, peak detection, and status.

Computes daily article-count trends for each story, identifies peak
coverage days, and determines the current lifecycle status (breaking,
developing, peak, fading, stale).
"""

import logging
from datetime import datetime, timezone

from db.queries import get_active_stories, get_articles_for_story, update_story_metadata

logger = logging.getLogger(__name__)


# ─── helpers ──────────────────────────────────────────────────────────────────


def _compute_trend(articles: list[dict]) -> list[dict]:
    """Compute daily article counts for the story's lifetime.

    Args:
        articles: Article dicts with ``published_at`` strings (ISO-8601).
            Articles missing ``published_at`` are silently skipped.

    Returns:
        List of ``{"date": "YYYY-MM-DD", "count": N}`` dicts, one per day
        from the earliest article to today (inclusive).  Days with zero
        articles still appear so the frontend can draw a continuous line.
    """
    dates: list[datetime] = []
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

    # Build a count-per-day dict
    counts: dict[str, int] = {}
    for dt in dates:
        key = dt.date().isoformat()
        counts[key] = counts.get(key, 0) + 1

    # Fill every day from first_day to today
    trend: list[dict] = []
    current = first_day
    one_day = __import__("datetime").timedelta(days=1)
    while current <= today:
        key = current.isoformat()
        trend.append({"date": key, "count": counts.get(key, 0)})
        current += one_day

    return trend


def _find_peak(trend: list[dict]) -> tuple[int, str]:
    """Find the peak day (highest article count) and its date.

    Args:
        trend: Output of ``_compute_trend``.

    Returns:
        ``(peak_count, peak_date_iso)`` where *peak_date_iso* is a
        ``"YYYY-MM-DD"`` string.  Returns ``(0, "")`` for empty trends.
    """
    if not trend:
        return 0, ""

    best = max(trend, key=lambda d: d["count"])
    return best["count"], best["date"]


def _determine_status(trend: list[dict], hours_since_last: float) -> str:
    """Determine story lifecycle status from its trend and recency.

    Statuses (checked in priority order):
        * ``"breaking"``   — first seen < 4 hours ago
        * ``"developing"`` — less than 24 hours old and still getting articles
        * ``"stale"``      — no new articles in 24+ hours
        * ``"peak"``       — today's count >= yesterday's (still growing)
        * ``"fading"``     — today's count < 50 % of peak day

    Args:
        trend: Output of ``_compute_trend`` (must not be empty).
        hours_since_last: Hours between now and the most recent article.

    Returns:
        One of the status strings above.
    """
    if not trend:
        return "stale"

    total_days = len(trend)

    # Age of the entire story in hours
    story_age_hours = (total_days - 1) * 24 + (
        datetime.now(timezone.utc).hour  # partial day
    )

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


# ─── public API ───────────────────────────────────────────────────────────────


def update_timelines(
    story_ids: list[int] | None = None,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Update timeline data for active stories.

    For each story this function:
    1. Fetches all articles sorted by ``published_at``
    2. Computes a daily article-count trend
    3. Finds the peak-coverage day
    4. Determines the lifecycle status
    5. Persists ``trend``, ``peak_date``, ``status``, ``first_seen``,
       and ``last_updated`` back to the stories table

    Args:
        story_ids: Specific story IDs to process.  ``None`` means all
            active stories.

    Returns::

        {
            "updated": int,
            "results": [
                {"story_id": int, "status": str, "days_active": int,
                 "trend": list[dict], "peak_date": str},
                ...
            ]
        }
    """
    if story_ids is not None:
        stories = [{"id": sid} for sid in story_ids]
    else:
        stories = get_active_stories()

    results: list[dict] = []

    for story in stories:
        story_id = story["id"]
        try:
            articles = (
                story_articles[story_id]
                if story_articles is not None and story_id in story_articles
                else get_articles_for_story(story_id)
            )

            if not articles:
                logger.debug("Story %d has no articles, skipping", story_id)
                continue

            trend = _compute_trend(articles)

            if not trend:
                logger.debug("Story %d has no datable articles, skipping", story_id)
                continue

            peak_count, peak_date = _find_peak(trend)

            # Hours since most recent article
            pub_dates = [
                datetime.fromisoformat(a["published_at"])
                for a in articles
                if a.get("published_at")
            ]
            latest = max(pub_dates)
            hours_since_last = (
                datetime.now(timezone.utc) - latest.replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600

            status = _determine_status(trend, hours_since_last)

            earliest = min(pub_dates)

            # Persist to DB
            update_story_metadata(
                story_id,
                trend=[{"date": d["date"], "count": d["count"]} for d in trend],
                peak_date=peak_date,
                status=status,
                first_seen=earliest.isoformat(),
            )

            results.append({
                "story_id": story_id,
                "status": status,
                "days_active": len(trend),
                "trend": trend,
                "peak_date": peak_date,
            })

        except Exception as exc:
            logger.error("Timeline update failed for story %d: %s", story_id, exc)

    logger.info("Updated timelines for %d stories", len(results))
    return {"updated": len(results), "results": results}


# ─── standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = update_timelines()
    print(f"Updated {result['updated']} stories")
    for r in result["results"][:10]:
        trend_str = " ".join([str(d["count"]) for d in r["trend"][-7:]])
        print(
            f"  #{r['story_id']}: status={r['status']} "
            f"trend=[{trend_str}] peak={r['peak_date']}"
        )
