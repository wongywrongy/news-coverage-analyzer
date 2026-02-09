"""Coverage scoring — pure formula measuring how much coverage a story receives.

No AI calls.  Computes a 0-100 score from four weighted components:

    article_count_norm  (40%)  story's article count / max across all active stories
    source_diversity    (30%)  unique sources / total monitored sources
    recency             (20%)  inverse decay from hours since last article
    velocity            (10%)  articles in last 24h / articles in prior 24h

The result is stored as ``coverage_score`` on the story row.
"""

import logging
import math
from datetime import datetime, timezone

from config.sources import SOURCE_BIAS
from db.queries import (
    get_active_stories,
    get_articles_for_story,
    update_story_metadata,
)

logger = logging.getLogger(__name__)

# ── Weights ──────────────────────────────────────────────────────────────────

W_ARTICLE_COUNT = 0.40
W_SOURCE_DIVERSITY = 0.30
W_RECENCY = 0.20
W_VELOCITY = 0.10

TOTAL_MONITORED_SOURCES = len(SOURCE_BIAS) or 40  # fallback if config empty


# ── Component helpers ────────────────────────────────────────────────────────


def _article_count_norm(story_count: int, max_count: int) -> float:
    """Normalize article count as ratio of max across all active stories.

    Returns 0-100.
    """
    if max_count <= 0:
        return 0.0
    return min(100.0, (story_count / max_count) * 100)


def _source_diversity(articles: list[dict]) -> float:
    """Unique sources covering this story / total monitored sources.

    Returns 0-100.
    """
    unique_sources = {
        a.get("source_domain") or a.get("source_name", "")
        for a in articles
        if a.get("source_domain") or a.get("source_name")
    }
    return min(100.0, (len(unique_sources) / TOTAL_MONITORED_SOURCES) * 100)


def _recency_score(hours_since_last: float | None) -> float:
    """Inverse decay from hours since last article.

    100 if <1hr, 50 at 12hr, 25 at 24hr, 10 at 48hr+.
    Uses exponential decay to hit these approximate breakpoints.
    """
    if hours_since_last is None:
        return 0.0
    if hours_since_last < 1:
        return 100.0
    # Exponential decay: 100 * e^(-k*h) where k calibrated so f(12)≈50
    # ln(0.5)/12 ≈ -0.0578
    k = 0.0578
    score = 100.0 * math.exp(-k * hours_since_last)
    return max(score, 0.0)


def _velocity_score(articles: list[dict]) -> float:
    """Articles in last 24h / articles in prior 24h.

    Returns 0-100 (capped).  If prior period has 0 articles but current
    has >0, returns 100.
    """
    now = datetime.now(timezone.utc)
    last_24h = 0
    prior_24h = 0

    for a in articles:
        raw = a.get("published_at")
        if not raw:
            continue
        try:
            pub = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)

        hours_ago = (now - pub).total_seconds() / 3600
        if hours_ago <= 24:
            last_24h += 1
        elif hours_ago <= 48:
            prior_24h += 1

    if last_24h == 0:
        return 0.0
    if prior_24h == 0:
        return 100.0
    return min(100.0, (last_24h / prior_24h) * 100)


# ── Core computation ─────────────────────────────────────────────────────────


def compute_coverage_score(
    story: dict,
    articles: list[dict],
    max_article_count: int,
) -> tuple[int, dict]:
    """Compute coverage score (0-100) for a single story.

    Args:
        story:             Story dict with at least ``article_count``.
        articles:          Articles belonging to this story.
        max_article_count: Maximum article_count across all active stories.

    Returns:
        (score 0-100, breakdown dict with component values)
    """
    story_count = story.get("article_count") or len(articles)

    # 1. Article count norm
    acn = _article_count_norm(story_count, max_article_count)

    # 2. Source diversity
    sd = _source_diversity(articles)

    # 3. Recency — hours since last article
    hours_since = None
    last_article_at = story.get("last_article_at")
    if last_article_at:
        try:
            dt = datetime.fromisoformat(str(last_article_at).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hours_since = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    rec = _recency_score(hours_since)

    # 4. Velocity
    vel = _velocity_score(articles)

    # Weighted sum
    raw = acn * W_ARTICLE_COUNT + sd * W_SOURCE_DIVERSITY + rec * W_RECENCY + vel * W_VELOCITY
    score = min(100, round(raw))

    breakdown = {
        "article_count_norm": round(acn, 1),
        "source_diversity": round(sd, 1),
        "recency": round(rec, 1),
        "velocity": round(vel, 1),
        "final": score,
    }
    return score, breakdown


# ── Public interface ─────────────────────────────────────────────────────────


def score_coverage(
    story_ids: list[int] | None = None,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Compute coverage scores for active stories.

    If *story_ids* is None, score all active stories.

    Returns::

        {
            "scored": int,
            "scores": [{"story_id": int, "score": int, "breakdown": dict}, ...]
        }
    """
    all_stories = get_active_stories()
    if not all_stories:
        logger.warning("No active stories — nothing to score")
        return {"scored": 0, "scores": []}

    # Decide targets
    if story_ids is not None:
        target_ids = set(story_ids)
        targets = [s for s in all_stories if s["id"] in target_ids]
    else:
        targets = all_stories

    if not targets:
        return {"scored": 0, "scores": []}

    # Max article count across ALL active stories (for normalization)
    max_article_count = max(
        (s.get("article_count") or 0 for s in all_stories), default=1
    )
    max_article_count = max(max_article_count, 1)  # avoid division by zero

    # Fetch articles if not provided
    if story_articles is None:
        story_articles = {}
        for s in targets:
            story_articles[s["id"]] = get_articles_for_story(s["id"])

    results: list[dict] = []
    for story in targets:
        sid = story["id"]
        articles = story_articles.get(sid, [])

        score, breakdown = compute_coverage_score(story, articles, max_article_count)

        results.append({
            "story_id": sid,
            "score": score,
            "breakdown": breakdown,
        })

        # Persist
        update_story_metadata(sid, coverage_score=float(score))

    logger.info("Coverage scoring complete: %d stories scored", len(results))
    return {"scored": len(results), "scores": results}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = score_coverage()
    print(f"\nScored {result['scored']} stories\n")

    for s in sorted(result["scores"], key=lambda x: x["score"], reverse=True)[:10]:
        b = s["breakdown"]
        print(
            f"  Story #{s['story_id']}: coverage={s['score']}"
            f"  (articles={b['article_count_norm']:.0f}"
            f"  sources={b['source_diversity']:.0f}"
            f"  recency={b['recency']:.0f}"
            f"  velocity={b['velocity']:.0f})"
        )
