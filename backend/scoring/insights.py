"""Global insights for the dashboard insights bar.

Computes exactly two insights per pipeline cycle:

1. **Undercovered** — category with the widest avg(impact) - avg(coverage) gap
   Fallback: individual topic with highest impact-coverage gap

2. **Surging** — category with the highest 48h article-count increase
   Fallback: individual topic with the highest velocity spike

Final fallback if both fail thresholds: highest impact topic + most covered topic.

After data computation, each insight's generic text is optionally enhanced via
a Claude Haiku call that references the specific topics driving the insight.
Enhancement is cached: Haiku is only called when the underlying insight changes
(different type+category than last cycle).  Cost: ~$0.002 per pipeline cycle
when both insights change, $0 when unchanged.
"""

import json
import logging
from datetime import datetime, timezone

from db.queries import get_active_stories, get_cached_insights, set_cached_insights

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Minimum gap to flag a category as undercovered
UNDERCOVERED_THRESHOLD = 15

# Minimum % increase to flag a category as surging
SURGING_THRESHOLD = 0.20  # 20%

# Minimum topics in a category for it to be considered
MIN_TOPICS_PER_CATEGORY = 3

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 60

CATEGORY_GROUPS = {
    "Politics & Law": [
        "POLITICS", "LAW", "GOVERNMENT", "LEGAL", "ELECTIONS",
    ],
    "World & Security": [
        "WORLD", "MILITARY", "INTERNATIONAL-RELATIONS", "SECURITY", "DEFENSE",
        "INTERNATIONAL", "INTERNATIONAL DIPLOMACY", "CONFLICT",
        "FOREIGN POLICY", "DIPLOMACY", "FOREIGN-POLICY",
    ],
    "Economy & Business": [
        "ECONOMY", "BUSINESS", "TECHNOLOGY", "FINANCE", "TRADE",
        "MARKETS", "ENERGY",
    ],
    "Science & Health": [
        "SCIENCE", "HEALTHCARE", "HEALTH", "ENVIRONMENT", "CLIMATE", "MEDICAL",
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_category_group(cat: str) -> str | None:
    """Map a story's category to its parent group label, or None."""
    trimmed = (cat or "").strip()

    # Match full group label (new format)
    if trimmed in CATEGORY_GROUPS:
        return trimmed

    # Match legacy uppercase member
    upper = trimmed.split("/")[0].strip().upper()
    for group_label, members in CATEGORY_GROUPS.items():
        if upper in members:
            return group_label

    return None


def _parse_trend(story: dict) -> list[dict]:
    """Parse story.trend JSONB into [{date, count}]."""
    trend = story.get("trend")
    if not trend:
        return []
    if isinstance(trend, str):
        try:
            trend = json.loads(trend)
        except (json.JSONDecodeError, ValueError):
            return []
    if not isinstance(trend, list):
        return []
    return trend


def _get_recent_dates() -> tuple[str, str, str, str]:
    """Return (today, yesterday, 2_days_ago, 3_days_ago) as YYYY-MM-DD."""
    now = datetime.now(timezone.utc)
    ms_per_day = 86400
    today = now.strftime("%Y-%m-%d")
    yesterday = (
        datetime.fromtimestamp(now.timestamp() - ms_per_day, tz=timezone.utc)
    ).strftime("%Y-%m-%d")
    two_ago = (
        datetime.fromtimestamp(now.timestamp() - 2 * ms_per_day, tz=timezone.utc)
    ).strftime("%Y-%m-%d")
    three_ago = (
        datetime.fromtimestamp(now.timestamp() - 3 * ms_per_day, tz=timezone.utc)
    ).strftime("%Y-%m-%d")
    return today, yesterday, two_ago, three_ago


# ── Category-level computations ─────────────────────────────────────────────


def _compute_category_gaps(
    stories: list[dict],
) -> list[tuple[str, float, int]]:
    """Compute avg(impact) - avg(coverage) per category group.

    Returns [(group_label, gap, topic_count)] sorted by gap descending.
    Only includes groups with >= MIN_TOPICS_PER_CATEGORY topics.
    """
    groups: dict[str, dict] = {}
    for label in CATEGORY_GROUPS:
        groups[label] = {"impact_sum": 0.0, "coverage_sum": 0.0, "count": 0}

    for story in stories:
        group = _get_category_group(story.get("category", ""))
        if group is None:
            continue
        g = groups[group]
        g["impact_sum"] += story.get("impact_score") or 0
        g["coverage_sum"] += (
            story.get("coverage_score") or story.get("attention_score") or 0
        )
        g["count"] += 1

    result = []
    for label, g in groups.items():
        if g["count"] < MIN_TOPICS_PER_CATEGORY:
            continue
        avg_impact = g["impact_sum"] / g["count"]
        avg_coverage = g["coverage_sum"] / g["count"]
        gap = avg_impact - avg_coverage
        result.append((label, gap, g["count"]))

    result.sort(key=lambda x: x[1], reverse=True)
    return result


def _compute_category_surges(
    stories: list[dict],
) -> list[tuple[str, float, int]]:
    """Compute 48h article-count surge per category group.

    Compares total article count in (today + yesterday) vs (2 days ago + 3 days ago).

    Returns [(group_label, pct_increase, topic_count)] sorted by surge descending.
    Only includes groups with >= MIN_TOPICS_PER_CATEGORY topics.
    """
    today, yesterday, two_ago, three_ago = _get_recent_dates()
    recent_dates = {today, yesterday}
    prior_dates = {two_ago, three_ago}

    groups: dict[str, dict] = {}
    for label in CATEGORY_GROUPS:
        groups[label] = {"recent": 0, "prior": 0, "count": 0}

    for story in stories:
        group = _get_category_group(story.get("category", ""))
        if group is None:
            continue
        groups[group]["count"] += 1

        trend = _parse_trend(story)
        for day in trend:
            d = day.get("date", "")
            c = day.get("count", 0)
            if d in recent_dates:
                groups[group]["recent"] += c
            elif d in prior_dates:
                groups[group]["prior"] += c

    result = []
    for label, g in groups.items():
        if g["count"] < MIN_TOPICS_PER_CATEGORY:
            continue
        if g["prior"] > 0:
            pct = (g["recent"] - g["prior"]) / g["prior"]
        elif g["recent"] > 0:
            pct = 1.0  # new activity from zero
        else:
            pct = 0.0
        result.append((label, pct, g["count"]))

    result.sort(key=lambda x: x[1], reverse=True)
    return result


# ── Topic-level fallbacks ────────────────────────────────────────────────────


def _find_top_gap_topic(stories: list[dict]) -> dict | None:
    """Find the single story with the largest impact-coverage gap."""
    best = None
    best_gap = -999
    for s in stories:
        impact = s.get("impact_score") or 0
        coverage = s.get("coverage_score") or s.get("attention_score") or 0
        gap = impact - coverage
        if gap > best_gap:
            best_gap = gap
            best = s
    return best if best and best_gap > 0 else None


def _find_top_velocity_topic(stories: list[dict]) -> dict | None:
    """Find the single story with the highest recent velocity spike."""
    today, yesterday, two_ago, three_ago = _get_recent_dates()
    recent_dates = {today, yesterday}
    prior_dates = {two_ago, three_ago}

    best = None
    best_ratio = -1

    for s in stories:
        trend = _parse_trend(s)
        recent = sum(d.get("count", 0) for d in trend if d.get("date") in recent_dates)
        prior = sum(d.get("count", 0) for d in trend if d.get("date") in prior_dates)

        if recent == 0:
            continue
        ratio = recent / prior if prior > 0 else float(recent)
        if ratio > best_ratio:
            best_ratio = ratio
            best = s

    return best if best and best_ratio > 1 else None


def _find_highest_impact_topic(stories: list[dict]) -> dict | None:
    """Find the story with the highest impact_score."""
    if not stories:
        return None
    return max(stories, key=lambda s: s.get("impact_score") or 0)


def _find_most_covered_topic(stories: list[dict]) -> dict | None:
    """Find the story with the highest coverage_score."""
    if not stories:
        return None
    return max(
        stories,
        key=lambda s: s.get("coverage_score") or s.get("attention_score") or 0,
    )


def _topic_label(story: dict) -> str:
    """Short display label for a story."""
    return (story.get("topic") or f"Story #{story.get('id', '?')}").strip()


# ── Haiku enhancement ────────────────────────────────────────────────────────


def _make_cache_key(insight: dict) -> str:
    """Fingerprint an insight by type + category for change detection."""
    return f"{insight.get('type', '')}:{insight.get('category', '')}"


def _get_top_topics_for_insight(
    insight: dict, stories: list[dict], n: int = 3,
) -> list[dict]:
    """Find the top N stories driving an insight.

    For undercovered: stories in the category with the highest impact-coverage gap.
    For surging: stories in the category with the highest recent velocity.
    """
    category = insight.get("category", "")
    insight_type = insight.get("type", "")

    # Filter stories to this category
    in_category = [
        s for s in stories
        if _get_category_group(s.get("category", "")) == category
    ] if category else stories

    if not in_category:
        in_category = stories

    if insight_type == "undercovered":
        # Sort by impact-coverage gap descending
        in_category.sort(
            key=lambda s: (s.get("impact_score") or 0)
            - (s.get("coverage_score") or s.get("attention_score") or 0),
            reverse=True,
        )
    else:
        # Sort by recent velocity / article count descending
        today, yesterday, _, _ = _get_recent_dates()
        recent_dates = {today, yesterday}

        def _recent_count(s):
            trend = _parse_trend(s)
            return sum(
                d.get("count", 0) for d in trend if d.get("date") in recent_dates
            )

        in_category.sort(key=_recent_count, reverse=True)

    return in_category[:n]


def _build_enhancement_context(insight: dict, stories: list[dict]) -> str:
    """Build the context string explaining WHY this insight was flagged."""
    category = insight.get("category", "")
    insight_type = insight.get("type", "")

    if insight_type == "undercovered":
        gaps = _compute_category_gaps(stories)
        for label, gap, count in gaps:
            if label == category:
                return f"average coverage gap of {gap:.0f} points across {count} topics in this category"
        # Fallback for topic-level insight
        return "this topic has high impact relative to its media coverage"

    else:  # surging
        surges = _compute_category_surges(stories)
        for label, pct, count in surges:
            if label == category:
                return f"48-hour article count increased {pct * 100:.0f}% across {count} topics in this category"
        return "this topic is seeing accelerating coverage"


def _enhance_insight_text(
    insight: dict,
    top_topics: list[dict],
    context: str,
) -> str | None:
    """Call Claude Haiku to produce a specific one-line description.

    Returns the enhanced text, or None on failure (caller keeps generic text).
    """
    try:
        from anthropic import Anthropic
        from config.settings import settings

        client = Anthropic(api_key=settings.anthropic_api_key)
    except Exception as exc:
        logger.warning("Cannot initialize Anthropic client for insight enhancement: %s", exc)
        return None

    insight_type = insight.get("type", "undercovered")
    category = insight.get("category", "")

    # Build topic lines
    topic_lines = []
    for t in top_topics:
        impact = t.get("impact_score") or 0
        coverage = t.get("coverage_score") or t.get("attention_score") or 0
        count = t.get("article_count") or 0
        topic_lines.append(
            f"- {_topic_label(t)} (impact: {impact:.0f}, coverage: {coverage:.0f}, {count} articles)"
        )

    topics_block = "\n".join(topic_lines) if topic_lines else "- No specific topics available"

    user_prompt = (
        f'Write a one-sentence insight for a "{insight_type}" alert.\n'
        f"Category: {category}\n"
        f"Top topics driving this:\n{topics_block}\n\n"
        f"Context: {context}\n\n"
        f"Write one neutral sentence (max 20 words) that names the specific "
        f"subject matter, not just the category."
    )

    try:
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=_MAX_TOKENS,
            system=(
                "You write concise, neutral news insight summaries for a dashboard. "
                "One sentence only. No editorializing. State what's happening factually."
            ),
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()

        # Sanity: strip quotes, ensure it's a single sentence
        text = text.strip('"\'')
        # If Haiku returned multiple sentences, take just the first
        if ". " in text:
            text = text.split(". ")[0] + "."

        if len(text) < 10 or len(text) > 200:
            logger.warning("Haiku insight text out of range (%d chars), falling back", len(text))
            return None

        return text

    except Exception as exc:
        logger.warning("Haiku insight enhancement failed: %s", exc)
        return None


def _enhance_insights(insights: list[dict], stories: list[dict]) -> list[dict]:
    """Enhance insight text via Haiku, with cache-key change detection.

    Only calls Haiku when the underlying insight data changed (different
    type+category than what's currently cached).  Otherwise reuses the
    cached enhanced text.
    """
    # Read current cache for change detection
    cached = get_cached_insights()
    cached_by_key: dict[str, dict] = {}
    for ci in cached:
        key = _make_cache_key(ci)
        cached_by_key[key] = ci

    for insight in insights:
        # Save generic text for fallback
        insight["generic_text"] = insight["text"]
        insight["cache_key"] = _make_cache_key(insight)

        cached_insight = cached_by_key.get(insight["cache_key"])

        if cached_insight and cached_insight.get("enhanced_text"):
            # Same type+category as last cycle — reuse cached enhanced text
            insight["enhanced_text"] = cached_insight["enhanced_text"]
            insight["text"] = cached_insight["enhanced_text"]
            logger.debug("Reusing cached enhanced text for %s", insight["cache_key"])
        else:
            # New or changed insight — call Haiku
            top_topics = _get_top_topics_for_insight(insight, stories)
            context = _build_enhancement_context(insight, stories)
            enhanced = _enhance_insight_text(insight, top_topics, context)

            if enhanced:
                insight["enhanced_text"] = enhanced
                insight["text"] = enhanced
                logger.info(
                    "Enhanced insight [%s]: %s", insight["cache_key"], enhanced[:80]
                )
            else:
                # Keep generic text
                insight["enhanced_text"] = ""
                logger.info(
                    "Kept generic text for [%s]: %s",
                    insight["cache_key"], insight["text"][:80],
                )

    return insights


# ── Main computation ─────────────────────────────────────────────────────────


def generate_insights() -> list[dict]:
    """Compute exactly 2 global insights from current data.

    Returns list of dicts: [{type, category, text, generic_text, cache_key, enhanced_text}].
    The frontend reads ``type``, ``category``, and ``text``.
    Results are cached in the insights_cache table.
    """
    stories = get_active_stories()
    if not stories:
        fallback = [
            {"type": "undercovered", "category": "", "text": "No active stories to analyze"},
            {"type": "surging", "category": "", "text": "No active stories to analyze"},
        ]
        set_cached_insights(fallback)
        return fallback

    insights: list[dict] = []

    # ── Insight 1: Undercovered ──────────────────────────────────────────

    category_gaps = _compute_category_gaps(stories)
    if category_gaps and category_gaps[0][1] > UNDERCOVERED_THRESHOLD:
        cat_label, gap, _ = category_gaps[0]
        insights.append({
            "type": "undercovered",
            "category": cat_label,
            "text": f"{cat_label} topics show the widest coverage gap this week",
        })
    else:
        # Fallback: individual topic with largest gap
        topic = _find_top_gap_topic(stories)
        if topic:
            insights.append({
                "type": "undercovered",
                "category": _get_category_group(topic.get("category", "")) or "",
                "text": (
                    f"{_topic_label(topic)} has high impact but limited "
                    f"coverage across sources"
                ),
            })

    # ── Insight 2: Surging ───────────────────────────────────────────────

    category_surges = _compute_category_surges(stories)
    if category_surges and category_surges[0][1] > SURGING_THRESHOLD:
        cat_label, pct, _ = category_surges[0]
        insights.append({
            "type": "surging",
            "category": cat_label,
            "text": f"{cat_label} coverage up significantly in the last 48 hours",
        })
    else:
        # Fallback: individual topic with highest velocity
        topic = _find_top_velocity_topic(stories)
        if topic:
            insights.append({
                "type": "surging",
                "category": _get_category_group(topic.get("category", "")) or "",
                "text": (
                    f"{_topic_label(topic)} is seeing a surge in coverage"
                ),
            })

    # ── Final fallback: ensure exactly 2 insights ────────────────────────

    if len(insights) == 0:
        # Both computations failed — use highest impact + most covered
        hi = _find_highest_impact_topic(stories)
        mc = _find_most_covered_topic(stories)
        if hi:
            insights.append({
                "type": "undercovered",
                "category": _get_category_group(hi.get("category", "")) or "",
                "text": f"{_topic_label(hi)} is the highest-impact topic this week",
            })
        if mc and (not hi or mc.get("id") != hi.get("id")):
            insights.append({
                "type": "surging",
                "category": _get_category_group(mc.get("category", "")) or "",
                "text": f"{_topic_label(mc)} is the most-covered topic this week",
            })

    if len(insights) == 1:
        # One computation succeeded, one failed — fill the gap
        existing_type = insights[0]["type"]
        if existing_type == "undercovered":
            mc = _find_most_covered_topic(stories)
            if mc:
                insights.append({
                    "type": "surging",
                    "category": _get_category_group(mc.get("category", "")) or "",
                    "text": f"{_topic_label(mc)} is the most-covered topic this week",
                })
        else:
            hi = _find_highest_impact_topic(stories)
            if hi:
                insights.insert(0, {
                    "type": "undercovered",
                    "category": _get_category_group(hi.get("category", "")) or "",
                    "text": f"{_topic_label(hi)} is the highest-impact topic this week",
                })

    # Guarantee exactly 2
    while len(insights) < 2:
        insights.append({
            "type": "surging" if len(insights) == 1 else "undercovered",
            "category": "",
            "text": "Monitoring coverage patterns across sources",
        })
    insights = insights[:2]

    # ── Haiku enhancement (optional, cached) ─────────────────────────────

    insights = _enhance_insights(insights, stories)

    # ── Cache ────────────────────────────────────────────────────────────

    set_cached_insights(insights)
    logger.info(
        "Generated %d insights: [%s] [%s]",
        len(insights),
        insights[0].get("text", "")[:60],
        insights[1].get("text", "")[:60],
    )

    return insights


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = generate_insights()
    print(f"\nGenerated {len(result)} insights:\n")
    for insight in result:
        enhanced = " (enhanced)" if insight.get("enhanced_text") else " (generic)"
        print(f"  [{insight['type']}]{enhanced} {insight['text']}")
        if insight.get("generic_text") and insight.get("enhanced_text"):
            print(f"           generic: {insight['generic_text']}")
        if insight.get("category"):
            print(f"           category: {insight['category']}")
    print()
