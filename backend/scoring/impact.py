"""Score real-world impact of news stories using Claude Haiku.

Each story gets a 0-100 impact score based on population affected,
policy significance, lasting consequences, geographic scope, and urgency.
As a free piggyback, cluster coherence is validated in the same API call —
headlines that don't belong are flagged as outliers for the orchestrator
to handle.

Cost: ~$0.002 per story (Haiku input + 300 output tokens).
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

from anthropic import Anthropic

from config.settings import settings
from config.sources import SOURCE_BIAS
from db import queries as db

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024
_MAX_HEADLINES = 50
_RESCORE_HOURS = 6.0
_GROWTH_THRESHOLD = 0.20  # 20% article count growth triggers rescore

_SYSTEM_PROMPT = (
    "You are a news analyst for ClearSignal. You have two jobs:\n"
    "1. Rate the real-world IMPACT of a news story\n"
    "2. Check if all headlines actually belong to the same story\n\n"
    "Be objective. Impact means lasting consequences for real people, "
    "NOT how much media coverage it gets.\n\n"
    "For cluster validation, be VERY conservative. Only flag articles "
    "that are clearly about a completely different event. Different angles "
    "on the same story are NOT outliers."
)

_BIAS_BUCKETS: dict[str, list[str]] = {
    "LEFT / FAR-LEFT": ["far-left", "left"],
    "LEFT-CENTER": ["left-center"],
    "CENTER": ["center"],
    "RIGHT-CENTER": ["right-center"],
    "RIGHT / FAR-RIGHT": ["right", "far-right"],
}


# ─── helpers ────────────────────────────────────────────────────────────────────


def _get_bias_label(source_domain: str) -> str:
    """Look up the bias label for a source domain (e.g. 'cnn.com')."""
    meta = SOURCE_BIAS.get(source_domain)
    if meta:
        return meta["label"]
    return "center"


def _bucket_for_label(label: str) -> str:
    """Map a bias label to a display bucket name."""
    for bucket, labels in _BIAS_BUCKETS.items():
        if label in labels:
            return bucket
    return "CENTER"


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
            last_scored = last_scored.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - last_scored).total_seconds() / 3600
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
        first_seen = first_seen.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - first_seen).days
    if age_days > 7 and story.get("status") == "stale":
        return True
    return False


def _build_prompt(story: dict, articles: list[dict]) -> str:
    """Build the Claude Haiku prompt for impact scoring + validation.

    Groups article headlines by source bias bucket. If >50 articles,
    sends only the 50 most recent (newest are most likely misassigned).
    """
    topic = story.get("topic") or "(unknown topic)"
    article_count = story.get("article_count") or len(articles)
    source_count = story.get("source_count") or 0

    # Cap at 50 most recent headlines (already sorted newest-first from DB)
    display_articles = articles[:_MAX_HEADLINES]

    # Group by bias bucket
    buckets: dict[str, list[str]] = {b: [] for b in _BIAS_BUCKETS}
    for a in display_articles:
        source = a.get("source_name") or "unknown"
        title = a.get("title") or "(no title)"
        article_id = a.get("id", "?")
        label = _get_bias_label(a.get("source_domain", ""))
        bucket = _bucket_for_label(label)
        buckets[bucket].append(f"- [{source}] {title}  (id:{article_id})")

    # Format grouped headlines
    sections: list[str] = []
    for bucket_name, lines in buckets.items():
        if lines:
            sections.append(f"{bucket_name}:\n" + "\n".join(lines))

    headlines_block = "\n\n".join(sections) if sections else "(no headlines)"

    truncation_note = ""
    if len(articles) > _MAX_HEADLINES:
        truncation_note = (
            f"\n(Showing {_MAX_HEADLINES} of {len(articles)} headlines — "
            "most recent shown)\n"
        )

    return (
        f"STORY: {topic}\n"
        f"ARTICLES ({article_count} from {source_count} sources):\n"
        f"{truncation_note}\n"
        f"{headlines_block}\n\n"
        "TASK 1 - IMPACT SCORE:\n"
        "Rate 0-100 using this rubric:\n"
        "- Population affected (0-25): How many people are directly impacted?\n"
        "  1-5: niche/local, 6-15: one state/industry, 16-25: national/global\n"
        "- Policy significance (0-25): Does this change laws, regulations, precedent?\n"
        "  1-5: no policy angle, 6-15: policy debate, 16-25: enacted/blocked policy\n"
        "- Lasting consequences (0-25): Will this matter in 6 months?\n"
        "  1-5: forgotten in days, 6-15: weeks-long relevance, 16-25: lasting change\n"
        "- Geographic scope (0-15): Local, state, national, or international?\n"
        "  1-5: local, 6-10: state/regional, 11-15: national/international\n"
        "- Urgency (0-10): Is this time-sensitive? Active crisis?\n"
        "  1-3: background story, 4-7: developing, 8-10: active crisis\n\n"
        "TASK 2 - CLUSTER VALIDATION:\n"
        "Review the headlines. Flag ONLY articles that are about a COMPLETELY\n"
        "DIFFERENT news event or topic. Do NOT flag articles that cover\n"
        "different angles, reactions, opinions, or consequences of the same\n"
        "underlying story — those BELONG together.\n\n"
        "Example of what to flag:\n"
        "- Story about Senate immigration bill, but one headline is about\n"
        "  a NBA basketball game → flag it\n"
        "- Story about a wildfire, but one headline is about cryptocurrency → flag it\n\n"
        "Example of what NOT to flag:\n"
        "- Story about deportation policy: headline about court blocking deportation,\n"
        "  headline about protests against deportation, headline about deportation\n"
        "  flights to Colombia — these are ALL the same story, do NOT flag\n"
        "- Different sources framing the same event differently → do NOT flag\n\n"
        "If in doubt, do NOT flag. We prefer keeping a borderline article over\n"
        "incorrectly removing it. Most stories should have 0 outliers.\n"
        "Only flag when it's obviously a completely unrelated topic.\n"
        "Return an empty outliers array if everything looks correct.\n\n"
        "Respond in JSON only, no other text.\n"
        "Keep reasoning to 1-2 SHORT sentences. Keep outlier reasons under 10 words.\n\n"
        "{\n"
        '  "impact_score": 82,\n'
        '  "population": "All US immigrants with pending cases (~11M)",\n'
        '  "reasoning": "Federal court order directly affects...",\n'
        '  "category": "politics",\n'
        '  "outliers": [\n'
        '    {"article_id": 4521, "reason": "About Nintendo Switch"},\n'
        '    {"article_id": 4587, "reason": "Unrelated trade policy"}\n'
        "  ]\n"
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
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
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

            # Validate and clamp impact_score
            score = parsed.get("impact_score", 0)
            if not isinstance(score, (int, float)):
                score = 0
            parsed["impact_score"] = max(0, min(100, int(score)))

            # Ensure outliers is a list
            if not isinstance(parsed.get("outliers"), list):
                parsed["outliers"] = []

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
        "outliers_flagged": int,
        "scores": list[dict]  # [{story_id, score, population, reasoning}]
        "outlier_articles": list[dict]  # [{article_id, story_id, reason}]
    }
    """
    result: dict = {
        "scored": 0,
        "skipped": 0,
        "errors": 0,
        "outliers_flagged": 0,
        "scores": [],
        "outlier_articles": [],
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

            score = parsed["impact_score"]
            population = parsed.get("population", "")
            reasoning = parsed.get("reasoning", "")
            category = parsed.get("category", "")
            outliers = parsed.get("outliers", [])

            # Persist score to DB
            db.update_story_scores(story_id, impact=float(score), attention=story.get("attention_score") or 0.0)

            # Persist metadata (category, population, scoring timestamp)
            meta_update: dict = {
                "impact_scored_at": datetime.now(timezone.utc).isoformat(),
                "scored_at_article_count": story.get("article_count") or len(articles),
                "population_affected": population,
            }
            if category:
                meta_update["category"] = category
            db.update_story_metadata(story_id, **meta_update)

            result["scored"] += 1
            result["scores"].append({
                "story_id": story_id,
                "score": score,
                "population": population,
                "reasoning": reasoning,
            })

            # Collect outlier articles
            article_ids_in_story = {a["id"] for a in articles}
            for outlier in outliers:
                aid = outlier.get("article_id")
                reason = outlier.get("reason", "")
                if aid is None:
                    continue
                if aid not in article_ids_in_story:
                    logger.warning(
                        "Story %d: outlier article_id %s not in story, ignoring.",
                        story_id, aid,
                    )
                    continue
                result["outlier_articles"].append({
                    "article_id": aid,
                    "story_id": story_id,
                    "reason": reason,
                })
                result["outliers_flagged"] += 1

            logger.debug(
                "Story %d: score=%d, population='%s', outliers=%d",
                story_id, score, population, len(outliers),
            )

        except Exception as exc:
            logger.error("Failed to score story %d: %s", story_id, exc)
            result["errors"] += 1

    logger.info(
        "Impact scoring complete. Scored %d, skipped %d, errors %d, outliers %d.",
        result["scored"],
        result["skipped"],
        result["errors"],
        result["outliers_flagged"],
    )
    return result


# ─── standalone test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")

    result = score_impacts(force=True)
    print(f"\nScored: {result['scored']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Errors: {result['errors']}")
    print(f"Outliers flagged: {result['outliers_flagged']}")

    for s in result["scores"][:5]:
        print(f"  Story #{s['story_id']}: {s['score']}/100 — {s['population']}")

    for o in result["outlier_articles"]:
        print(f"  Outlier article #{o['article_id']} in story #{o['story_id']}: {o['reason']}")
