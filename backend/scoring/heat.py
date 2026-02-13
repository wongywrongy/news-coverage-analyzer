"""Heat scoring — determines topic prominence on the front page.

Combines four weighted signals into a single sortable number:

    impact      (30%)  real-world significance
    source_breadth (25%)  logarithmic source diversity
    velocity    (25%)  articles per hour in the last 24h
    divergence  (20%)  framing diversity across sources

Recency is a multiplier — stories lose heat as they age regardless
of other signals.

No AI calls.  Pure formula over existing fields.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime

from constants import (
    COVERAGE_GAP_BADGE_THRESHOLD,
    HEAT_WEIGHT_DIVERGENCE,
    HEAT_WEIGHT_IMPACT,
    HEAT_WEIGHT_SOURCE_BREADTH,
    HEAT_WEIGHT_VELOCITY,
    RECENCY_DEFAULT,
    RECENCY_TIERS,
    TOTAL_FRAMING_CATEGORIES,
)
from db.queries import (
    get_active_stories,
    get_analysis,
    update_story_metadata,
)

logger = logging.getLogger(__name__)

# ── Weights ──────────────────────────────────────────────────────────────────

W_IMPACT = HEAT_WEIGHT_IMPACT
W_SOURCES = HEAT_WEIGHT_SOURCE_BREADTH
W_VELOCITY = HEAT_WEIGHT_VELOCITY
W_DIVERGENCE = HEAT_WEIGHT_DIVERGENCE

# ── Component helpers ────────────────────────────────────────────────────────


def _source_breadth(source_count: int) -> float:
    """Logarithmic source score.  20 sources isn't 10x better than 2.

    log2(sources + 1) * 15, caps around 100 at ~60 sources.
    """
    return min(math.log(max(source_count, 1) + 1, 2) * 15, 100.0)


def _velocity_from_trend(trend: list | str | None) -> float:
    """Articles per hour in the last 24h, converted to 0-100 score.

    5 articles/hour = 100.  Uses the last day of trend data.
    """
    if not trend:
        return 0.0
    if isinstance(trend, str):
        try:
            trend = json.loads(trend)
        except (json.JSONDecodeError, ValueError):
            return 0.0
    if not isinstance(trend, list):
        return 0.0

    # Sum last day's count
    if not trend:
        return 0.0
    last_day_count = trend[-1].get("count", 0) if trend else 0

    # Articles per hour (assuming 1 day of data)
    velocity = last_day_count / 24.0
    return min(velocity * 20, 100.0)  # 5 articles/hour = 100


def _framing_divergence(source_framings: list[dict] | None) -> float:
    """Distinct primary framings / total categories, scaled to 0-100."""
    if not source_framings:
        return 0.0

    distinct = set()
    for sf in source_framings:
        pf = sf.get("primary_framing")
        if pf:
            distinct.add(pf.lower().strip())

    return min(100.0, (len(distinct) / TOTAL_FRAMING_CATEGORIES) * 100)


def _recency_decay(story: dict) -> float:
    """Recency multiplier based on last article timestamp.

    Stories lose heat as they age:
        <6h  → 1.0
        <12h → 0.85
        <24h → 0.65
        <48h → 0.4
        else → 0.2
    """
    raw = story.get("last_article_at") or story.get("last_updated")
    if not raw:
        return RECENCY_DEFAULT
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return RECENCY_DEFAULT

    hours = (datetime.now(UTC) - dt).total_seconds() / 3600
    for threshold_hours, multiplier in RECENCY_TIERS:
        if hours < threshold_hours:
            return multiplier
    return RECENCY_DEFAULT


# ── Core computation ─────────────────────────────────────────────────────────


def compute_heat(
    story: dict,
    source_framings: list[dict] | None = None,
) -> tuple[float, dict]:
    """Compute heat score (0-100) for a single story.

    Returns (heat_score, breakdown_dict).
    """
    impact = min(story.get("impact_score") or 0, 100)
    source_score = _source_breadth(story.get("source_count") or 0)
    velocity_score = _velocity_from_trend(story.get("trend"))
    divergence_score = _framing_divergence(source_framings)
    recency = _recency_decay(story)

    raw = (
        impact * W_IMPACT
        + source_score * W_SOURCES
        + velocity_score * W_VELOCITY
        + divergence_score * W_DIVERGENCE
    )
    heat = round(raw * recency, 2)

    breakdown = {
        "impact": round(impact, 1),
        "source_breadth": round(source_score, 1),
        "velocity": round(velocity_score, 1),
        "divergence": round(divergence_score, 1),
        "recency": round(recency, 2),
        "raw": round(raw, 1),
        "heat": heat,
    }
    return heat, breakdown


def get_gap_badge(story: dict) -> str | None:
    """Return 'undercovered' badge if impact >> coverage, else None."""
    impact = story.get("impact_score") or 0
    coverage = story.get("coverage_score") or story.get("attention_score") or 0
    gap = impact - coverage
    if gap >= COVERAGE_GAP_BADGE_THRESHOLD:
        return "undercovered"
    return None


# ── Public interface ─────────────────────────────────────────────────────────


def score_heat(story_ids: list[int] | None = None) -> dict:
    """Compute heat for active stories and persist to DB.

    Returns: {"scored": N, "scores": [...]}
    """
    all_stories = get_active_stories()
    if not all_stories:
        logger.warning("No active stories — nothing to heat-score")
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

        # Get source_framings from analysis if it exists
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

        heat, breakdown = compute_heat(story, source_framings)
        badge = get_gap_badge(story)

        # Persist
        meta: dict = {
            "heat": heat,
            "heat_updated_at": datetime.now(UTC).isoformat(),
        }
        if badge:
            meta["featured_reason"] = badge
        else:
            # Preserve existing featured_reason from ranking if no gap badge
            existing_reason = story.get("featured_reason", "")
            if existing_reason != "undercovered":
                pass  # keep whatever ranking assigned
            else:
                # Was undercovered, now isn't — clear it
                meta["featured_reason"] = "notable"

        update_story_metadata(sid, **meta)

        results.append({
            "story_id": sid,
            "heat": heat,
            "badge": badge,
            "breakdown": breakdown,
        })

    logger.info("Heat scoring complete: %d stories scored", len(results))
    return {"scored": len(results), "scores": results}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = score_heat()
    print(f"\nScored {result['scored']} stories\n")

    sorted_scores = sorted(result["scores"], key=lambda x: x["heat"], reverse=True)
    for s in sorted_scores[:15]:
        b = s["breakdown"]
        badge_str = f"  [{s['badge']}]" if s.get("badge") else ""
        print(
            f"  Story #{s['story_id']}: heat={s['heat']}"
            f"  (impact={b['impact']:.0f}"
            f"  sources={b['source_breadth']:.0f}"
            f"  velocity={b['velocity']:.0f}"
            f"  divergence={b['divergence']:.0f}"
            f"  recency={b['recency']:.2f})"
            f"{badge_str}"
        )
