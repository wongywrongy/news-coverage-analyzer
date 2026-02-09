"""Rename vague story headlines into specific, neutral ones using Claude Haiku.

Checks if a story topic is vague (contains generic words or is too long),
then uses the article headlines in the cluster to generate a better one.

Cost: ~$0.001 per story (Haiku input + output tokens).
"""

import json
import logging
import re

from anthropic import Anthropic

from config.settings import settings
from db import queries as db

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 256

_VAGUE_WORDS = {"various", "multiple", "several", "different", "numerous", "many", "some"}

_SYSTEM_PROMPT = (
    "You rewrite vague or generic news story titles into specific, neutral "
    "headlines. You follow strict rules for neutrality."
)


def _is_vague(topic: str) -> bool:
    """Check if a story topic is vague and needs renaming."""
    if not topic:
        return True
    words = topic.lower().split()
    if len(words) > 15:
        return True
    if any(w in _VAGUE_WORDS for w in words):
        return True
    # Placeholder-style topics from the labeling step
    if topic.startswith("cluster-") or topic.startswith("story-"):
        return True
    return False


def _build_prompt(topic: str, articles: list[dict]) -> str:
    """Build the rename prompt with article headlines for context."""
    headlines = []
    for a in articles[:20]:
        source = a.get("source_name") or "unknown"
        title = a.get("title") or "(no title)"
        headlines.append(f"- {title} ({source})")

    return (
        f"Rewrite this story title to be specific and neutral.\n\n"
        f"Current title: {topic}\n\n"
        f"Article headlines from this cluster:\n"
        + "\n".join(headlines)
        + "\n\n"
        "Rules:\n"
        "- Maximum 12 words.\n"
        "- Use factual, descriptive language only.\n"
        "- No emotional adjectives (devastating, controversial, unprecedented, "
        "alarming, historic, shocking).\n"
        "- No loaded framing: prefer 'X would change Y by Z' over 'X threatens Y' "
        "or 'X saves Y.'\n"
        "- Identify the most specific shared subject across articles.\n"
        "- If articles describe different angles of one event, lead with the "
        "event, not the angle.\n\n"
        'Respond ONLY with valid JSON:\n'
        '{\n'
        '  "headline": "<max 12 words, specific, neutral>",\n'
        '  "rationale": "<one sentence: what made the original vague and how this fixes it>"\n'
        '}'
    )


def rename_vague_headlines(
    story_ids: list[int] | None = None,
    force: bool = False,
) -> dict:
    """Rename vague story headlines using Claude Haiku.

    If story_ids is None, check all active stories.
    If force=True, rename even non-vague topics.

    Returns: {"renamed": int, "skipped": int, "errors": int, "renames": list}
    """
    result: dict = {"renamed": 0, "skipped": 0, "errors": 0, "renames": []}

    all_stories = db.get_active_stories()
    if story_ids is not None:
        id_set = set(story_ids)
        stories = [s for s in all_stories if s.get("id") in id_set]
    else:
        stories = all_stories

    candidates = []
    for s in stories:
        topic = s.get("topic", "")
        if force or _is_vague(topic):
            candidates.append(s)
        else:
            result["skipped"] += 1

    if not candidates:
        logger.info("No vague headlines to rename.")
        return result

    logger.info("Renaming %d vague headlines.", len(candidates))
    client = Anthropic(api_key=settings.anthropic_api_key)

    for story in candidates:
        story_id = story["id"]
        topic = story.get("topic", "")

        try:
            articles = db.get_articles_for_story(story_id)
            if not articles:
                result["skipped"] += 1
                continue

            prompt = _build_prompt(topic, articles)
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            new_headline = parsed.get("headline", "").strip()

            if not new_headline or len(new_headline.split()) > 14:
                logger.warning(
                    "Story %d: Haiku returned invalid headline: %s",
                    story_id, new_headline,
                )
                result["errors"] += 1
                continue

            db.update_story_metadata(story_id, topic=new_headline)
            result["renamed"] += 1
            result["renames"].append({
                "story_id": story_id,
                "old": topic,
                "new": new_headline,
                "rationale": parsed.get("rationale", ""),
            })
            logger.info(
                "Story %d: renamed '%s' → '%s'",
                story_id, topic, new_headline,
            )

        except Exception as exc:
            logger.error("Failed to rename story %d: %s", story_id, exc)
            result["errors"] += 1

    logger.info(
        "Headline rename complete: renamed=%d, skipped=%d, errors=%d",
        result["renamed"], result["skipped"], result["errors"],
    )
    return result
