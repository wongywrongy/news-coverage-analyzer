"""Generate concise, neutral topic labels for stories using Claude Haiku.

Replaces placeholder labels (raw headlines) with clean wire-service-style
topic slugs.  Cheap enough to run every cycle (~$0.001 per 20 stories).
"""

import logging
import time

from anthropic import Anthropic

from config.settings import settings
from db import queries as db

logger = logging.getLogger(__name__)

_LABEL_PROMPT = """\
You are a wire-service editor writing a topic slug.
Given these headlines about the same story, generate a concise \
3-8 word neutral topic label. No punctuation. No articles (a, an, the).
Just the factual topic.

Examples of good labels:
- Senate Passes Immigration Reform Bill
- SC Measles Outbreak Reaches 900 Cases
- Federal Reserve Holds Interest Rates
- Ukraine Russia Ceasefire Negotiations

Headlines:
{headlines}

Topic label:"""


# ─── helpers ────────────────────────────────────────────────────────────────────


def _validate_label(label: str) -> bool:
    """Check if a generated label meets quality standards."""
    if len(label.split()) < 2:
        return False
    if label.count(",") > 1:
        return False
    if len(label) < 5:
        return False
    return True


def _needs_labeling(story: dict) -> bool:
    """Check if a story's topic looks like a raw headline placeholder.

    Signs of a placeholder:
    - topic is None or empty
    - Contains " - " or " | " (headline source suffixes)
    - Longer than 80 characters
    - Contains quotation marks (usually from a headline)
    - Contains "..." (truncated headline)
    - Starts with lowercase (topic labels should be title-cased)
    """
    topic = (story.get("topic") or "").strip()
    if not topic:
        return True
    if " - " in topic or " | " in topic:
        return True
    if len(topic) > 80:
        return True
    if '"' in topic or "\u2018" in topic or "\u2019" in topic:
        return True
    if "..." in topic:
        return True
    if topic[0].islower():
        return True
    if not _validate_label(topic):
        return True
    return False


def _generate_label(headlines: list[str]) -> str:
    """Call Claude Haiku to generate a concise topic label.

    Returns the label string, stripped of quotes and whitespace.
    Retries once on API error, then raises.  If the first label
    fails quality validation, one retry with stricter instructions
    is attempted.
    """
    prompt = _LABEL_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines))
    client = Anthropic(api_key=settings.anthropic_api_key)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            label = response.content[0].text.strip().strip("\"'")

            if not _validate_label(label):
                logger.warning("Label '%s' failed quality check, retrying with stricter prompt.", label)
                retry_prompt = (
                    f"The label '{label}' is too vague or looks like a keyword list. "
                    "Generate a specific 4-8 word topic label that describes "
                    "the actual news event, not just keywords.\n\n"
                    "Headlines:\n" + "\n".join(f"- {h}" for h in headlines[:10])
                    + "\n\nBetter topic label:"
                )
                retry_response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=50,
                    messages=[{"role": "user", "content": retry_prompt}],
                )
                label = retry_response.content[0].text.strip().strip("\"'")

            return label
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Claude API error (attempt 1), retrying: %s", exc)
                time.sleep(1)

    raise last_error  # type: ignore[misc]


# ─── public API ─────────────────────────────────────────────────────────────────


def label_stories(story_ids: list[int] | None = None) -> dict:
    """Generate topic labels for stories.

    If story_ids is None, label all active stories whose topic
    looks like a placeholder (contains " - " suffix pattern or
    is longer than 80 chars -- signs of a raw headline being used).

    Returns: {
        "labeled": int,
        "skipped": int,
        "errors": int,
        "labels": list[dict]   # [{story_id, old_topic, new_topic}]
    }
    """
    result: dict = {"labeled": 0, "skipped": 0, "errors": 0, "labels": []}

    # ── 1. Resolve which stories to process ──────────────────────────────────
    if story_ids is not None:
        all_stories = db.get_active_stories()
        id_set = set(story_ids)
        stories = [s for s in all_stories if s.get("id") in id_set]
    else:
        all_stories = db.get_active_stories()
        stories = [s for s in all_stories if _needs_labeling(s)]
        result["skipped"] = len(all_stories) - len(stories)

    if not stories:
        logger.info("No stories need labeling.")
        return result

    # ── 2. Label each story ──────────────────────────────────────────────────
    for story in stories:
        story_id = story["id"]
        old_topic = story.get("topic") or ""

        try:
            articles = db.get_articles_for_story(story_id)
            if not articles:
                logger.warning("Story %d has no articles, skipping.", story_id)
                result["skipped"] += 1
                continue

            # Deduplicate and cap headlines
            seen: set[str] = set()
            headlines: list[str] = []
            for a in articles:
                title = (a.get("title") or "").strip()
                if title and title not in seen:
                    seen.add(title)
                    headlines.append(title)
                if len(headlines) >= 15:
                    break

            if not headlines:
                logger.warning("Story %d: no usable headlines, skipping.", story_id)
                result["skipped"] += 1
                continue

            new_topic = _generate_label(headlines)
            db.update_story_metadata(story_id, topic=new_topic)

            result["labeled"] += 1
            result["labels"].append({
                "story_id": story_id,
                "old_topic": old_topic,
                "new_topic": new_topic,
            })
            logger.debug("Story %d: '%s' → '%s'", story_id, old_topic, new_topic)

        except Exception as exc:
            logger.error("Failed to label story %d: %s", story_id, exc)
            result["errors"] += 1

    logger.info(
        "Labeled %d stories. Skipped %d (already labeled). %d errors.",
        result["labeled"],
        result["skipped"],
        result["errors"],
    )
    return result


# ─── standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")
    result = label_stories()
    print(f"\nLabeled: {result['labeled']}  Skipped: {result['skipped']}  "
          f"Errors: {result['errors']}")
    for item in result["labels"]:
        print(f"  #{item['story_id']}: '{item['old_topic']}' → '{item['new_topic']}'")
