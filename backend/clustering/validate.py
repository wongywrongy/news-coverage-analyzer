"""Topic validation — filter out historical, evergreen, and non-current-events topics.

Runs after clustering + labeling, before scoring.  Two-pass approach:

1. Fast keyword pre-filter (free, no API call) — catches obvious historical topics
2. GPT-4o-mini validation — classifies ambiguous topics as current or not

Invalid stories are deactivated (active=False) so they're automatically
excluded from all downstream stages.  The validation_reason is stored
for debugging.

No heavy dependencies — uses OpenAI (same as selection stage).

Usage:
    python -m clustering.validate
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta

from config.settings import settings
from config.sources import SOURCE_BIAS, get_source_region
from db.queries import (
    deactivate_story,
    get_active_stories,
    get_articles_for_story,
    get_entities_for_topic,
    get_top_connected_entities,
    update_story_metadata,
)

logger = logging.getLogger(__name__)


# ── Fast keyword pre-filter ─────────────────────────────────────────────────

HISTORICAL_PATTERNS = [
    r"assassination of (?!attempt)",
    r"(?:civil|world) war (?:i{1,3}|1|2)\b",
    r"\bfounding fathers\b",
    r"(?:18|19)\d{2}s?\b.*(?:era|century|period)",
    r"\bhistorical (?:impact|significance|legacy)\b",
    r"\bhistory of\b",
]

EVERGREEN_PATTERNS = [
    r"^how (?:the |to )",
    r"^what (?:is|are) ",
    r"^why (?:the |do )",
    r"\btips for\b",
    r"\bbest (?:ways|practices)\b",
]

_compiled_historical = [re.compile(p, re.IGNORECASE) for p in HISTORICAL_PATTERNS]
_compiled_evergreen = [re.compile(p, re.IGNORECASE) for p in EVERGREEN_PATTERNS]


# ── US relevance — keyword triggers & source analysis ────────────────────────

US_KEYWORD_TRIGGERS = [
    r"\b(?:congress|senate|house of representatives|capitol hill)\b",
    r"\b(?:white house|oval office|executive order)\b",
    r"\b(?:supreme court|scotus|federal court|circuit court)\b",
    r"\b(?:pentagon|state department|doj|fbi|cia|nsa|dhs|fema|epa|fda|sec|ftc|fcc)\b",
    r"\b(?:federal reserve|fed rate|treasury department|wall street)\b",
    r"\b(?:democrat(?:ic)?|republican|gop)\b",
    r"\b(?:us military|american troops|nato.*us)\b",
    r"\b(?:immigration|border patrol|ice (?:agents?|raids?))\b",
    r"\b(?:medicaid|medicare|social security|obamacare|aca)\b",
    r"\b(?:second amendment|first amendment|roe v|citizens united)\b",
    r"\b(?:silicon valley|big tech)\b",
    r"\bamerican\b",
    r"\bu\.?s\.?\b",
]

_compiled_us_keywords = [re.compile(p, re.IGNORECASE) for p in US_KEYWORD_TRIGGERS]


def _has_us_keyword(topic: str, headlines: list[str]) -> bool:
    """Check if topic or headlines contain US-relevant keywords."""
    text = topic + " " + " ".join(headlines)
    return any(p.search(text) for p in _compiled_us_keywords)


def _compute_international_ratio(articles: list[dict]) -> float:
    """Compute what fraction of a topic's articles come from international sources.

    Returns a float 0.0-1.0 where 1.0 means all articles are from international sources.
    """
    if not articles:
        return 0.0
    intl_count = 0
    for a in articles:
        domain = a.get("source_domain") or a.get("source_name", "")
        region = get_source_region(domain)
        if region == "international":
            intl_count += 1
    return intl_count / len(articles)


def _has_us_primary_source(articles: list[dict]) -> bool:
    """Check if at least one article comes from a US primary source.

    A 'primary' source is a major US outlet (e.g. NYT, WaPo, CNN, Fox) as
    tagged in SOURCE_BIAS. If any US primary source is covering the topic,
    it's likely US-relevant regardless of international ratio.
    """
    for a in articles:
        domain = a.get("source_domain") or a.get("source_name", "")
        meta = SOURCE_BIAS.get(domain, {})
        if meta.get("region") == "us" and meta.get("primary"):
            return True
    return False


def quick_reject(topic: str, articles: list[dict]) -> tuple[bool, str | None]:
    """Fast heuristic check.  Returns (should_reject, reason).

    Only rejects with high confidence — when in doubt, returns False
    so the topic passes to GPT-4o-mini.
    """
    topic_lower = topic.lower()

    # If all articles are recent (<14 days), topic is likely current
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=14)
    dates = []
    for a in articles:
        raw = a.get("published_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            dates.append(dt)
        except (ValueError, TypeError):
            continue

    if dates and all(d > cutoff for d in dates):
        # All articles are recent — only reject on very strong pattern match
        pass
    elif dates and all(d < cutoff for d in dates):
        # All articles are old — more aggressive filtering
        return True, "All articles older than 14 days"

    for pattern in _compiled_historical:
        if pattern.search(topic_lower):
            return True, f"Historical pattern: {pattern.pattern}"

    for pattern in _compiled_evergreen:
        if pattern.search(topic_lower):
            return True, f"Evergreen pattern: {pattern.pattern}"

    return False, None


# ── GPT-4o-mini validation ──────────────────────────────────────────────────

VALIDATION_PROMPT = """\
You assess whether a news topic should be included in a current events analysis platform.
Today's date is {today}. Treat this as the present day when evaluating dates.

You are evaluating three dimensions:

1. CURRENCY — Is this about something happening now (within the last 30 days)?
   - Active events, ongoing investigations, current legislation, live legal proceedings = current
   - Historical retrospectives, anniversaries, educational content = not current
   - EXCEPTION: Historical events that have NEW developments (newly released documents, \
reopened investigations) ARE current

2. SUBSTANCE — Is this substantive enough for serious analysis?
   - Policy, law, governance, economics, international relations, public health, \
major court cases, institutional decisions = substantive
   - Celebrity gossip, entertainment, sports, lifestyle, human interest = not substantive
   - GRAY AREA: Tech company decisions (product launches, leadership changes) can be \
substantive if they affect policy, markets, or public welfare

3. CONNECTEDNESS — Does this topic connect to important ongoing storylines?
   - Even if a topic sounds routine or procedural, it may be important because of \
WHO is involved or WHAT it connects to
   - Entity connections are provided below. High-importance entities signal that this \
topic sits within a major storyline
   - A confirmation hearing, committee vote, or regulatory filing can be the most \
important story of the week if it involves the right people or advances the right narrative

Scoring:
- CURRENCY: 0-10 (0 = purely historical, 10 = breaking right now)
- SUBSTANCE: 0-10 (0 = trivial, 10 = major institutional/policy significance)
- CONNECTEDNESS: 0-10 (0 = isolated, no entity connections; 10 = central node in \
multiple major ongoing storylines)

Include the topic if ANY of these conditions are met:
- Currency >= 6 AND Substance >= 5
- Connectedness >= 7 (regardless of other scores)
- Currency >= 8 (breaking news always included even if substance is borderline)
- Substance >= 8 (major institutional events always included even if slightly older)

Respond with valid JSON only. No markdown, no backticks:
{{"currency": <0-10>, "substance": <0-10>, "connectedness": <0-10>, \
"include": true/false, "reason": "<one sentence>", "confidence": "high" | "medium" | "low"}}"""


US_RELEVANCE_PROMPT = """\
You assess whether an international news topic has relevance to a US audience.

Topic: {topic}
Sample headlines:
{headlines}

Does this topic have a meaningful connection to the United States or US interests?

Consider:
- Direct US involvement (policy, military, diplomacy, trade)
- Impact on US economy, markets, or supply chains
- Implications for US foreign policy or alliances
- Effects on American citizens or residents
- Precedent-setting for US domestic issues
- Significant global events that any informed US reader should know about

Respond with valid JSON only:
{{"us_relevant": true/false, "connection_type": "direct" | "indirect" | "informational" | "none", \
"connection_note": "<one sentence explaining the US connection or why none exists>"}}"""


def _check_us_relevance(topic: str, articles: list[dict]) -> dict:
    """Call GPT-4o-mini to assess US relevance of a majority-international topic.

    Returns: {"us_relevant": bool, "connection_type": str, "connection_note": str}
    """
    from openai import OpenAI

    headlines = [a.get("title", "") for a in articles[:8]]

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.1,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": US_RELEVANCE_PROMPT.format(
                topic=topic,
                headlines="\n".join(f"- {h}" for h in headlines),
            ),
        }],
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def _build_entity_context(story_id: int) -> str:
    """Build entity context string for the validation prompt."""
    entities = get_entities_for_topic(story_id)
    if not entities:
        return "No known entity connections."

    lines = []
    for ent in entities:
        eid = ent.get("id")
        name = ent.get("canonical_name", "unknown")
        etype = ent.get("entity_type", "")
        importance = ent.get("importance", 0)
        topic_count = ent.get("topic_count", 0)

        # Get top connected entities
        connected = get_top_connected_entities(eid) if eid else []
        connected_names = [c["name"] for c in connected]
        connected_str = ", ".join(connected_names) if connected_names else "none"

        lines.append(
            f"- {name} ({etype}, importance: {importance:.0f}/100)\n"
            f"  Connected to: {connected_str}\n"
            f"  Seen in {topic_count} topics on this platform"
        )

    return "\n".join(lines)


def _call_openai_validation(topic: str, articles: list[dict], story_id: int | None = None) -> dict:
    """Call GPT-4o-mini for topic validation.  Returns parsed JSON."""
    from openai import OpenAI

    sample_headlines = [a.get("title", "") for a in articles[:5]]

    dates = []
    for a in articles:
        raw = a.get("published_at")
        if raw:
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                dates.append(dt.strftime("%Y-%m-%d"))
            except (ValueError, TypeError):
                pass

    earliest = min(dates) if dates else "unknown"
    latest = max(dates) if dates else "unknown"

    # Build entity context
    entity_context = _build_entity_context(story_id) if story_id else "No known entity connections."

    user_msg = (
        f"Topic: {topic}\n"
        f"Article count: {len(articles)}\n"
        f"Publication dates: {earliest} to {latest}\n"
        f"Sample headlines:\n"
        + "\n".join(f"- {h}" for h in sample_headlines)
        + f"\n\nEntity connections (from knowledge graph):\n{entity_context}\n\n"
        + "Should this topic be included?"
    )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.1,
        max_tokens=250,
        messages=[
            {"role": "system", "content": VALIDATION_PROMPT.format(
                today=datetime.now(UTC).strftime("%Y-%m-%d"),
            )},
            {"role": "user", "content": user_msg},
        ],
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


# ── Public interface ────────────────────────────────────────────────────────


def validate_topics(story_ids: list[int] | None = None) -> dict:
    """Validate active stories, deactivating non-current topics.

    If story_ids is None, validates all active stories that haven't
    been validated yet (validated != True).

    Returns: {"validated": N, "rejected": M, "accepted": K, "errors": E}
    """
    all_stories = get_active_stories()
    if not all_stories:
        logger.info("No active stories to validate")
        return {"validated": 0, "rejected": 0, "accepted": 0, "errors": 0}

    if story_ids is not None:
        target_ids = set(story_ids)
        targets = [s for s in all_stories if s["id"] in target_ids]
    else:
        # Only validate stories not yet validated
        targets = [s for s in all_stories if not s.get("validated")]

    if not targets:
        logger.info("All active stories already validated")
        return {"validated": 0, "rejected": 0, "accepted": 0, "errors": 0}

    stats = {"validated": 0, "rejected": 0, "accepted": 0, "errors": 0}

    for story in targets:
        sid = story["id"]
        topic = story.get("topic", f"story-{sid}")
        articles = get_articles_for_story(sid)

        if not articles:
            update_story_metadata(sid, validated=True, validation_reason="No articles")
            stats["validated"] += 1
            stats["accepted"] += 1
            continue

        # Step 1: Fast keyword check
        should_reject, reason = quick_reject(topic, articles)
        if should_reject:
            deactivate_story(sid)
            update_story_metadata(
                sid,
                validated=True,
                validation_reason=f"keyword: {reason}",
                validation_confidence="high",
            )
            stats["validated"] += 1
            stats["rejected"] += 1
            logger.info("REJECTED (keyword) story #%d: %s — %s", sid, topic, reason)
            continue

        # Step 2: US relevance check for majority-international topics
        intl_ratio = _compute_international_ratio(articles)
        us_connection_type = ""
        us_connection_note = ""

        if intl_ratio > 0.70:
            headlines = [a.get("title", "") for a in articles[:8]]

            # Safety net: US primary source override
            if _has_us_primary_source(articles):
                logger.info(
                    "US primary source found for story #%d: %s — skipping intl filter",
                    sid, topic,
                )
                us_connection_type = "direct"
                us_connection_note = "US primary source covering this topic"

            # Safety net: US keyword trigger
            elif _has_us_keyword(topic, headlines):
                logger.info(
                    "US keyword trigger for story #%d: %s — skipping intl filter",
                    sid, topic,
                )
                us_connection_type = "direct"
                us_connection_note = "US keyword detected in topic/headlines"

            else:
                # Call GPT-4o-mini for US relevance assessment
                try:
                    us_result = _check_us_relevance(topic, articles)
                    us_relevant = us_result.get("us_relevant", True)
                    us_connection_type = us_result.get("connection_type", "")
                    us_connection_note = us_result.get("connection_note", "")

                    if not us_relevant:
                        deactivate_story(sid)
                        reason = f"Not US-relevant: {us_connection_note}"
                        update_story_metadata(
                            sid,
                            validated=True,
                            validation_reason=reason,
                            validation_confidence="medium",
                            us_connection_type="none",
                            us_connection_note=us_connection_note,
                        )
                        stats["validated"] += 1
                        stats["rejected"] += 1
                        logger.info("REJECTED (US relevance) story #%d: %s — %s", sid, topic, reason)
                        continue

                except Exception as exc:
                    # On failure, assume relevant — never block pipeline
                    logger.warning("US relevance check failed for story #%d: %s", sid, exc)

        # Persist US connection metadata if we have it
        if us_connection_type:
            update_story_metadata(
                sid,
                us_connection_type=us_connection_type,
                us_connection_note=us_connection_note,
            )

        # Step 3: Check entity protection before GPT validation
        entity_protected = False
        protection_reason = ""
        entities = get_entities_for_topic(sid)
        for ent in entities:
            imp = ent.get("importance", 0)
            if imp > 60:
                entity_protected = True
                protection_reason = (
                    f"Protected: connected to [{ent.get('canonical_name', '?')}] "
                    f"(importance {imp:.0f})"
                )
                break

        # Step 4: GPT-4o-mini validation
        try:
            result = _call_openai_validation(topic, articles, story_id=sid)

            # Handle new multi-factor format
            if "include" in result:
                is_valid = result.get("include", True)
                reason = result.get("reason", "")
                confidence = result.get("confidence", "medium")
                connectedness = result.get("connectedness", 0)
            else:
                # Backward compat with old format
                is_valid = result.get("valid", True)
                reason = result.get("reason", "")
                confidence = result.get("confidence", "medium")

            # Don't reject on low confidence
            if not is_valid and confidence == "low":
                is_valid = True
                reason = f"Low-confidence rejection overridden: {reason}"

            # Entity protection override
            if not is_valid and entity_protected:
                is_valid = True
                reason = f"{protection_reason}. Original rejection: {reason}"
                logger.info(
                    "PROTECTED story #%d: %s — %s", sid, topic, protection_reason
                )

            if not is_valid:
                deactivate_story(sid)
                logger.info("REJECTED (GPT) story #%d: %s — %s", sid, topic, reason)
                stats["rejected"] += 1
            else:
                stats["accepted"] += 1

            update_story_metadata(
                sid,
                validated=True,
                validation_reason=reason,
                validation_confidence=confidence,
            )
            stats["validated"] += 1

        except Exception as exc:
            # On failure, assume valid — never block pipeline
            logger.warning("Validation failed for story #%d (%s): %s", sid, topic, exc)
            update_story_metadata(
                sid,
                validated=True,
                validation_reason=f"Validation error: {exc}",
                validation_confidence="unknown",
            )
            stats["validated"] += 1
            stats["accepted"] += 1
            stats["errors"] += 1

    logger.info(
        "Validation complete: %d validated, %d rejected, %d accepted, %d errors",
        stats["validated"], stats["rejected"], stats["accepted"], stats["errors"],
    )
    return stats


# ── Standalone test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = validate_topics()
    print(f"\nValidated: {result['validated']}")
    print(f"Rejected:  {result['rejected']}")
    print(f"Accepted:  {result['accepted']}")
    print(f"Errors:    {result['errors']}")
