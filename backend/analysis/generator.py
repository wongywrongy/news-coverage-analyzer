"""Generate neutral, wire-service-style analyses for news stories using Claude Sonnet.

This is the product's primary output — what users read on ClearSignal.
Each analysis synthesizes coverage from across the political spectrum into
a single, neutral, AP-style briefing with bias contrasts and fact checks.
"""

import json
import logging
from datetime import datetime, timezone

from anthropic import Anthropic

from config.settings import settings
from config.sources import SOURCE_BIAS
from db.queries import (
    get_active_stories,
    get_analysis,
    get_articles_for_story,
    upsert_analysis,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 2000
MIN_ARTICLES = 3
STALE_GROWTH_RATIO = 0.30
STALE_HOURS = 12
MAX_HEADLINES_PER_GROUP = 8

BIAS_BUCKETS = {
    "LEFT / FAR-LEFT": ("far-left", "left"),
    "LEFT-CENTER": ("left-center",),
    "CENTER": ("center",),
    "RIGHT-CENTER": ("right-center",),
    "RIGHT / FAR-RIGHT": ("right", "far-right"),
}

SYSTEM_PROMPT = (
    "You are a wire-service journalist writing for ClearSignal, a platform "
    "that helps readers see through media bias. Your job is to write a "
    "neutral, factual analysis of a news story based on how multiple outlets "
    "across the political spectrum are covering it.\n\n"
    "RULES:\n"
    "- Write in AP/Reuters wire-service style: factual, neutral, no editorializing\n"
    "- Never use opinion language: 'shocking', 'alarming', 'exciting', 'controversial'\n"
    "- Never take sides. Present what each side claims, let the reader decide.\n"
    "- Use active voice and short sentences\n"
    "- Attribute claims to their sources: 'CNN reported...', 'Fox News characterized...'\n"
    "- When outlets disagree on framing, present both framings without judgment\n"
    "- The 'bottom_line' should describe concrete impact on ordinary people\n"
    "- The 'coverage_note' should reference actual data: article count, source count, "
    "which parts of the spectrum are covering it and which aren't\n\n"
    "Respond in JSON only. No other text."
)


# ── Public API ──────────────────────────────────────────────


def generate_analyses(
    story_ids: list[int] | None = None,
    max_per_cycle: int = 5,
    force: bool = False,
) -> dict:
    """Generate neutral analyses for stories that need them.

    If story_ids is None, pick the top stories by priority:
    - Stories with no analysis yet (highest priority)
    - Stories whose analysis is stale (article count grew >30%)
    - Sort by impact_score descending (most important first)
    - Cap at max_per_cycle to control API costs

    If force=True, regenerate even if analysis exists and is fresh.

    Returns: {
        "generated": int,
        "skipped": int,
        "errors": int,
        "analyses": list[dict]  # [{story_id, headline}]
    }
    """
    result: dict = {"generated": 0, "skipped": 0, "errors": 0, "analyses": []}

    stories = _resolve_stories(story_ids)
    if not stories:
        logger.info("No stories to analyse")
        return result

    # Filter and prioritise
    if force:
        candidates = stories
    else:
        candidates = [s for s in stories if _needs_analysis(s)]

    candidates = _prioritise(candidates)[:max_per_cycle]
    logger.info("Analysis cycle: %d candidates (force=%s)", len(candidates), force)

    client = Anthropic(api_key=settings.anthropic_api_key)

    for story in candidates:
        story_id = story["id"]
        topic = story.get("topic", f"story-{story_id}")

        articles = get_articles_for_story(story_id)
        if len(articles) < MIN_ARTICLES:
            logger.info("Skipping story %d (%s): only %d articles", story_id, topic, len(articles))
            result["skipped"] += 1
            continue

        system, user_msg = _build_sonnet_prompt(story, articles)
        parsed = _call_sonnet(client, system, user_msg)

        if parsed is None:
            logger.error("Failed to generate analysis for story %d (%s)", story_id, topic)
            result["errors"] += 1
            continue

        analysis_data = {
            "story_id": story_id,
            "headline": parsed.get("headline", ""),
            "dateline": parsed.get("dateline", ""),
            "lede": parsed.get("lede", ""),
            "context": parsed.get("context", ""),
            "contrasts": parsed.get("contrasts", []),
            "facts": parsed.get("facts", []),
            "bottom_line": parsed.get("bottom_line", ""),
            "coverage_note": parsed.get("coverage_note", ""),
            "article_count_at_gen": story.get("article_count") or len(articles),
        }

        upsert_analysis(analysis_data)
        result["generated"] += 1
        result["analyses"].append({"story_id": story_id, "headline": analysis_data["headline"]})
        logger.info("Generated analysis for story %d: %s", story_id, analysis_data["headline"])

    logger.info(
        "Analysis cycle complete: generated=%d skipped=%d errors=%d",
        result["generated"],
        result["skipped"],
        result["errors"],
    )
    return result


# ── Internals ───────────────────────────────────────────────


def _resolve_stories(story_ids: list[int] | None) -> list[dict]:
    """Fetch stories — either specific IDs or all active stories."""
    all_stories = get_active_stories()
    if story_ids is None:
        return all_stories
    id_set = set(story_ids)
    return [s for s in all_stories if s["id"] in id_set]


def _needs_analysis(story: dict) -> bool:
    """Check if a story needs a new or updated analysis.

    Returns True if:
    - Story has >= MIN_ARTICLES articles AND no analysis exists
    - Article count grew >30% since last generation
    - Analysis is older than 12 hours AND story has new articles

    Returns False if:
    - Story has fewer than MIN_ARTICLES articles
    - Analysis exists and is fresh
    """
    article_count = story.get("article_count") or 0
    if article_count < MIN_ARTICLES:
        return False

    existing = get_analysis(story["id"])
    if existing is None:
        return True

    # Check growth ratio
    prev_count = existing.get("article_count_at_gen") or 0
    if prev_count > 0 and article_count > prev_count * (1 + STALE_GROWTH_RATIO):
        return True

    # Check age + new articles
    generated_at = existing.get("generated_at")
    if generated_at and article_count > prev_count:
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
        if age_hours > STALE_HOURS:
            return True

    return False


def _prioritise(stories: list[dict]) -> list[dict]:
    """Sort candidates by analysis priority.

    Priority tiers (descending):
    1. No analysis + impact_score >= 50
    2. No analysis + article_count >= 10
    3. Stale analysis (grew >30%)
    4. Everything else by impact_score descending
    """

    def sort_key(story: dict) -> tuple:
        has_analysis = get_analysis(story["id"]) is not None
        impact = story.get("impact_score") or 0
        article_count = story.get("article_count") or 0

        if not has_analysis and impact >= 50:
            tier = 0
        elif not has_analysis and article_count >= 10:
            tier = 1
        elif has_analysis:
            tier = 2
        else:
            tier = 3

        return (tier, -impact)

    return sorted(stories, key=sort_key)


def _build_sonnet_prompt(story: dict, articles: list[dict]) -> tuple[str, str]:
    """Build system prompt and user message for Claude Sonnet.

    Groups articles by bias bucket, formats headlines, and assembles
    the structured user message.

    Returns: (system_prompt, user_message)
    """
    # Group articles by bias bucket
    buckets: dict[str, list[dict]] = {name: [] for name in BIAS_BUCKETS}

    for article in articles:
        domain = article.get("source_domain", "")
        bias_info = SOURCE_BIAS.get(domain)
        label = bias_info["label"] if bias_info else "center"
        placed = False
        for bucket_name, labels in BIAS_BUCKETS.items():
            if label in labels:
                buckets[bucket_name].append(article)
                placed = True
                break
        if not placed:
            buckets["CENTER"].append(article)

    # For large stories, sample headlines
    for bucket_name in buckets:
        arts = buckets[bucket_name]
        # Sort by recency
        arts.sort(key=lambda a: a.get("published_at") or "", reverse=True)
        if len(arts) > MAX_HEADLINES_PER_GROUP:
            buckets[bucket_name] = arts[:MAX_HEADLINES_PER_GROUP]

    # Format headline sections
    headline_sections = []
    for bucket_name in BIAS_BUCKETS:
        arts = buckets[bucket_name]
        count = len(arts)
        headline_sections.append(f"{bucket_name} ({count}):")
        if count == 0:
            headline_sections.append("(no coverage from this segment)")
        else:
            for a in arts:
                domain = a.get("source_domain", "unknown")
                title = a.get("title", "(no title)")
                headline_sections.append(f"  - [{domain}] {title}")
        headline_sections.append("")

    # Unique source count
    source_domains = {a.get("source_domain") for a in articles if a.get("source_domain")}
    source_count = len(source_domains)

    # Build user message
    user_msg = (
        f"STORY: {story.get('topic', 'Unknown')}\n"
        f"IMPACT SCORE: {story.get('impact_score', 0)}/100\n"
        f"ATTENTION SCORE: {story.get('attention_score', 0)}/100\n"
        f"STATUS: {story.get('status', 'unknown')}\n"
        f"ARTICLES: {len(articles)} from {source_count} sources\n\n"
        f"HEADLINES BY POLITICAL LEAN:\n\n"
        + "\n".join(headline_sections)
        + f"SENTIMENT: left={story.get('sentiment_left', 'n/a')}, "
        f"center={story.get('sentiment_center', 'n/a')}, "
        f"right={story.get('sentiment_right', 'n/a')}\n\n"
        'Generate a neutral analysis in this JSON format:\n'
        "{\n"
        '  "headline": "Neutral 8-15 word headline, no opinion words, AP style",\n'
        '  "dateline": "CITY (ClearSignal)",\n'
        '  "lede": "2-3 sentence lede answering who/what/when/where. Factual only.",\n'
        '  "context": "2-3 sentences of background. Why does this matter? What led to this?",\n'
        '  "contrasts": [\n'
        "    {\n"
        '      "theme": "What aspect of the story outlets disagree on",\n'
        '      "sourceA": "outlet name",\n'
        '      "biasA": "left-center",\n'
        '      "claimA": "How this outlet frames/reports it",\n'
        '      "sourceB": "another outlet",\n'
        '      "biasB": "right-center",\n'
        '      "claimB": "How this outlet frames/reports it"\n'
        "    }\n"
        "  ],\n"
        '  "facts": [\n'
        "    {\n"
        '      "claim": "A specific factual claim made in coverage",\n'
        '      "reality": "What the verifiable facts show",\n'
        '      "verdict": "confirmed | misleading | lacks context | unverified"\n'
        "    }\n"
        "  ],\n"
        '  "bottom_line": "1-2 sentences: concrete consequences for ordinary people. No jargon.",\n'
        '  "coverage_note": "Reference actual numbers: X articles from Y sources. Note which '
        "political leans are covering this and which aren't. Note if coverage volume matches "
        'the story\'s real-world significance."\n'
        "}"
    )

    return SYSTEM_PROMPT, user_msg


def _call_sonnet(client: Anthropic, system: str, user_msg: str) -> dict | None:
    """Call Claude Sonnet and parse structured JSON response.

    Retries once on parse failure with a corrective nudge.
    Returns parsed dict or None.
    """
    for attempt in range(2):
        try:
            messages = [{"role": "user", "content": user_msg}]
            if attempt == 1:
                messages.append({"role": "assistant", "content": "{"})
                # Retry nudge: ask for valid JSON
                messages = [
                    {"role": "user", "content": user_msg + "\n\nPlease respond in valid JSON only."}
                ]

            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages,
            )
            raw = response.content[0].text
            parsed = _parse_response(raw)

            if parsed is not None:
                return parsed

            if attempt == 0:
                logger.warning("Invalid JSON from Sonnet (attempt 1), retrying")

        except Exception:
            logger.exception("Sonnet API error (attempt %d)", attempt + 1)
            if attempt == 0:
                continue
            return None

    logger.error("Failed to get valid JSON from Sonnet after 2 attempts")
    return None


def _parse_response(raw: str) -> dict | None:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    text = raw.strip()

    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s", exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Sonnet response is not a JSON object")
        return None

    # Validate required fields exist (use defaults for missing)
    required = ("headline", "lede", "bottom_line")
    missing = [f for f in required if not data.get(f)]
    if missing:
        logger.warning("Sonnet response missing key fields: %s", missing)
        return None

    return data


# ── Entry point ─────────────────────────────────────────────


if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
    )

    stories = get_active_stories()
    if not stories:
        print("No active stories found")
        sys.exit(0)

    top_ids = [
        s["id"]
        for s in sorted(stories, key=lambda s: s.get("impact_score") or 0, reverse=True)[:3]
    ]
    print(f"Generating analyses for top {len(top_ids)} stories: {top_ids}")

    result = generate_analyses(story_ids=top_ids)
    print(f"\nGenerated: {result['generated']}")
    print(f"Skipped:   {result['skipped']}")
    print(f"Errors:    {result['errors']}")
    for a in result["analyses"]:
        print(f"\n  Story #{a['story_id']}:")
        print(f"  Headline: {a['headline']}")
