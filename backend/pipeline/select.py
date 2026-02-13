"""Editorial selection — GPT-4o-mini decides which stories get Claude analysis.

Sits between score and scrape in the pipeline. Saves cost by only sending
high-priority stories through expensive Claude analysis + scraping.

Falls back to existing staleness-based trigger logic if OpenAI fails.

Usage:
    python -m pipeline.select
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from config.settings import settings
from db.queries import (
    clear_selection_flags,
    get_entities_for_topic,
    get_selection_candidates,
    get_top_connected_entities,
    mark_stories_selected,
)

logger = logging.getLogger(__name__)

SELECTION_PROMPT = """\
You are an editorial director for a nonpartisan, US-focused news analysis platform.

Your job: decide which stories deserve expensive AI analysis this cycle.
You have a budget of {max_stories} analysis slots.

AUDIENCE: Your readers are primarily US-based. Prioritize stories that matter
most to an informed American audience.

For each story, choose ONE action:
- "analyze_new": Story has no analysis yet and is worth analyzing
- "re_analyze": Story already has analysis but significant developments warrant a refresh
- "skip": Not worth analyzing (or analysis is still fresh)

PRIORITIZE stories where:
1. Impact score is high AND multiple sources are covering it (major stories readers expect to see)
2. Article velocity is increasing (stories gaining momentum right now)
3. High framing divergence is likely (politically charged topics, policy debates, investigations)
4. Multiple ideologically diverse sources are covering it (more contrast potential)
5. Undercovered high-impact stories are still valuable but should not dominate — feature 1-2 per cycle max
6. Missing analysis entirely (analyze_new over re_analyze when close)
7. US domestic stories should generally rank above international stories at similar impact levels
8. International stories ARE worth analyzing when they directly affect US interests, policy, economy,
   or security — but purely foreign stories with no US nexus should be deprioritized

SKIP stories that are:
- Low significance (< 30 score)
- Stale with no new articles
- Already have fresh analysis with few new articles since
- Purely international with no meaningful US connection (unless impact > 80)

Each story may include entity_connections showing which people, organizations,
and cases it connects to, along with their importance scores. Use this to:
- Prioritize stories that sit at intersections of multiple important storylines
- Recognize that "routine" events involving high-importance entities often
  deserve analysis because they advance ongoing narratives
- Avoid dismissing procedural/legal stories when the entities involved have
  high importance scores — these are often where major stories develop

Here are the candidate stories:

{candidates_json}

Respond with a JSON object:
{{
  "decisions": [
    {{
      "story_id": <int>,
      "action": "analyze_new" | "re_analyze" | "skip",
      "priority": <int 1-10, 10=highest>,
      "reason": "<brief reason>"
    }}
  ]
}}

Include ALL stories in your response. Return valid JSON only.
"""


def _build_candidate_list(candidates: list[dict]) -> list[dict]:
    """Build a compact candidate list for the prompt."""
    now = datetime.now(UTC)
    items = []
    for c in candidates:
        # Hours since last article
        last_article_at = c.get("last_article_at")
        hours_since_last_article = None
        if last_article_at:
            try:
                dt = datetime.fromisoformat(str(last_article_at).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                hours_since_last_article = round((now - dt).total_seconds() / 3600, 1)
            except (ValueError, TypeError):
                pass

        has_analysis = c.get("has_analysis", False)

        # Hours since analysis
        hours_since_analysis = None
        if has_analysis and c.get("analysis_generated_at"):
            try:
                dt = datetime.fromisoformat(
                    str(c["analysis_generated_at"]).replace("Z", "+00:00")
                )
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                hours_since_analysis = round((now - dt).total_seconds() / 3600, 1)
            except (ValueError, TypeError):
                pass

        # Articles since analysis
        article_count = c.get("article_count") or 0
        article_count_at_gen = c.get("article_count_at_gen") or 0
        articles_since_analysis = article_count - article_count_at_gen if has_analysis else None

        # Coverage gap
        impact = c.get("impact_score") or 0
        coverage = c.get("coverage_score") or 0
        coverage_gap = round(impact - coverage, 1)

        # Entity connections
        entity_connections = []
        cluster_importance = 0
        try:
            entities = get_entities_for_topic(c["id"])
            for ent in entities:
                eid = ent.get("id")
                imp = ent.get("importance", 0)
                connected = get_top_connected_entities(eid) if eid else []
                entity_connections.append({
                    "name": ent.get("canonical_name", ""),
                    "importance": round(imp, 1),
                    "linked_to": [conn["name"] for conn in connected],
                })
                cluster_importance = max(cluster_importance, imp)
        except Exception as exc:
            logger.debug("Entity graph lookup failed for story %d: %s", c["id"], exc)

        item = {
            "story_id": c["id"],
            "topic": c.get("topic", ""),
            "category": c.get("category", ""),
            "impact_score": impact,
            "significance_score": c.get("significance_score") or 0,
            "coverage_score": coverage,
            "coverage_gap": coverage_gap,
            "article_count": article_count,
            "source_count": c.get("source_count") or 0,
            "status": c.get("status", ""),
            "hours_since_last_article": hours_since_last_article,
            "has_analysis": has_analysis,
            "hours_since_analysis": hours_since_analysis,
            "articles_since_analysis": articles_since_analysis,
        }
        if entity_connections:
            item["entity_connections"] = entity_connections
            item["cluster_importance"] = round(cluster_importance, 1)
        items.append(item)
    return items


def _call_openai(prompt: str, num_candidates: int) -> dict:
    """Call GPT-4o-mini for editorial selection. Returns parsed JSON."""
    from openai import OpenAI

    # ~40 tokens per story decision; cap at model limit
    max_tokens = min(max(2000, num_candidates * 60 + 200), 16384)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def run_editorial_selection() -> dict:
    """Run the editorial selection stage.

    Returns: {"selected": N, "skipped": M, "re_analyze": K} or
             {"selected": 0, "skipped": 0, "error": str} on failure.
    """
    if not settings.selection_enabled:
        logger.info("Editorial selection disabled, skipping")
        return {"selected": 0, "skipped": 0, "re_analyze": 0, "disabled": True}

    # Step 1: Clear previous cycle's flags
    clear_selection_flags()

    # Step 2: Get candidates
    candidates = get_selection_candidates()
    if not candidates:
        logger.info("No active stories to select from")
        return {"selected": 0, "skipped": 0, "re_analyze": 0}

    # Step 3: Build compact candidate list, pre-filtered to top ~50
    candidate_list = _build_candidate_list(candidates)

    # Pre-filter: only send plausible candidates to GPT-4o-mini.
    # Sort by impact descending; drop stories with < 3 articles or
    # significance < 20 (unless they have no analysis yet).
    MAX_CANDIDATES = 100
    candidate_list = [
        c for c in candidate_list
        if c["article_count"] >= 3
        and (c["significance_score"] >= 20 or not c["has_analysis"])
    ]
    candidate_list.sort(key=lambda c: c["impact_score"], reverse=True)
    skipped_pre = max(0, len(candidate_list) - MAX_CANDIDATES)
    candidate_list = candidate_list[:MAX_CANDIDATES]

    if not candidate_list:
        logger.info("No candidates pass pre-filter")
        return {"selected": 0, "skipped": 0, "re_analyze": 0}

    logger.info(
        "Sending %d candidates to GPT-4o-mini (%d pre-filtered out)",
        len(candidate_list), skipped_pre,
    )

    # Step 4: Call GPT-4o-mini
    prompt = SELECTION_PROMPT.format(
        max_stories=settings.max_stories_per_analysis_cycle,
        candidates_json=json.dumps(candidate_list, indent=2),
    )

    try:
        result = _call_openai(prompt, num_candidates=len(candidate_list))
    except Exception as exc:
        logger.warning("OpenAI selection call failed: %s — falling back to staleness logic", exc)
        return {"selected": 0, "skipped": 0, "re_analyze": 0, "error": str(exc)}

    # Step 5: Process decisions
    decisions = result.get("decisions", [])
    selections = []
    stats = {"selected": 0, "skipped": 0, "re_analyze": 0}

    for d in decisions:
        action = d.get("action", "skip")
        story_id = d.get("story_id")
        if not story_id:
            continue
        if action in ("analyze_new", "re_analyze"):
            selections.append({
                "story_id": story_id,
                "reason": f"{action}: {d.get('reason', '')}",
                "priority": d.get("priority", 5),
            })
            if action == "re_analyze":
                stats["re_analyze"] += 1
            stats["selected"] += 1
        else:
            stats["skipped"] += 1

    # Step 6: Mark selected stories in DB
    if selections:
        mark_stories_selected(selections)

    logger.info(
        "Editorial selection: %d selected (%d re_analyze), %d skipped",
        stats["selected"], stats["re_analyze"], stats["skipped"],
    )
    return stats


if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(name)s | %(message)s")

    from rich import print as rprint

    rprint("[bold]Editorial Selection (standalone)[/bold]\n")
    result = run_editorial_selection()
    rprint(f"  Selected:    {result.get('selected', 0)}")
    rprint(f"  Re-analyze:  {result.get('re_analyze', 0)}")
    rprint(f"  Skipped:     {result.get('skipped', 0)}")
    if result.get("error"):
        rprint(f"  [red]Error:[/red] {result['error']}")
