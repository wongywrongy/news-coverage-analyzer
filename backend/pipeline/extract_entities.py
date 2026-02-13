"""Entity extraction — extract named entities from topics using GPT-4o-mini.

Runs after label, before validate. Batches up to 20 topics per API call
for cost efficiency (~$0.001-0.003 per batch).

Extracts: PERSON, ORGANIZATION, LEGAL_CASE, LEGISLATION, EVENT, LOCATION

Usage:
    python -m pipeline.extract_entities
"""

from __future__ import annotations

import json
import logging
from itertools import islice

from config.settings import settings
from db.queries import (
    find_entity_by_alias,
    get_active_stories,
    get_articles_for_story,
    get_extracted_topic_ids,
    link_topic_entity,
    upsert_entity,
)

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20

_SYSTEM_PROMPT = """\
You extract named entities from news topics and their headlines.

For each topic, return the entities present with their type and a canonical name.

Entity types: PERSON, ORGANIZATION, LEGAL_CASE, LEGISLATION, EVENT, LOCATION

Canonicalization rules:
- Use the most common full name: "Donald Trump" not "Trump" or "President Trump"
- Use official organization names: "Department of Justice" not "DOJ" (but include "DOJ" as an alias)
- For legal cases, use the common reference: "Epstein case" not "United States v. Epstein"
- Merge duplicates: "Pam Bondi" and "Pamela Bondi" are the same entity
- Only extract entities that are SUBSTANTIVELY relevant to the topic, not passing mentions
- A person mentioned only as providing a quote about an unrelated topic is not substantively relevant

Respond with valid JSON only:
{
  "topics": [
    {
      "topic_id": <id>,
      "entities": [
        {
          "name": "Canonical Name",
          "type": "PERSON",
          "aliases": ["Alternate Name", "Short Name"],
          "relevance": "primary" | "secondary"
        }
      ]
    }
  ]
}

"primary" = the topic is directly about this entity
"secondary" = the entity is involved but the topic isn't primarily about them"""


def _build_user_prompt(topics: list[dict], story_articles: dict[int, list[dict]] | None = None) -> str:
    """Build the user prompt for a batch of topics."""
    lines = ["Extract entities from these topics:\n"]
    for topic in topics:
        sid = topic["id"]
        label = topic.get("topic", f"story-{sid}")
        lines.append(f"Topic ID: {sid}")
        lines.append(f"Label: {label}")

        # Get sample headlines
        if story_articles and sid in story_articles:
            articles = story_articles[sid]
        else:
            articles = get_articles_for_story(sid)

        headlines = [a.get("title", "") for a in articles[:5] if a.get("title")]
        if headlines:
            lines.append("Headlines (sample):")
            for h in headlines:
                lines.append(f"- {h}")

        lines.append("")  # blank line between topics

    return "\n".join(lines)


def _call_openai_extraction(prompt: str) -> dict:
    """Call GPT-4o-mini for entity extraction. Returns parsed JSON."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.1,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def _resolve_entity(name: str, entity_type: str, aliases: list[str]) -> int | None:
    """Resolve an entity: find existing by name/alias or create new.

    Returns entity ID.
    """
    # 1. Try upsert by canonical name (handles exact match + creates new)
    entity_id = upsert_entity(name, entity_type, aliases)
    if entity_id:
        return entity_id

    # 2. Try alias match
    for alias in aliases:
        entity_id = find_entity_by_alias(alias, entity_type)
        if entity_id:
            # Update with new alias (the canonical name)
            upsert_entity_aliases = [name] + aliases
            upsert_entity(name, entity_type, upsert_entity_aliases)
            return entity_id

    return None


def _batched(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            break
        yield batch


def extract_entities(
    story_ids: list[int] | None = None,
    force: bool = False,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Extract entities from active stories.

    If story_ids is None, processes stories that haven't been extracted yet.
    If force=True, re-extracts all active stories.

    Returns: {"extracted": N, "entities_found": M, "errors": E}
    """
    stats = {"extracted": 0, "entities_found": 0, "errors": 0, "skipped": 0}

    all_stories = get_active_stories()
    if not all_stories:
        logger.info("No active stories for entity extraction")
        return stats

    if story_ids is not None:
        id_set = set(story_ids)
        targets = [s for s in all_stories if s["id"] in id_set]
    elif force:
        targets = all_stories
    else:
        already_extracted = get_extracted_topic_ids()
        targets = [s for s in all_stories if s["id"] not in already_extracted]
        stats["skipped"] = len(all_stories) - len(targets)

    if not targets:
        logger.info("All active stories already have entity extractions")
        return stats

    logger.info("Extracting entities for %d stories", len(targets))

    # Process in batches of _BATCH_SIZE
    for batch in _batched(targets, _BATCH_SIZE):
        try:
            prompt = _build_user_prompt(batch, story_articles)
            result = _call_openai_extraction(prompt)

            topics_data = result.get("topics", [])
            topic_map = {t["topic_id"]: t for t in topics_data if "topic_id" in t}

            for story in batch:
                sid = story["id"]
                topic_result = topic_map.get(sid)
                if not topic_result:
                    logger.debug("No entities returned for story #%d", sid)
                    stats["extracted"] += 1
                    continue

                entities = topic_result.get("entities", [])
                for ent in entities:
                    name = ent.get("name", "").strip()
                    etype = ent.get("type", "").upper()
                    aliases = ent.get("aliases", [])
                    relevance = ent.get("relevance", "secondary")

                    if not name or not etype:
                        continue

                    entity_id = _resolve_entity(name, etype, aliases)
                    if entity_id:
                        link_topic_entity(sid, entity_id, relevance)
                        stats["entities_found"] += 1

                stats["extracted"] += 1

        except Exception as exc:
            logger.error("Entity extraction batch failed: %s", exc)
            stats["errors"] += 1

    logger.info(
        "Entity extraction complete: %d extracted, %d entities found, %d errors",
        stats["extracted"], stats["entities_found"], stats["errors"],
    )
    return stats


if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = extract_entities()
    print(f"\nExtracted: {result['extracted']}")
    print(f"Entities found: {result['entities_found']}")
    print(f"Errors: {result['errors']}")
