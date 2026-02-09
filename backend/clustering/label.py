"""Generate concise, neutral topic labels for stories using Claude Haiku.

Replaces placeholder labels (raw headlines) with clean wire-service-style
topic slugs AND assigns one of four fixed categories.

Cheap enough to run every cycle (~$0.001 per 20 stories).
"""

import json
import logging
import time

from anthropic import Anthropic

from config.settings import settings
from db import queries as db

logger = logging.getLogger(__name__)

# ── The four canonical categories (fixed — never add new ones) ───────────────

VALID_CATEGORIES = [
    "Politics & Law",
    "World & Security",
    "Economy & Business",
    "Science & Health",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Politics & Law": [
        "congress", "senate", "legislation", "court", "election",
        "impeach", "judiciary", "amendment", "governor", "vote",
        "democrat", "republican", "partisan", "attorney general",
        "confirmation", "nomination", "political", "supreme court",
        "house", "speaker", "caucus", "bipartisan", "veto", "law",
        "prosecutor", "indictment", "ruling", "justice", "pardon",
        "ballot", "redistricting", "filibuster", "bill", "lobbyist",
    ],
    "World & Security": [
        "nato", "military", "diplomacy", "sanctions", "conflict",
        "border", "intelligence", "terrorism", "defense", "troops",
        "missile", "nuclear", "alliance", "ceasefire", "invasion",
        "peacekeeping", "embassy", "refugee", "treaty", "warfare",
        "geopolitical", "sovereignty", "coup", "occupation", "arms",
        "drone", "airstrikes", "insurgent", "hostage", "espionage",
        "ukraine", "russia", "china", "iran", "north korea",
    ],
    "Economy & Business": [
        "fed", "inflation", "gdp", "earnings", "trade", "market",
        "unemployment", "tariff", "rate", "stock", "revenue",
        "merger", "acquisition", "recession", "fiscal", "debt",
        "economy", "layoffs", "ipo", "crypto", "bitcoin", "bank",
        "interest rate", "consumer", "retail", "supply chain",
        "oil", "energy", "tech", "startup", "venture", "profit",
        "manufacturing", "jobs", "wage", "housing", "real estate",
    ],
    "Science & Health": [
        "vaccine", "climate", "research", "fda", "cdc", "outbreak",
        "study", "emissions", "species", "medical", "pharmaceutical",
        "disease", "trial", "genetic", "environmental", "pandemic",
        "virus", "hospital", "cancer", "mental health", "drug",
        "therapy", "diagnosis", "obesity", "opioid", "wildfire",
        "hurricane", "earthquake", "nasa", "space", "ai", "genome",
    ],
}

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

Also classify this topic into exactly one category:
- Politics & Law
- World & Security
- Economy & Business
- Science & Health

Headlines:
{headlines}

Respond ONLY with valid JSON:
{{"topic": "<3-8 word neutral topic label>", "category": "<one of the four categories>"}}"""

# ── Prompt for category-only classification (existing labeled stories) ───────

_CLASSIFY_PROMPT = """\
Classify this news topic into exactly one category:
- Politics & Law
- World & Security
- Economy & Business
- Science & Health

Topic: {topic}
Sample headlines:
{headlines}

Respond with ONLY the category name, nothing else."""


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


def _validate_category(category: str) -> str | None:
    """Return the category if valid, or None."""
    if category in VALID_CATEGORIES:
        return category
    # Fuzzy match — handle casing/whitespace variations
    cat_lower = category.strip().lower()
    for valid in VALID_CATEGORIES:
        if valid.lower() == cat_lower:
            return valid
    return None


def classify_by_keywords(text: str) -> str:
    """Classify text into a category using keyword matching.

    Scans the text for keywords from each category and returns the
    category with the most hits.  Falls back to "Economy & Business"
    if no keywords match (largest catch-all group).
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] == 0:
        return "Economy & Business"
    return best


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


def _needs_categorization(story: dict) -> bool:
    """Check if a story has a good topic but no/invalid category."""
    if _needs_labeling(story):
        return False  # needs full relabeling, not just categorization
    category = (story.get("category") or "").strip()
    return _validate_category(category) is None


def _generate_label(headlines: list[str]) -> tuple[str, str]:
    """Call Claude Haiku to generate a topic label AND category.

    Returns (topic, category).  Retries once on API error.
    If the first label fails quality validation, one retry with
    stricter instructions is attempted.  Category is validated
    and falls back to keyword matching if invalid.
    """
    prompt = _LABEL_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines))
    client = Anthropic(api_key=settings.anthropic_api_key)

    headline_text = " ".join(headlines)
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Parse JSON response
            topic, category = _parse_label_response(raw, headline_text)

            if not _validate_label(topic):
                logger.warning("Label '%s' failed quality check, retrying.", topic)
                retry_prompt = (
                    f"The label '{topic}' is too vague or looks like a keyword list. "
                    "Generate a specific 4-8 word topic label that describes "
                    "the actual news event, not just keywords.\n\n"
                    "Also classify into exactly one category:\n"
                    "- Politics & Law\n- World & Security\n"
                    "- Economy & Business\n- Science & Health\n\n"
                    "Headlines:\n" + "\n".join(f"- {h}" for h in headlines[:10])
                    + '\n\nRespond ONLY with valid JSON:\n'
                    '{"topic": "<better label>", "category": "<category>"}'
                )
                retry_response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    messages=[{"role": "user", "content": retry_prompt}],
                )
                raw2 = retry_response.content[0].text.strip()
                topic, category = _parse_label_response(raw2, headline_text)

            return topic, category

        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Claude API error (attempt 1), retrying: %s", exc)
                time.sleep(1)

    raise last_error  # type: ignore[misc]


def _parse_label_response(raw: str, fallback_text: str) -> tuple[str, str]:
    """Parse a JSON response from the labeling prompt.

    Handles both clean JSON and responses with extra text around it.
    Returns (topic, category) where category is always valid.
    """
    topic = ""
    category = ""

    # Try JSON parse
    try:
        data = json.loads(raw)
        topic = data.get("topic", "").strip().strip("\"'")
        category = data.get("category", "").strip()
    except (json.JSONDecodeError, AttributeError):
        # Maybe JSON is embedded in surrounding text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end])
                topic = data.get("topic", "").strip().strip("\"'")
                category = data.get("category", "").strip()
            except (json.JSONDecodeError, AttributeError):
                pass

    # If JSON parse failed entirely, treat raw text as topic (backward compat)
    if not topic:
        topic = raw.strip().strip("\"'")

    # Validate category — fall back to keyword matching
    valid_cat = _validate_category(category)
    if valid_cat is None:
        valid_cat = classify_by_keywords(topic + " " + fallback_text)
        logger.debug("AI category '%s' invalid, keyword fallback → '%s'", category, valid_cat)

    return topic, valid_cat


def _classify_story_ai(topic: str, headlines: list[str]) -> str:
    """Call Claude Haiku to classify an existing topic into a category.

    Cheaper than full labeling — only asks for the category.
    Falls back to keyword classification on error.
    """
    prompt = _CLASSIFY_PROMPT.format(
        topic=topic,
        headlines="\n".join(f"- {h}" for h in headlines[:10]),
    )
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        valid = _validate_category(raw)
        if valid:
            return valid
    except Exception as exc:
        logger.warning("AI classification failed for '%s': %s", topic, exc)

    return classify_by_keywords(topic + " " + " ".join(headlines))


# ─── public API ─────────────────────────────────────────────────────────────────


def label_stories(story_ids: list[int] | None = None) -> dict:
    """Generate topic labels AND categories for stories.

    If story_ids is None, processes:
    1. Stories whose topic looks like a placeholder → full relabel + categorize
    2. Stories with good topic but no category → categorize only

    Returns: {
        "labeled": int,
        "categorized": int,
        "skipped": int,
        "errors": int,
        "labels": list[dict]   # [{story_id, old_topic, new_topic, category}]
    }
    """
    result: dict = {
        "labeled": 0, "categorized": 0,
        "skipped": 0, "errors": 0, "labels": [],
    }

    # ── 1. Resolve which stories to process ──────────────────────────────────
    all_stories = db.get_active_stories()

    if story_ids is not None:
        id_set = set(story_ids)
        needs_label = [s for s in all_stories if s.get("id") in id_set]
        needs_category_only = []
    else:
        needs_label = [s for s in all_stories if _needs_labeling(s)]
        needs_category_only = [s for s in all_stories if _needs_categorization(s)]
        result["skipped"] = len(all_stories) - len(needs_label) - len(needs_category_only)

    # ── 2. Full label + categorize ───────────────────────────────────────────
    for story in needs_label:
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

            new_topic, category = _generate_label(headlines)
            db.update_story_metadata(story_id, topic=new_topic, category=category)

            result["labeled"] += 1
            result["labels"].append({
                "story_id": story_id,
                "old_topic": old_topic,
                "new_topic": new_topic,
                "category": category,
            })
            logger.debug(
                "Story %d: '%s' → '%s' [%s]",
                story_id, old_topic, new_topic, category,
            )

        except Exception as exc:
            logger.error("Failed to label story %d: %s", story_id, exc)
            result["errors"] += 1

    # ── 3. Category-only pass (good topic, missing category) ─────────────────
    for story in needs_category_only:
        story_id = story["id"]
        topic = story.get("topic", "")

        try:
            articles = db.get_articles_for_story(story_id)
            headlines = [
                (a.get("title") or "").strip()
                for a in (articles or [])
                if (a.get("title") or "").strip()
            ][:10]

            category = _classify_story_ai(topic, headlines)
            db.update_story_metadata(story_id, category=category)

            result["categorized"] += 1
            result["labels"].append({
                "story_id": story_id,
                "old_topic": topic,
                "new_topic": topic,
                "category": category,
            })
            logger.debug("Story %d: categorized as '%s'", story_id, category)

        except Exception as exc:
            logger.error("Failed to categorize story %d: %s", story_id, exc)
            result["errors"] += 1

    logger.info(
        "Labeled %d stories, categorized %d more. Skipped %d. %d errors.",
        result["labeled"],
        result["categorized"],
        result["skipped"],
        result["errors"],
    )
    return result


def categorize_stories_by_keywords(story_ids: list[int] | None = None) -> dict:
    """Classify stories using keyword matching only (no AI, free).

    For backfilling categories on existing stories without API cost.
    Only affects stories with an empty or invalid category.

    Returns: {"categorized": int, "skipped": int}
    """
    all_stories = db.get_active_stories()

    if story_ids is not None:
        id_set = set(story_ids)
        targets = [s for s in all_stories if s["id"] in id_set]
    else:
        targets = [
            s for s in all_stories
            if _validate_category((s.get("category") or "").strip()) is None
        ]

    categorized = 0
    for story in targets:
        topic = story.get("topic") or ""
        if not topic.strip():
            continue

        category = classify_by_keywords(topic)
        db.update_story_metadata(story["id"], category=category)
        categorized += 1
        logger.debug("Story %d: keyword → '%s'", story["id"], category)

    logger.info("Keyword-categorized %d / %d stories", categorized, len(targets))
    return {"categorized": categorized, "skipped": len(targets) - categorized}


# ─── standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")
    result = label_stories()
    print(f"\nLabeled: {result['labeled']}  Categorized: {result['categorized']}  "
          f"Skipped: {result['skipped']}  Errors: {result['errors']}")
    for item in result["labels"]:
        print(f"  #{item['story_id']}: '{item['old_topic']}' → '{item['new_topic']}' [{item['category']}]")
