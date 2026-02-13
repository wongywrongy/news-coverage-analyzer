"""Homepage ranking — decides which topics surface per category.

Computes a rank_score (0-100) from five weighted components:

    impact_weight       (35%)  raw impact_score
    coverage_weight     (20%)  raw coverage_score (heavily covered = headliner)
    velocity_weight     (20%)  articles last 24h vs prior 24h ratio
    recency_weight      (15%)  100 if articles today, decays over 72h
    framing_diversity   (10%)  number of distinct primary_framings / 7

Also assigns a featured_reason string explaining why the topic ranked.

No AI calls.  Reads from stories + analyses tables.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime

from db.queries import (
    get_active_stories,
    get_analysis,
    update_story_metadata,
)

logger = logging.getLogger(__name__)

# ── Weights ──────────────────────────────────────────────────────────────────

W_IMPACT = 0.35
W_COVERAGE = 0.20
W_VELOCITY = 0.20
W_RECENCY = 0.15
W_FRAMING = 0.10

# Total known framing categories from analysis/framing.py
TOTAL_FRAMING_CATEGORIES = 7


# ── Component helpers ────────────────────────────────────────────────────────


def _recency_factor(story: dict) -> float:
    """100 if articles today, exponential decay over 72h to ~0.

    Uses last_article_at timestamp.  Falls back to last_updated.
    """
    raw = story.get("last_article_at") or story.get("last_updated")
    if not raw:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return 0.0

    hours_ago = (datetime.now(UTC) - dt).total_seconds() / 3600
    if hours_ago < 1:
        return 100.0
    # Decay so that ~72h -> ~5
    # 100 * e^(-k*72) = 5  =>  k = ln(20)/72 ~ 0.0416
    k = 0.0416
    return max(0.0, 100.0 * math.exp(-k * hours_ago))


def _velocity_factor(story: dict) -> float:
    """Ratio of recent vs prior articles from the trend JSONB.

    Reads the last 2 days vs prior 2 days of daily counts.
    Returns 0-100 (capped).
    """
    trend = story.get("trend")
    if not trend:
        return 0.0
    if isinstance(trend, str):
        try:
            trend = json.loads(trend)
        except (json.JSONDecodeError, ValueError):
            return 0.0
    if not isinstance(trend, list) or len(trend) < 2:
        return 0.0

    # Last 2 days vs prior 2 days
    recent = trend[-2:] if len(trend) >= 2 else trend
    prior = trend[-4:-2] if len(trend) >= 4 else []

    recent_count = sum(d.get("count", 0) for d in recent)
    prior_count = sum(d.get("count", 0) for d in prior)

    if recent_count == 0:
        return 0.0
    if prior_count == 0:
        return 100.0
    return min(100.0, (recent_count / prior_count) * 100)


def _framing_diversity(source_framings: list[dict]) -> float:
    """Count distinct primary_framings / total categories.

    Returns 0-100.
    """
    if not source_framings:
        return 0.0

    distinct = set()
    for sf in source_framings:
        pf = sf.get("primary_framing")
        if pf:
            distinct.add(pf.lower().strip())

    return min(100.0, (len(distinct) / TOTAL_FRAMING_CATEGORIES) * 100)


# ── Core computation ─────────────────────────────────────────────────────────


def compute_rank_score(
    story: dict,
    source_framings: list[dict] | None = None,
) -> tuple[float, dict]:
    """Compute rank score (0-100) for a single story.

    Args:
        story:           Story dict with impact_score, coverage_score, etc.
        source_framings: Framing dicts from the analyses table (optional).

    Returns:
        (score 0-100, breakdown dict)
    """
    impact = story.get("impact_score") or 0
    coverage = story.get("coverage_score") or story.get("attention_score") or 0

    impact_component = min(impact, 100)
    coverage_component = min(coverage, 100)
    recency_component = _recency_factor(story)
    velocity_component = _velocity_factor(story)
    framing_component = _framing_diversity(source_framings or [])

    raw = (
        impact_component * W_IMPACT
        + coverage_component * W_COVERAGE
        + velocity_component * W_VELOCITY
        + recency_component * W_RECENCY
        + framing_component * W_FRAMING
    )
    score = min(100.0, round(raw, 1))

    breakdown = {
        "impact": round(impact_component, 1),
        "coverage": round(coverage_component, 1),
        "velocity": round(velocity_component, 1),
        "recency": round(recency_component, 1),
        "framing": round(framing_component, 1),
        "final": score,
    }
    return score, breakdown


def get_featured_reason(story: dict) -> str:
    """Return a human-readable reason why this story is featured.

    Priority order:
    1. undercovered (impact >> coverage by 20+)
    2. overcovered (coverage >> impact by 20+)
    3. trending (status == 'trending' or recent velocity spike)
    4. high_impact (impact_score > 80)
    5. notable (default)
    """
    impact = story.get("impact_score") or 0
    coverage = story.get("coverage_score") or story.get("attention_score") or 0
    gap = impact - coverage

    if gap > 20:
        return "undercovered"
    if gap < -20:
        return "overcovered"

    status = (story.get("status") or "").lower()
    if status == "trending":
        return "trending"

    # Check velocity from trend data
    vel = _velocity_factor(story)
    if vel > 150:
        return "trending"

    if impact > 80:
        return "high_impact"

    return "notable"


# ── Public interface ─────────────────────────────────────────────────────────


def score_rankings(story_ids: list[int] | None = None) -> dict:
    """Compute rank scores for active stories and persist to DB.

    If *story_ids* is None, score all active stories.

    Returns::

        {
            "scored": int,
            "scores": [{"story_id": int, "rank_score": float,
                         "featured_reason": str, "breakdown": dict}, ...]
        }
    """
    all_stories = get_active_stories()
    if not all_stories:
        logger.warning("No active stories — nothing to rank")
        return {"scored": 0, "scores": []}

    if story_ids is not None:
        target_ids = set(story_ids)
        targets = [s for s in all_stories if s["id"] in target_ids]
    else:
        targets = all_stories

    if not targets:
        return {"scored": 0, "scores": []}

    results: list[dict] = []

    for story in targets:
        sid = story["id"]

        # Fetch source_framings from the analysis (if exists)
        source_framings = []
        analysis = get_analysis(sid)
        if analysis:
            sf = analysis.get("source_framings")
            if isinstance(sf, str):
                try:
                    sf = json.loads(sf)
                except (json.JSONDecodeError, ValueError):
                    sf = []
            if isinstance(sf, list):
                source_framings = sf

        score, breakdown = compute_rank_score(story, source_framings)
        reason = get_featured_reason(story)

        results.append({
            "story_id": sid,
            "rank_score": score,
            "featured_reason": reason,
            "breakdown": breakdown,
        })

        # Persist
        update_story_metadata(
            sid,
            rank_score=float(score),
            featured_reason=reason,
        )

    logger.info("Ranking complete: %d stories scored", len(results))
    return {"scored": len(results), "scores": results}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = score_rankings()
    print(f"\nRanked {result['scored']} stories\n")

    sorted_scores = sorted(result["scores"], key=lambda x: x["rank_score"], reverse=True)
    for s in sorted_scores[:15]:
        b = s["breakdown"]
        print(
            f"  Story #{s['story_id']}: rank={s['rank_score']}"
            f"  reason={s['featured_reason']}"
            f"  (impact={b['impact']:.0f}"
            f"  coverage={b['coverage']:.0f}"
            f"  velocity={b['velocity']:.0f}"
            f"  recency={b['recency']:.0f}"
            f"  framing={b['framing']:.0f})"
        )
