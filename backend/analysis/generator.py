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

MIN_ARTICLES = 3
STALE_GROWTH_RATIO = 0.30
STALE_HOURS = 12
MAX_ARTICLES_PER_ANALYSIS = 8
MAX_BODY_WORDS = 300

BIAS_LABELS = {
    "far-left": "LEFT",
    "left": "LEFT",
    "left-center": "LEFT-CENTER",
    "center": "CENTER",
    "right-center": "RIGHT-CENTER",
    "right": "RIGHT",
    "far-right": "RIGHT",
}

SYSTEM_PROMPT = (
    "You are a news analyst for ClearSignal, a platform that shows readers "
    "how the same story is covered across the political spectrum. Your "
    "analysis must be rigorously neutral. You describe patterns — you do "
    "not evaluate whether coverage is 'good,' 'bad,' 'sufficient,' or "
    "'insufficient.' You never tell readers what to think.\n\n"
    "NEUTRALITY PRINCIPLES:\n"
    "- Attribute all contested claims to their source: 'according to "
    "[outlet]' or 'as reported by [outlet].'\n"
    "- When sources disagree on facts, state both versions without "
    "adjudicating.\n"
    "- Do not use emotional or evaluative adjectives (devastating, "
    "unprecedented, controversial, alarming, historic) unless directly "
    "quoting a source and attributing the quote.\n"
    "- Do not infer motives for why outlets covered or framed a story "
    "a particular way.\n"
    "- If all sources agree on framing, say so. Do not fabricate "
    "disagreement.\n"
    "- Acknowledge when information is incomplete, developing, or "
    "uncertain.\n"
    "- Do not reference political lean labels (left, right, center). "
    "Describe what outlets emphasize, not where they fall on a spectrum.\n\n"
    "WRITING STYLE:\n"
    "- Write in clear, direct prose. Vary sentence length — short declarative "
    "sentences mixed with longer explanatory ones create rhythm.\n"
    "- Lead every paragraph with its most important point. Do not bury the key "
    "information in the middle or end of a paragraph.\n"
    "- Use concrete details over abstract descriptions. '14 sources covered this, "
    "but only 3 mentioned the cost estimates' is better than 'coverage varied "
    "across outlets.'\n"
    "- Use transitions between paragraphs. The analysis should read as a narrative, "
    "not disconnected blocks of information.\n"
    "- Avoid bureaucratic language. Never use: 'it should be noted that,' "
    "'it is worth mentioning,' 'with respect to,' 'in terms of,' "
    "'it is important to note,' 'it bears mentioning.' Just state the fact.\n"
    "- Avoid hedge stacking. Do not write 'it appears that sources may potentially "
    "suggest...' — write 'several sources suggest...' One hedge per claim maximum.\n"
    "- Avoid beginning consecutive sentences or paragraphs with the same word.\n"
    "- Do not use the phrase 'it remains to be seen.' State what is uncertain "
    "directly: 'The timeline is unclear' or 'No official figure has been released.'\n\n"
    "Respond in JSON only. No markdown, no preamble."
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

        # Classify per-article framing before building the analysis prompt
        article_framings = []
        try:
            from analysis.framing import classify_article_framings
            article_framings = classify_article_framings(articles)
        except Exception as exc:
            logger.warning("Framing classification failed for story %d: %s", story_id, exc)

        system, user_msg = _build_sonnet_prompt(story, articles, article_framings)
        parsed = _call_sonnet(client, system, user_msg)

        if parsed is None:
            logger.error("Failed to generate analysis for story %d (%s)", story_id, topic)
            result["errors"] += 1
            continue

        spectrum = parsed.get("spectrum", "")
        coverage_note = parsed.get("coverage_note", "") or spectrum
        analysis_data = {
            "story_id": story_id,
            "headline": parsed.get("headline", ""),
            "dateline": parsed.get("dateline", ""),
            "lede": parsed.get("lede", ""),
            "context": parsed.get("context", ""),
            "source_framings": parsed.get("source_framings", []),
            "contrasts": parsed.get("contrasts", []),
            "facts": parsed.get("facts", []),
            "bottom_line": parsed.get("bottom_line", ""),
            "spectrum": spectrum,
            "coverage_note": coverage_note,
            "framing_check": parsed.get("framing_check", ""),
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
    """Check if a story needs a new or updated analysis."""
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


def _get_article_lean(article: dict) -> str:
    """Get the political lean bucket for an article."""
    domain = article.get("source_domain", "")
    bias_info = SOURCE_BIAS.get(domain)
    label = bias_info["label"] if bias_info else "center"
    return BIAS_LABELS.get(label, "CENTER")


def _lean_diversity_score(articles: list[dict]) -> float:
    """Score 0-1 based on how many different political leans cover this story."""
    leans: set[str] = set()
    for a in articles:
        lean = _get_article_lean(a)
        if "LEFT" in lean:
            leans.add("left")
        if "CENTER" in lean:
            leans.add("center")
        if "RIGHT" in lean:
            leans.add("right")
    return {0: 0.0, 1: 0.2, 2: 0.6, 3: 1.0}.get(len(leans), 0.0)


def _select_articles(articles: list[dict]) -> list[dict]:
    """Select up to MAX_ARTICLES_PER_ANALYSIS articles for the prompt.

    Strategy:
    1. Pick 1 article from each available political lean
    2. Fill remaining slots with most recent articles
    3. Always include earliest and most recent article
    """
    if len(articles) <= MAX_ARTICLES_PER_ANALYSIS:
        return articles

    selected: list[dict] = []
    selected_ids: set[int] = set()

    # Sort by published_at for recency
    sorted_by_date = sorted(
        articles,
        key=lambda a: a.get("published_at") or "",
        reverse=True,
    )

    # Always include most recent article
    if sorted_by_date:
        selected.append(sorted_by_date[0])
        selected_ids.add(sorted_by_date[0].get("id"))

    # Always include earliest article
    earliest = sorted_by_date[-1] if sorted_by_date else None
    if earliest and earliest.get("id") not in selected_ids:
        selected.append(earliest)
        selected_ids.add(earliest.get("id"))

    # Group by lean, pick one from each
    lean_groups: dict[str, list[dict]] = {}
    for a in articles:
        lean = _get_article_lean(a)
        lean_groups.setdefault(lean, []).append(a)

    for lean, group in lean_groups.items():
        if len(selected) >= MAX_ARTICLES_PER_ANALYSIS:
            break
        # Pick the article with the most body text from this lean
        group.sort(key=lambda a: len(a.get("body") or ""), reverse=True)
        for a in group:
            if a.get("id") not in selected_ids:
                selected.append(a)
                selected_ids.add(a.get("id"))
                break

    # Fill remaining slots with most recent articles
    for a in sorted_by_date:
        if len(selected) >= MAX_ARTICLES_PER_ANALYSIS:
            break
        if a.get("id") not in selected_ids:
            selected.append(a)
            selected_ids.add(a.get("id"))

    return selected


def _format_article_content(article: dict) -> str:
    """Format a single article for the prompt — source + title + description + body excerpt.

    NOTE: Bias labels are intentionally NOT included in the prompt context.
    The LLM should classify framing from article text alone, without
    knowing the outlet's political lean label (CONFLICT-05 resolution).
    """
    source = article.get("source_name") or article.get("source_domain", "unknown")
    title = article.get("title", "(no title)")
    published = article.get("published_at", "")

    parts = [f"Source: {source}"]
    parts.append(f"Headline: {title}")
    if published:
        parts.append(f"Published: {published}")

    desc = (article.get("description") or "").strip()
    if desc:
        parts.append(desc)

    body = (article.get("body") or "").strip()
    if body:
        words = body.split()
        excerpt = " ".join(words[:MAX_BODY_WORDS])
        if len(words) > MAX_BODY_WORDS:
            excerpt += "..."
        parts.append(f"Excerpt: {excerpt}")

    return "\n".join(parts)


def _prioritise(stories: list[dict]) -> list[dict]:
    """Sort candidates by composite priority.

    New formula: significance threshold + category weight + diversity + impact + staleness.
    """

    def sort_key(story: dict) -> float:
        # Skip low-significance stories
        sig = story.get("significance_score") or 0
        if sig > 0 and sig < settings.min_significance_score:
            return 0.0  # will sort last

        has_analysis = get_analysis(story["id"]) is not None
        impact = (story.get("impact_score") or 0) / 100.0

        cat = (story.get("category") or "").strip()
        cat_weight = {
            # Full category names (new format)
            "Politics & Law": 1.0,
            "World & Security": 0.9,
            "Science & Health": 0.8,
            "Economy & Business": 0.6,
            # Legacy uppercase keys (backward compat)
            "POLITICS": 1.0, "LAW": 1.0,
            "WORLD": 0.9, "MILITARY": 0.9,
            "HEALTH": 0.8, "SCIENCE": 0.8,
            "BUSINESS": 0.6, "ECONOMY": 0.6,
        }.get(cat, 0.1)

        articles = get_articles_for_story(story["id"])
        diversity = _lean_diversity_score(articles)

        # Staleness tier
        article_count = story.get("article_count") or 0
        if not has_analysis and (story.get("impact_score") or 0) >= 50:
            tier = 0
        elif not has_analysis and article_count >= 10:
            tier = 1
        elif has_analysis:
            tier = 2
        else:
            tier = 3
        staleness = 1.0 - (tier / 3.0)

        score = impact * 0.3 + diversity * 0.3 + cat_weight * 0.2 + staleness * 0.2
        return -score  # negate so higher score sorts first

    return sorted(stories, key=sort_key)


def _build_sonnet_prompt(
    story: dict,
    articles: list[dict],
    article_framings: list[dict] | None = None,
) -> tuple[str, str]:
    """Build system prompt and user message for Claude Sonnet.

    Sends article CONTENT (title + description + first 300 words of body)
    for up to 8 selected articles, plus optional per-article framing data.

    Returns: (system_prompt, user_message)
    """
    # Select articles
    selected = _select_articles(articles)

    # Format article content sections
    article_sections = []
    for a in selected:
        article_sections.append(_format_article_content(a))
        article_sections.append("---")

    # Unique source count
    source_domains = {a.get("source_domain") for a in articles if a.get("source_domain")}
    source_count = len(source_domains)

    # Build significance factors context if available
    sig_factors = story.get("significance_factors")
    sig_factors_str = ""
    if sig_factors:
        if isinstance(sig_factors, str):
            sig_factors_str = sig_factors
        else:
            sig_factors_str = json.dumps(sig_factors)

    # Build user message
    user_msg = (
        f"Analyze this story for ClearSignal readers.\n\n"
        f"Story: {story.get('topic', 'Unknown')}\n"
        f"Category: {story.get('category', 'unknown')}\n"
        f"Impact score: {story.get('impact_score', 0)}/100"
        + (f" (factors: {sig_factors_str})" if sig_factors_str else "")
        + f"\nAttention score: {story.get('attention_score', 0)}/100\n"
        f"Number of articles: {len(articles)} from {source_count} sources\n\n"
        f"Article excerpts (first {MAX_BODY_WORDS} words each, "
        f"{len(selected)} of {len(articles)}):\n\n"
        + "\n".join(article_sections)
        + "\n\n"
        + (
            "Per-article framing analysis (pre-computed):\n"
            + "\n".join(
                f"- {f['source']}: primary framing = {f['primary_framing']}, "
                f"notable inclusions = {f['notable_inclusions']}, "
                f"notable omissions = {f['notable_omissions']}"
                for f in (article_framings or [])
            )
            + "\n\n"
            if article_framings
            else ""
        )
        + "Produce the following fields. Respond ONLY with valid JSON, "
        "no markdown, no preamble:\n\n"
        "{\n"
        '  "headline": "<max 12 words, neutral, factual, no emotional adjectives>",\n'
        '  "lede": "<2-3 sentences, max 60 words. First sentence answers who/what/when/where. '
        "Second sentence adds the key tension or significance. Write like the opening of "
        'a wire service dispatch — tight, factual, immediately clear. No throat-clearing.>",\n'
        '  "context": "<4-6 paragraphs. Write as a narrative briefing, not a list of facts. '
        "Start with the immediate situation. Then layer in background that helps the reader "
        "understand why this matters. Each paragraph should build on the previous one. "
        "Use specific numbers, dates, and names — not vague summaries. End with what "
        "remains uncertain or unresolved. The reader should feel informed, not lectured. "
        'Draw extensively on the article excerpts. Attribute claims.>",\n'
        '  "source_framings": [\n'
        "    {\n"
        '      "source": "outlet name",\n'
        '      "framings": ["economic impact", "policy/regulatory"],\n'
        '      "primary_framing": "economic impact",\n'
        '      "notable_inclusions": "Facts/angles present here but absent from others, or none identified",\n'
        '      "notable_omissions": "Facts/angles in other articles but absent here, or none identified"\n'
        "    }\n"
        "  ],\n"
        '  "contrasts": [\n'
        "    {\n"
        '      "theme": "What differs: e.g., cause attributed, proposed solution, affected group emphasized",\n'
        '      "sourceA": "outlet name",\n'
        '      "framingA": "economic impact",\n'
        '      "claimA": "Quote or closely paraphrase the source actual language. Be specific about what they emphasize or omit.",\n'
        '      "sourceB": "outlet with DIFFERENT framing",\n'
        '      "framingB": "social/cultural impact",\n'
        '      "claimB": "Quote or closely paraphrase. Show the actual framing difference through content, not meta-commentary."\n'
        "    }\n"
        "  ],\n"
        '  "facts": [\n'
        "    {\n"
        '      "claim": "A specific factual claim from coverage",\n'
        '      "reality": "What verifiable facts show",\n'
        '      "verdict": "confirmed | misleading | lacks context | unverified"\n'
        "    }\n"
        "  ],\n"
        '  "bottom_line": "<3-4 sentences maximum. Be direct. First sentence: what is happening '
        "right now. Second: why it matters to the reader concretely. Third: what to watch for "
        "next. No hedging, no filler, no 'it remains to be seen.' This should read like a "
        'sharp summary a trusted editor would give you verbally.>",\n'
        '  "spectrum": "<1-2 sentences. State the coverage pattern with numbers: how many sources '
        "from each part of the spectrum covered this, whether any notable perspective is "
        "missing. Be specific — 'covered by 8 left-leaning and 3 right-leaning outlets, "
        "with center sources largely absent' is better than 'coverage skewed left.' "
        'Descriptive only.>",\n'
        '  "coverage_note": "<1 sentence: This story was covered by N sources. '
        "Coverage volume is [higher than / lower than / roughly proportional to] "
        'estimated real-world impact. No editorializing beyond this.>",\n'
        '  "framing_check": "<Internal audit: what framing choices did you make, '
        "and what alternatives did you consider? For transparency logging, "
        'not user display.>"\n'
        "}\n\n"
        "IMPORTANT:\n"
        "- If all articles share the same framing and there are no meaningful "
        'contrasts, return "contrasts": [] and note this in spectrum.\n'
        "- If fewer than 3 articles are available, add to coverage_note: "
        '"Based on limited source sample (N articles)."\n'
        "- Do not reference political lean labels (left, right, center). "
        "Describe what outlets emphasize, not where they fall on a spectrum."
    )

    return SYSTEM_PROMPT, user_msg


def _call_sonnet(client: Anthropic, system: str, user_msg: str) -> dict | None:
    """Call Claude Sonnet and parse structured JSON response.

    Retries once on parse failure with a corrective nudge.
    Returns parsed dict or None.
    """
    model = settings.claude_model
    max_tokens = settings.max_analysis_tokens

    for attempt in range(2):
        try:
            messages = [{"role": "user", "content": user_msg}]
            if attempt == 1:
                messages = [
                    {"role": "user", "content": user_msg + "\n\nPlease respond in valid JSON only."}
                ]

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
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
