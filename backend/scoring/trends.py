"""Trend computation from the story_daily_counts table.

Reads pre-aggregated daily counts and builds continuous trend arrays
with zero-filled gaps, suitable for frontend timeline visualization.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from db.queries import get_active_stories, get_daily_counts

logger = logging.getLogger(__name__)


def compute_trend_from_counts(daily_counts: list[dict]) -> list[dict]:
    """Build a continuous trend array from sparse daily counts.

    Args:
        daily_counts: Rows from story_daily_counts, each with
            ``"date"`` (``"YYYY-MM-DD"``) and ``"article_count"`` (int).

    Returns:
        ``[{"date": "YYYY-MM-DD", "count": N}, ...]`` with one entry
        per day from the earliest date to today (inclusive).  Days with
        no articles get ``count: 0``.
    """
    if not daily_counts:
        return []

    # Build lookup from date string → count
    counts: dict[str, int] = {}
    for row in daily_counts:
        date_str = row.get("date", "")
        # Supabase may return date as "YYYY-MM-DD" or datetime string
        if "T" in str(date_str):
            date_str = str(date_str).split("T")[0]
        count = row.get("article_count", 0)
        if date_str:
            counts[date_str] = count

    if not counts:
        return []

    # Determine range
    dates = sorted(counts.keys())
    try:
        first_day = datetime.strptime(dates[0], "%Y-%m-%d").date()
    except ValueError:
        return []

    today = datetime.now(UTC).date()

    # Fill every day from first_day to today
    trend: list[dict] = []
    current = first_day
    one_day = timedelta(days=1)
    while current <= today:
        key = current.isoformat()
        trend.append({"date": key, "count": counts.get(key, 0)})
        current += one_day

    return trend


def get_story_trend(story_id: int) -> list[dict]:
    """Fetch daily counts for a story and return a continuous trend array.

    Convenience function combining ``get_daily_counts`` + ``compute_trend_from_counts``.
    """
    daily_counts = get_daily_counts(story_id)
    return compute_trend_from_counts(daily_counts)


def compute_trend_direction(trend: list[dict], window: int = 3) -> str:
    """Determine trend direction from the last N days.

    Args:
        trend: Output of ``compute_trend_from_counts``.
        window: Number of recent days to evaluate.

    Returns:
        ``"trending"`` if slope > 0.5, ``"cooling"`` if slope < -0.5,
        otherwise ``"steady"``.
    """
    if len(trend) < window + 1:
        return "steady"

    recent = trend[-(window + 1):]
    earlier_avg = sum(d["count"] for d in recent[:window]) / window
    latest = recent[-1]["count"]
    slope = latest - earlier_avg

    if slope > 0.5:
        return "trending"
    if slope < -0.5:
        return "cooling"
    return "steady"


# ─── standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    stories = get_active_stories()
    print(f"Active stories: {len(stories)}")

    for story in stories[:5]:
        sid = story["id"]
        trend = get_story_trend(sid)
        direction = compute_trend_direction(trend)
        last_7 = " ".join(str(d["count"]) for d in trend[-7:]) if trend else "no data"
        print(f"  #{sid}: {len(trend)} days, direction={direction}, last 7: [{last_7}]")
