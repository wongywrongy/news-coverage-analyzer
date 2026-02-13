"""Score real-world significance of news stories using Claude Haiku.

Each story gets a 0-100 significance score based on five weighted factors:
  - Population directly affected (0-30)
  - Economic magnitude (0-25)
  - Policy/regulatory change (0-20)
  - Duration of effect (0-15)
  - Irreversibility (0-10)

Returns a full factor breakdown with per-factor rationale, confidence
level, and insufficient-data flags.

Cost: ~$0.002 per story (Haiku input + output tokens).
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime

from anthropic import Anthropic

from config.settings import settings
from constants import ENTITY_BOOST_CAP, ENTITY_BOOST_FACTOR, RESCORE_GROWTH_THRESHOLD, RESCORE_HOURS
from db import queries as db
from db.queries import get_entities_for_topic, get_top_connected_entities

logger = logging.getLogger(__name__)

_HAIKU_MODEL = settings.haiku_model
_MAX_TOKENS = 1024
_MAX_HEADLINES = 50
_RESCORE_HOURS = RESCORE_HOURS
_GROWTH_THRESHOLD = RESCORE_GROWTH_THRESHOLD

_SYSTEM_PROMPT = (
    "You are a news significance scorer for a US-focused news analysis platform. "
    "You evaluate the real-world impact of a news story using 5 measurable factors, "
    "with particular attention to how it affects the United States and US interests. "
    "You are descriptive, not prescriptive. You do not judge whether a story "
    "'deserves' coverage — you estimate its tangible impact on people and systems.\n\n"
    "AUDIENCE CONTEXT: Your scores should reflect importance to a US audience. "
    "For international stories, weight the US connection: direct effects on US "
    "policy, economy, security, or citizens score higher than events with no "
    "US nexus. Global events that affect world markets, alliances, or set "
    "precedents for US issues are still significant."
)

# ─── helpers ────────────────────────────────────────────────────────────────────


def _needs_scoring(story: dict) -> bool:
    """Determine if a story needs (re)scoring.

    Returns True if:
    - impact_score is 0, None, or missing
    - article_count increased >20% since last scored count
    - Last scored >6 hours ago AND story has new articles
    """
    score = story.get("impact_score")
    if score is None or score == 0:
        return True

    # Check article count growth since last score
    current_count = story.get("article_count") or 0
    scored_count = story.get("scored_at_article_count") or 0
    if scored_count > 0 and current_count > 0:
        growth = (current_count - scored_count) / scored_count
        if growth > _GROWTH_THRESHOLD:
            return True

    # Check staleness: last scored >6h ago AND has new articles
    last_scored = story.get("impact_scored_at")
    if last_scored and current_count > scored_count:
        if isinstance(last_scored, str):
            try:
                last_scored = datetime.fromisoformat(last_scored)
            except ValueError:
                return True
        if last_scored.tzinfo is None:
            last_scored = last_scored.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - last_scored).total_seconds() / 3600
        if age_hours > _RESCORE_HOURS:
            return True

    return False


def _is_stale_story(story: dict) -> bool:
    """Check if story is too old and inactive to score."""
    first_seen = story.get("first_seen")
    if not first_seen:
        return False
    if isinstance(first_seen, str):
        try:
            first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        except ValueError:
            return False
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=UTC)
    age_days = (datetime.now(UTC) - first_seen).days
    if age_days > 7 and story.get("status") == "stale":
        return True
    return False


def _build_prompt(story: dict, articles: list[dict]) -> str:
    """Build the Claude Haiku user prompt for 5-factor significance scoring.

    Sends article headlines and excerpts (first 150 words) without any
    bias labels or political grouping.
    """
    topic = story.get("topic") or "(unknown topic)"

    # Cap at 50 most recent articles (already sorted newest-first from DB)
    display_articles = articles[:_MAX_HEADLINES]

    # Format each article: "- {headline} ({source_name}): \"{first_150_words}\""
    lines: list[str] = []
    for a in display_articles:
        source = a.get("source_name") or "unknown"
        title = a.get("title") or "(no title)"
        # Build excerpt from body or description
        body = (a.get("body") or a.get("description") or "").strip()
        words = body.split()
        excerpt = " ".join(words[:150]) if words else ""
        if excerpt:
            lines.append(f'- {title} ({source}): "{excerpt}"')
        else:
            lines.append(f"- {title} ({source})")

    articles_block = "\n".join(lines) if lines else "(no articles)"

    # Build entity context
    story_id = story.get("id")
    entity_context = ""
    if story_id:
        entities = get_entities_for_topic(story_id)
        if entities:
            ent_lines = []
            for ent in entities:
                eid = ent.get("id")
                name = ent.get("canonical_name", "unknown")
                etype = ent.get("entity_type", "")
                importance = ent.get("importance", 0)
                topic_count = ent.get("topic_count", 0)
                connected = get_top_connected_entities(eid) if eid else []
                connected_str = ", ".join(c["name"] for c in connected) if connected else "none"
                ent_lines.append(
                    f"- {name} ({etype}, importance: {importance:.0f})\n"
                    f"  Connected to: {connected_str}\n"
                    f"  Appears in {topic_count} other topics"
                )
            entity_context = (
                "\n\nEntity connections for this topic:\n"
                + "\n".join(ent_lines)
                + "\n\nConsider how this topic's connection to established storylines "
                "affects its real-world importance. A procedural event that advances "
                "or threatens a high-importance storyline should score higher than "
                "its headline suggests.\n"
            )

    return (
        f"Evaluate the significance of this news story.\n\n"
        f"Story title: {topic}\n"
        f"Article headlines and excerpts:\n"
        f"{articles_block}\n"
        f"{entity_context}\n"
        "Score each factor from 0 to its maximum. Base scores ONLY on facts "
        "stated or directly implied in the articles. If a factor cannot be "
        "scored from available information, score it 0 and list it in "
        "insufficient_data.\n\n"
        "Factors:\n"
        "1. population_affected (0-30): Number of people who experience "
        "direct, tangible consequences. Score 5 for < 1,000; 10 for "
        "1,000-100,000; 15 for 100K-1M; 20 for 1M-50M; 25 for 50M-500M; "
        "30 for > 500M.\n"
        "2. economic_magnitude (0-25): Verified or reasonably estimated "
        "financial impact. Score 5 for < $10M; 10 for $10M-$1B; 15 for "
        "$1B-$50B; 20 for $50B-$500B; 25 for > $500B.\n"
        "3. policy_change (0-20): Does this create, alter, or remove laws, "
        "regulations, treaties, or institutional rules? Score 0 for no "
        "policy dimension; 10 for proposed/pending change; 15 for enacted "
        "change affecting one jurisdiction; 20 for enacted change affecting "
        "multiple jurisdictions or international scope.\n"
        "4. duration (0-15): How long will the effects persist? Score 3 "
        "for < 1 week; 6 for 1 week-1 month; 9 for 1-12 months; 12 for "
        "1-10 years; 15 for > 10 years or permanent.\n"
        "5. irreversibility (0-10): Can the effects be undone? Score 0 for "
        "fully reversible; 5 for partially reversible with significant "
        "effort; 10 for irreversible (e.g., deaths, environmental "
        "destruction, demolished infrastructure).\n\n"
        "Rules:\n"
        "- Do not inflate scores based on emotional language in articles.\n"
        "- Do not score based on how 'interesting' or 'clickable' the "
        "story is.\n"
        "- When in doubt, score lower and flag insufficient data.\n\n"
        "After scoring the topic on its surface-level signals, consider:\n\n"
        "DOWNSTREAM CONSEQUENCES: What could this story lead to if it develops further?\n"
        "Rate the potential downstream impact from 1-10, independent of how significant "
        "the headline appears right now.\n\n"
        "Respond ONLY with valid JSON, no markdown, no preamble:\n"
        "{\n"
        '  "significance_score": <sum of 5 factors, 0-100>,\n'
        '  "factors": {\n'
        '    "population_affected": {"score": <int>, "rationale": "<one sentence>"},\n'
        '    "economic_magnitude": {"score": <int>, "rationale": "<one sentence>"},\n'
        '    "policy_change": {"score": <int>, "rationale": "<one sentence>"},\n'
        '    "duration": {"score": <int>, "rationale": "<one sentence>"},\n'
        '    "irreversibility": {"score": <int>, "rationale": "<one sentence>"}\n'
        "  },\n"
        '  "insufficient_data": ["<factor names where score is 0 due to missing info>"],\n'
        '  "confidence": "low" | "medium" | "high",\n'
        '  "downstream_potential": <1-10>,\n'
        '  "downstream_rationale": "<what could this lead to, in one sentence>"\n'
        "}"
    )


def _call_haiku(prompt: str) -> dict | None:
    """Call Claude Haiku and parse structured JSON response.

    Retries once on failure. Returns parsed dict or None on error.
    """
    client = Anthropic(api_key=settings.anthropic_api_key)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            msg = prompt if attempt == 0 else prompt + "\n\nReturn valid JSON only, no other text."
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": msg}],
            )

            # If output was truncated, the JSON is incomplete — skip retry
            if response.stop_reason == "max_tokens":
                logger.warning(
                    "Haiku response truncated (hit %d token limit), skipping.",
                    _MAX_TOKENS,
                )
                return None

            raw = response.content[0].text.strip()

            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            # Use raw_decode to ignore trailing text after valid JSON
            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(raw)

            # Validate and clamp significance_score
            score = parsed.get("significance_score", 0)
            if not isinstance(score, (int, float)):
                score = 0
            parsed["significance_score"] = max(0, min(100, int(score)))

            # Backward compat alias
            parsed["impact_score"] = parsed["significance_score"]

            # Validate factor sub-scores and clamp to their max ranges
            factor_maxes = {
                "population_affected": 30,
                "economic_magnitude": 25,
                "policy_change": 20,
                "duration": 15,
                "irreversibility": 10,
            }
            factors = parsed.get("factors", {})
            if isinstance(factors, dict):
                for key, max_val in factor_maxes.items():
                    factor = factors.get(key, {})
                    if isinstance(factor, dict):
                        raw = factor.get("score", 0)
                        if not isinstance(raw, (int, float)):
                            raw = 0
                        factor["score"] = max(0, min(max_val, int(raw)))
                parsed["factors"] = factors

            # Normalize confidence
            if parsed.get("confidence") not in ("low", "medium", "high"):
                parsed["confidence"] = "low"

            # Ensure insufficient_data is a list
            if not isinstance(parsed.get("insufficient_data"), list):
                parsed["insufficient_data"] = []

            return parsed

        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt == 0:
                logger.warning(
                    "JSON parse error (attempt 1), retrying: %s — raw: %.200s",
                    exc, raw if "raw" in dir() else "N/A",
                )
                time.sleep(1)
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Claude API error (attempt 1), retrying: %s", exc)
                time.sleep(1)

    logger.error("Claude Haiku call failed after 2 attempts: %s", last_error)
    return None


# ─── public API ──────────────────────────────────────────────────────────────────


def score_impacts(
    story_ids: list[int] | None = None,
    force: bool = False,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Score impact for active stories using Claude Haiku.

    If story_ids is None, score stories that need it:
    - Never been scored (impact_score = 0 or NULL)
    - Article count grew >20% since last score
    - Last scored >6 hours ago AND has new articles

    If force=True, score all active stories regardless.

    Returns: {
        "scored": int,
        "skipped": int,
        "errors": int,
        "scores": list[dict]  # [{story_id, score, factors, confidence, insufficient_data}]
        "outlier_articles": list[dict]  # always empty (kept for pipeline compat)
    }
    """
    result: dict = {
        "scored": 0,
        "skipped": 0,
        "errors": 0,
        "scores": [],
        "outlier_articles": [],  # kept for pipeline compat (always empty now)
    }

    # ── 1. Resolve which stories to process ──────────────────────────────
    all_stories = db.get_active_stories()

    if story_ids is not None:
        id_set = set(story_ids)
        stories = [s for s in all_stories if s.get("id") in id_set]
    elif force:
        stories = all_stories
    else:
        stories = [s for s in all_stories if _needs_scoring(s)]
        result["skipped"] = len(all_stories) - len(stories)

    if not stories:
        logger.info("No stories need impact scoring.")
        return result

    logger.info("Scoring impact for %d stories.", len(stories))

    # ── 2. Score each story ──────────────────────────────────────────────
    for story in stories:
        story_id = story["id"]

        if _is_stale_story(story):
            db.update_story_metadata(story_id, impact_score=0)
            result["skipped"] += 1
            logger.debug("Story %d is stale, zeroed impact and skipped.", story_id)
            continue

        try:
            articles = (
                story_articles[story_id]
                if story_articles is not None and story_id in story_articles
                else db.get_articles_for_story(story_id)
            )
            if not articles:
                logger.warning("Story %d has no articles, skipping.", story_id)
                result["skipped"] += 1
                continue

            prompt = _build_prompt(story, articles)
            parsed = _call_haiku(prompt)

            if parsed is None:
                logger.warning("Story %d: Haiku returned no usable result.", story_id)
                result["errors"] += 1
                continue

            score = parsed["significance_score"]
            factors = parsed.get("factors", {})
            confidence = parsed.get("confidence", "low")
            insufficient = parsed.get("insufficient_data", [])
            category = parsed.get("category", "")

            # Entity boost: max(entity.importance) * 0.15, capped at 15
            entity_boost = 0.0
            entities = get_entities_for_topic(story_id)
            if entities:
                max_importance = max(
                    (e.get("importance", 0) for e in entities), default=0
                )
                entity_boost = min(max_importance * ENTITY_BOOST_FACTOR, ENTITY_BOOST_CAP)

            boosted_score = min(100, score + entity_boost)

            # Extract population rationale from factors for backward compat
            pop_rationale = ""
            pop_factor = factors.get("population_affected", {})
            if isinstance(pop_factor, dict):
                pop_rationale = pop_factor.get("rationale", "")

            if entity_boost > 0:
                logger.debug(
                    "Story %d: entity boost +%.1f (base %d → %d)",
                    story_id, entity_boost, score, int(boosted_score),
                )

            # Persist score to DB (impact_score = significance_score for compat)
            db.update_story_scores(story_id, impact=float(boosted_score), attention=story.get("attention_score") or 0.0)

            # Persist significance breakdown + metadata
            meta_update: dict = {
                "significance_score": int(boosted_score),
                "significance_factors": json.dumps(factors),
                "confidence": confidence,
                "caveats": insufficient,
                "impact_scored_at": datetime.now(UTC).isoformat(),
                "scored_at_article_count": story.get("article_count") or len(articles),
                "population_affected": pop_rationale,
            }
            if category:
                meta_update["category"] = category
            db.update_story_metadata(story_id, **meta_update)

            result["scored"] += 1
            result["scores"].append({
                "story_id": story_id,
                "score": int(boosted_score),
                "base_score": score,
                "entity_boost": round(entity_boost, 1),
                "factors": factors,
                "confidence": confidence,
                "insufficient_data": insufficient,
                "downstream_potential": parsed.get("downstream_potential"),
                "downstream_rationale": parsed.get("downstream_rationale"),
            })

            logger.debug(
                "Story %d: significance=%d, confidence=%s",
                story_id, score, confidence,
            )

        except Exception as exc:
            logger.error("Failed to score story %d: %s", story_id, exc)
            result["errors"] += 1

    logger.info(
        "Impact scoring complete. Scored %d, skipped %d, errors %d.",
        result["scored"],
        result["skipped"],
        result["errors"],
    )
    return result


# ─── standalone test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")

    result = score_impacts(force=True)
    print(f"\nScored: {result['scored']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Errors: {result['errors']}")

    for s in result["scores"][:5]:
        factors = s.get("factors", {})
        pop = factors.get("population_affected", {}).get("score", "?")
        econ = factors.get("economic_magnitude", {}).get("score", "?")
        pol = factors.get("policy_change", {}).get("score", "?")
        print(
            f"  Story #{s['story_id']}: {s['score']}/100 "
            f"(pop={pop} econ={econ} pol={pol}) "
            f"confidence={s.get('confidence', '?')}"
        )
