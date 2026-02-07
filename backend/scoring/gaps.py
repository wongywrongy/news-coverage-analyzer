"""Attention-gap detection — the core value proposition of ClearSignal.

Compares each story's impact_score against its attention_score to identify
stories where media coverage doesn't match real-world significance.

Categories:
- BURIED: high impact, low attention (important but under-reported)
- OVERCOVERED: low impact, high attention (less important but dominates news)
- BALANCED: attention roughly matches impact
"""

import logging

from db.queries import get_active_stories

logger = logging.getLogger(__name__)

# A 30-point gap on a 0-100 scale means one dimension is at least 30%
# higher than the other — a significant mismatch.  Tunable later once
# we see how scores distribute in practice.
GAP_THRESHOLD = 30


def _classify_story(impact: float, attention: float) -> tuple[str, float]:
    """Classify a story's attention gap.

    gap = impact - attention

    Positive gap = buried (impact > attention = underreported)
    Negative gap = overcovered (attention > impact = overreported)

    Classification:
    - BURIED: gap >= 30 (impact at least 30 points above attention)
    - OVERCOVERED: gap <= -30 (attention at least 30 points above impact)
    - BALANCED: -30 < gap < 30

    Returns:
        (classification_str, gap_value)
    """
    gap = impact - attention

    if gap >= GAP_THRESHOLD:
        return ("buried", gap)
    if gap <= -GAP_THRESHOLD:
        return ("overcovered", gap)
    return ("balanced", gap)


def _explain_gap(classification: str, gap: float) -> str:
    """Generate a human-readable explanation for a gap classification.

    These are computed descriptions, not AI-generated.
    """
    if classification == "buried":
        if gap > 60:
            return "Critical story receiving almost no coverage"
        return "High-impact story receiving minimal coverage"

    if classification == "overcovered":
        if gap < -60:
            return "Minor story dominating news coverage"
        return "Low-impact story receiving disproportionate coverage"

    return "Coverage roughly matches significance"


def detect_gaps(story_ids: list[int] | None = None) -> dict:
    """Detect attention gaps across all active stories.

    Args:
        story_ids: Optional list of story IDs to filter to.
                   If None, all active stories are analyzed.

    Returns:
        {
            "total_stories": int,
            "buried": list[dict],
            "overcovered": list[dict],
            "balanced": list[dict],
        }
    """
    stories = get_active_stories()

    if story_ids is not None:
        id_set = set(story_ids)
        stories = [s for s in stories if s["id"] in id_set]

    buried: list[dict] = []
    overcovered: list[dict] = []
    balanced: list[dict] = []
    skipped = 0

    for story in stories:
        impact = story.get("impact_score")
        attention = story.get("attention_score")

        # Skip stories that haven't been scored yet
        if not impact or not attention:
            skipped += 1
            continue

        classification, gap = _classify_story(impact, attention)
        explanation = _explain_gap(classification, gap)

        entry = {
            "story_id": story["id"],
            "topic": story.get("topic", "Unknown"),
            "impact_score": impact,
            "attention_score": attention,
            "gap": gap,
            "classification": classification,
            "explanation": explanation,
        }

        if classification == "buried":
            buried.append(entry)
        elif classification == "overcovered":
            overcovered.append(entry)
        else:
            balanced.append(entry)

    # Most buried first (largest positive gap)
    buried.sort(key=lambda s: s["gap"], reverse=True)
    # Most overcovered first (largest negative gap)
    overcovered.sort(key=lambda s: s["gap"])

    total = len(buried) + len(overcovered) + len(balanced)

    logger.info(
        "Gap detection complete: %d scored stories — %d buried, %d overcovered, "
        "%d balanced (%d skipped, unscored)",
        total, len(buried), len(overcovered), len(balanced), skipped,
    )

    return {
        "total_stories": total,
        "buried": buried,
        "overcovered": overcovered,
        "balanced": balanced,
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

    print(f"\n🔴 BURIED ({len(result['buried'])} stories):")
    for s in result["buried"][:5]:
        print(
            f"  {s['topic']}: impact={s['impact_score']}, "
            f"attention={s['attention_score']}, gap=+{s['gap']}"
        )

    print(f"\n🟡 OVERCOVERED ({len(result['overcovered'])} stories):")
    for s in result["overcovered"][:5]:
        print(
            f"  {s['topic']}: impact={s['impact_score']}, "
            f"attention={s['attention_score']}, gap={s['gap']}"
        )

    print(f"\n🟢 BALANCED ({len(result['balanced'])} stories):")
    print(f"  {len(result['balanced'])} stories with attention matching impact")
