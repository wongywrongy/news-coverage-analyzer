"""
Attention scoring — measures HOW MUCH media coverage a story receives.

Every component is **relative**: percentile-ranked against all active stories
so scores automatically adjust to the current news cycle.  No AI calls.

Components (weights sum to 1.0):
  article_count  0.35   — raw volume of articles
  source_diversity 0.25 — number of distinct outlets
  bias_breadth   0.20   — spectrum coverage (far-left … far-right)
  velocity       0.10   — articles per hour in last 24 h
  recency_boost  0.10   — decays 4 points per hour since last update
"""

import logging
from datetime import datetime, timezone

from db.queries import (
    get_active_stories,
    get_articles_for_story,
    update_story_metadata,
)

logger = logging.getLogger(__name__)

# ── Weights ──────────────────────────────────────────────────────────────────

W_ARTICLE_COUNT = 0.35
W_SOURCE_DIVERSITY = 0.25
W_BIAS_BREADTH = 0.20
W_VELOCITY = 0.10
W_RECENCY = 0.10

BIAS_CATEGORIES = {
    "far-left", "left", "left-center", "center",
    "right-center", "right", "far-right",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _percentile_rank(value: float, values: list[float]) -> float:
    """Return the percentile rank of *value* within *values* (0-100).

    Uses the "weak" definition: percentage of values strictly less than
    *value*, plus half the percentage equal to *value*.  Matches the
    behaviour of ``scipy.stats.percentileofscore(kind='rank')``.

    If *values* is empty, returns 0.
    """
    n = len(values)
    if n == 0:
        return 0.0
    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return ((below + 0.5 * equal) / n) * 100


def _hours_since(dt: datetime | str | None) -> float | None:
    """Return hours elapsed since *dt*, or None if *dt* is missing."""
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if isinstance(dt, str):
        # Supabase returns ISO strings — handle both 'Z' and '+00:00'
        dt = dt.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (now - dt).total_seconds() / 3600.0
    return max(0.0, delta)


def _velocity(articles: list[dict]) -> float:
    """Count articles published in the last 24 hours.

    The count itself is later percentile-ranked across stories, so we
    don't need to convert to articles-per-hour here.
    """
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


# ── Core computation ─────────────────────────────────────────────────────────

def _compute_attention(
    story: dict,
    all_stories: list[dict],
    articles: list[dict],
    velocity_values: list[float],
) -> tuple[float, dict]:
    """Compute normalised attention score for a single story.

    Args:
        story:            The target story dict.
        all_stories:      All active stories (for percentile baselines).
        articles:         Articles belonging to *story*.
        velocity_values:  Pre-computed velocity counts for every active story
                          (same order as *all_stories*).

    Returns:
        (score 0–100, breakdown dict with component scores)
    """
    article_counts = [s.get("article_count", 0) for s in all_stories]
    source_counts = [s.get("source_count", 0) for s in all_stories]

    # 1. Article count percentile
    article_pct = _percentile_rank(
        story.get("article_count", 0), article_counts,
    )

    # 2. Source diversity percentile
    source_pct = _percentile_rank(
        story.get("source_count", 0), source_counts,
    )

    # 3. Bias breadth (absolute, not percentile)
    distinct_biases = {
        a.get("source_bias")
        for a in articles
        if a.get("source_bias") in BIAS_CATEGORIES
    }
    bias_breadth = (len(distinct_biases) / len(BIAS_CATEGORIES)) * 100

    # 4. Velocity percentile
    vel = _velocity(articles)
    velocity_pct = _percentile_rank(vel, velocity_values)

    # 5. Recency boost
    hours = _hours_since(story.get("last_updated"))
    if hours is None:
        recency = 0.0
    else:
        recency = max(0.0, 100.0 - hours * 4.0)

    score = round(
        article_pct * W_ARTICLE_COUNT
        + source_pct * W_SOURCE_DIVERSITY
        + bias_breadth * W_BIAS_BREADTH
        + velocity_pct * W_VELOCITY
        + recency * W_RECENCY,
        1,
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


# ── Public interface ─────────────────────────────────────────────────────────

def score_attention(
    story_ids: list[int] | None = None,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Compute attention scores for active stories.

    If *story_ids* is None, score all active stories.

    Returns::

        {
            "scored": int,
            "scores": [{"story_id": int, "score": float, "breakdown": dict}, …]
        }
    """
    all_stories = get_active_stories()
    if not all_stories:
        logger.warning("No active stories found — nothing to score")
        return {"scored": 0, "scores": []}

    # Decide which stories to score
    if story_ids is not None:
        target_ids = set(story_ids)
        targets = [s for s in all_stories if s["id"] in target_ids]
    else:
        targets = all_stories

    if not targets:
        logger.warning("None of the requested story_ids are active")
        return {"scored": 0, "scores": []}

    # Fetch articles for every active story (needed for velocity baselines
    # even for stories we aren't scoring).
    if story_articles is None:
        story_articles = {}
        for s in all_stories:
            sid = s["id"]
            story_articles[sid] = get_articles_for_story(sid)

    # Pre-compute velocity for all active stories (percentile baseline)
    velocity_values = [_velocity(story_articles[s["id"]]) for s in all_stories]

    results: list[dict] = []
    for story in targets:
        sid = story["id"]
        articles = story_articles.get(sid, [])

        if not articles and story.get("article_count", 0) == 0:
            score, breakdown = 0.0, {
                "article_count_pct": 0.0,
                "source_diversity_pct": 0.0,
                "bias_breadth": 0.0,
                "velocity_pct": 0.0,
                "recency_boost": 0.0,
                "final": 0.0,
            }
        else:
            score, breakdown = _compute_attention(
                story, all_stories, articles, velocity_values,
            )

        results.append({
            "story_id": sid,
            "score": score,
            "breakdown": breakdown,
        })

        # Persist — only update attention_score, leave impact_score untouched
        update_story_metadata(sid, attention_score=score)

    logger.info(
        "Attention scoring complete: %d stories scored", len(results),
    )
    return {"scored": len(results), "scores": results}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = score_attention()
    print(f"\nScored {result['scored']} stories\n")

    for s in sorted(result["scores"], key=lambda x: x["score"], reverse=True)[:10]:
        print(f"  Story #{s['story_id']}: attention={s['score']:.1f}")
        b = s["breakdown"]
        print(
            f"    articles={b['article_count_pct']:.0f}%"
            f"  sources={b['source_diversity_pct']:.0f}%"
            f"  bias={b['bias_breadth']:.0f}%"
            f"  velocity={b['velocity_pct']:.0f}%"
            f"  recency={b['recency_boost']:.0f}%"
        )
