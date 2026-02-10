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

import json
import logging
import re
from datetime import datetime, timezone, timedelta

from config.settings import settings
from db.queries import (
    get_active_stories,
    get_articles_for_story,
    deactivate_story,
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


def quick_reject(topic: str, articles: list[dict]) -> tuple[bool, str | None]:
    """Fast heuristic check.  Returns (should_reject, reason).

    Only rejects with high confidence — when in doubt, returns False
    so the topic passes to GPT-4o-mini.
    """
    topic_lower = topic.lower()

    # If all articles are recent (<14 days), topic is likely current
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)
    dates = []
    for a in articles:
        raw = a.get("published_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
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
You validate whether a topic represents a CURRENT news event.
Today's date is {today}. Treat this as the present day when evaluating dates.
Respond with JSON only. No markdown, no backticks.

Reject if:
- Historical event (assassinations, wars, treaties from decades/centuries ago)
- Articles are opinion pieces using historical events as analogies
- Evergreen educational content ("How the Electoral College Works")
- Pure entertainment recaps, sports recaps, or lifestyle content with no news value
- Obituaries or retrospectives about past events

Accept if:
- Something happening or developing within the last 30 days
- Even if it references history, it's about a CURRENT development
- Active policy debates, ongoing investigations, current legislation
- Breaking news, developing situations, scheduled upcoming events
- Article publication dates are near today's date ({today})"""


def _call_openai_validation(topic: str, articles: list[dict]) -> dict:
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

    user_msg = (
        f"Topic: {topic}\n"
        f"Article count: {len(articles)}\n"
        f"Publication dates: {earliest} to {latest}\n"
        f"Sample headlines:\n"
        + "\n".join(f"- {h}" for h in sample_headlines)
        + "\n\nIs this a current news event?\n"
        'Respond with: {"valid": true/false, "reason": "one sentence", '
        '"confidence": "high/medium/low"}'
    )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.1,
        max_tokens=150,
        messages=[
            {"role": "system", "content": VALIDATION_PROMPT.format(
                today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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

        # Step 2: GPT-4o-mini validation
        try:
            result = _call_openai_validation(topic, articles)
            is_valid = result.get("valid", True)
            reason = result.get("reason", "")
            confidence = result.get("confidence", "medium")

            # Don't reject on low confidence
            if not is_valid and confidence == "low":
                is_valid = True
                reason = f"Low-confidence rejection overridden: {reason}"

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
