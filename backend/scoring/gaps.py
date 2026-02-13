"""Coverage-gap detection — the core value proposition of ClearSignal.

Compares each story's significance_score against its coverage_score
(attention_score) to characterize the relationship between real-world
impact and media coverage volume.

Uses neutral, descriptive language throughout:
- "significance exceeds coverage"  (NOT "buried" or "underreported")
- "coverage exceeds significance"  (NOT "overblown" or "hyped")
- "roughly proportional"

Each gap entry includes caveats acknowledging that coverage data is a
sample, not a census.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from db.queries import get_active_stories

logger = logging.getLogger(__name__)

# A 30-point gap on a 0-100 scale means one dimension is at least 30%
# higher than the other.  Tunable once we see how scores distribute.
GAP_THRESHOLD = 30


# ── Classification ──────────────────────────────────────────────────────────


def _classify_gap(significance: float, coverage: float) -> tuple[str, float]:
    """Classify the relationship between significance and coverage.

    gap = significance - coverage

    Returns:
        (gap_direction, gap_value)

    gap_direction is one of:
        "significance exceeds coverage"
        "coverage exceeds significance"
        "roughly proportional"
    """
    gap = significance - coverage

    if gap >= GAP_THRESHOLD:
        return ("significance exceeds coverage", gap)
    if gap <= -GAP_THRESHOLD:
        return ("coverage exceeds significance", gap)
    return ("roughly proportional", gap)


def _describe_gap(
    topic: str,
    significance: float,
    coverage: float,
    gap: float,
    direction: str,
    status: str,
) -> str:
    """Generate a neutral, descriptive summary of the gap observation.

    Rules (from prompt spec):
    - No editorializing ("good"/"bad")
    - No motive attribution ("media chose to...")
    - Acknowledge this is a sample, not a census
    """
    abs_gap = abs(gap)

    if direction == "roughly proportional":
        return (
            f'"{topic}" shows coverage volume roughly proportional to its '
            f"estimated significance (significance {significance:.0f}, "
            f"coverage {coverage:.0f}). "
            f"The {abs_gap:.0f}-point difference is within normal variation."
        )

    if direction == "significance exceeds coverage":
        intensity = "notably" if abs_gap >= 50 else "moderately"
        return (
            f'"{topic}" has {intensity} lower coverage relative to its '
            f"estimated significance (significance {significance:.0f}, "
            f"coverage {coverage:.0f}, gap +{gap:.0f}). "
            f"This observation is based on sampled sources and may not "
            f"reflect total coverage."
        )

    # coverage exceeds significance
    intensity = "notably" if abs_gap >= 50 else "moderately"
    return (
        f'"{topic}" has {intensity} higher coverage relative to its '
        f"estimated significance (significance {significance:.0f}, "
        f"coverage {coverage:.0f}, gap {gap:.0f}). "
        f"This observation is based on sampled sources and may not "
        f"reflect total coverage."
    )


def _build_caveats(story: dict, coverage: float) -> list[str]:
    """Generate a list of limitation caveats for this gap observation."""
    caveats: list[str] = [
        "Coverage data is a sample from monitored sources, not a census of all media."
    ]

    article_count = story.get("article_count") or 0
    if article_count < 5:
        caveats.append(
            f"Low sample size ({article_count} articles) — gap estimate is less reliable."
        )

    status = story.get("status", "")
    if status == "developing":
        caveats.append(
            "Story is still developing; coverage volume may change significantly."
        )

    # Check recency — if story is very new, coverage may not have caught up
    first_seen = story.get("first_seen")
    if first_seen:
        if isinstance(first_seen, str):
            try:
                first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            except ValueError:
                first_seen = None
        if first_seen:
            if first_seen.tzinfo is None:
                first_seen = first_seen.replace(tzinfo=UTC)
            age_hours = (datetime.now(UTC) - first_seen).total_seconds() / 3600
            if age_hours < 6:
                caveats.append(
                    f"Story first seen {age_hours:.0f}h ago — coverage may still be emerging."
                )

    return caveats


# ── Public API ──────────────────────────────────────────────────────────────


def detect_gaps(story_ids: list[int] | None = None) -> dict:
    """Detect coverage gaps across all active stories.

    Compares significance_score (real-world impact estimate) against
    attention_score (coverage volume/prominence) for each story.

    Args:
        story_ids: Optional list of story IDs to filter to.
                   If None, all active stories are analyzed.

    Returns:
        {
            "total_stories": int,
            "significance_exceeds_coverage": list[dict],
            "coverage_exceeds_significance": list[dict],
            "roughly_proportional": list[dict],
            # Backward-compat aliases:
            "buried": list[dict],       (same list as significance_exceeds_coverage)
            "overcovered": list[dict],   (same list as coverage_exceeds_significance)
            "balanced": list[dict],      (same list as roughly_proportional)
        }

    Each entry dict contains:
        story_id, topic, significance_score, coverage_score, gap,
        gap_direction, description, caveats
    """
    stories = get_active_stories()

    if story_ids is not None:
        id_set = set(story_ids)
        stories = [s for s in stories if s["id"] in id_set]

    sig_exceeds: list[dict] = []
    cov_exceeds: list[dict] = []
    proportional: list[dict] = []
    skipped = 0

    for story in stories:
        significance = story.get("significance_score") or story.get("impact_score")
        coverage = story.get("coverage_score") or story.get("attention_score")

        # Skip stories that haven't been scored yet
        if not significance or not coverage:
            skipped += 1
            continue

        direction, gap = _classify_gap(significance, coverage)
        description = _describe_gap(
            topic=story.get("topic", "Unknown"),
            significance=significance,
            coverage=coverage,
            gap=gap,
            direction=direction,
            status=story.get("status", ""),
        )
        caveats = _build_caveats(story, coverage)

        entry = {
            "story_id": story["id"],
            "topic": story.get("topic", "Unknown"),
            "significance_score": significance,
            "coverage_score": coverage,
            "coverage_volume": story.get("article_count") or 0,
            "source_diversity": story.get("source_count") or 0,
            "gap": gap,
            "gap_direction": direction,
            "description": description,
            "caveats": caveats,
            # Backward-compat keys
            "impact_score": significance,
            "attention_score": coverage,
            "classification": direction,
            "explanation": description,
        }

        if direction == "significance exceeds coverage":
            sig_exceeds.append(entry)
        elif direction == "coverage exceeds significance":
            cov_exceeds.append(entry)
        else:
            proportional.append(entry)

    # Largest positive gap first
    sig_exceeds.sort(key=lambda s: s["gap"], reverse=True)
    # Largest negative gap first
    cov_exceeds.sort(key=lambda s: s["gap"])

    total = len(sig_exceeds) + len(cov_exceeds) + len(proportional)

    logger.info(
        "Gap detection: %d stories — %d significance>coverage, "
        "%d coverage>significance, %d proportional (%d skipped, unscored)",
        total, len(sig_exceeds), len(cov_exceeds), len(proportional), skipped,
    )

    return {
        "total_stories": total,
        "significance_exceeds_coverage": sig_exceeds,
        "coverage_exceeds_significance": cov_exceeds,
        "roughly_proportional": proportional,
        # Backward-compat aliases (same list objects)
        "buried": sig_exceeds,
        "overcovered": cov_exceeds,
        "balanced": proportional,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  __main__ — standalone test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(level="INFO", format="%(name)s | %(message)s")

    result = detect_gaps()

    print(f"\nTotal scored stories: {result['total_stories']}")

    sig_ex = result["significance_exceeds_coverage"]
    print(f"\nSIGNIFICANCE > COVERAGE ({len(sig_ex)} stories):")
    for s in sig_ex[:5]:
        print(
            f"  {s['topic']}: significance={s['significance_score']}, "
            f"coverage={s['coverage_score']}, gap=+{s['gap']:.0f}"
        )
        print(f"    {s['description']}")
        if s['caveats']:
            print(f"    Caveats: {'; '.join(s['caveats'])}")

    cov_ex = result["coverage_exceeds_significance"]
    print(f"\nCOVERAGE > SIGNIFICANCE ({len(cov_ex)} stories):")
    for s in cov_ex[:5]:
        print(
            f"  {s['topic']}: significance={s['significance_score']}, "
            f"coverage={s['coverage_score']}, gap={s['gap']:.0f}"
        )
        print(f"    {s['description']}")

    prop = result["roughly_proportional"]
    print(f"\nROUGHLY PROPORTIONAL ({len(prop)} stories)")
