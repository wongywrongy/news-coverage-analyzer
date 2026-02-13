"""
Re-generate all existing analyses using the updated prompt.
Runs in priority order, with rate limiting and progress tracking.

Usage:
    cd backend
    python -m scripts.reanalyze_all                       # dry run (preview only)
    python -m scripts.reanalyze_all --execute             # actually re-run
    python -m scripts.reanalyze_all --execute --limit 10  # re-run first 10 only
    python -m scripts.reanalyze_all --execute --resume    # resume from last completed
    python -m scripts.reanalyze_all --execute --delay 1.5 # custom delay between calls
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# Ensure backend/ is on the path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from analysis.generator import generate_analyses
from config.settings import settings
from db.client import get_client

logger = logging.getLogger(__name__)

COST_PER_STORY = 0.10  # ~$0.05-0.15 per Sonnet analysis


def get_stories_to_reanalyze(limit: int | None = None, resume: bool = False) -> list[dict]:
    """Get all stories with existing analyses, ordered by priority.

    Priority: impact_score desc, then article_count desc.
    If resume=True, skip stories already at the current analysis version.
    """
    supabase = get_client()
    current_version = settings.current_analysis_version

    # Fetch stories that have analyses
    result = (
        supabase.table("stories")
        .select(
            "id, topic, impact_score, article_count, active, "
            "analyses(analysis_version, updated_at)"
        )
        .eq("active", True)
        .gte("article_count", 3)
        .order("impact_score", desc=True)
        .execute()
    )

    stories = []
    for row in result.data or []:
        analyses = row.pop("analyses", None)

        # Only include stories that have an existing analysis
        if isinstance(analyses, list) and analyses:
            analysis = analyses[0]
        elif isinstance(analyses, dict) and analyses:
            analysis = analyses
        else:
            continue

        row["analysis_version"] = analysis.get("analysis_version") or 1
        row["analysis_updated_at"] = analysis.get("updated_at")

        # If resuming, skip stories already at the current version
        if resume and row["analysis_version"] >= current_version:
            continue

        stories.append(row)

    # Secondary sort by article_count desc (impact_score is primary from query)
    stories.sort(key=lambda s: (-(s.get("impact_score") or 0), -(s.get("article_count") or 0)))

    if limit:
        stories = stories[:limit]

    return stories


def reanalyze_story(story: dict) -> bool:
    """Re-run the full analysis pipeline for a single story."""
    try:
        result = generate_analyses(
            story_ids=[story["id"]],
            max_per_cycle=1,
            force=True,
        )
        return result["generated"] > 0
    except Exception as e:
        logger.error("Failed to re-analyze story %d (%s): %s", story["id"], story.get("topic"), e)
        return False


def main() -> None:
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
    )

    parser = argparse.ArgumentParser(description="Re-run all analyses with updated prompt")
    parser.add_argument("--execute", action="store_true", help="Actually run (default is dry run)")
    parser.add_argument("--limit", type=int, default=None, help="Max stories to process")
    parser.add_argument("--resume", action="store_true", help="Skip stories already at current version")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between API calls")
    args = parser.parse_args()

    stories = get_stories_to_reanalyze(limit=args.limit, resume=args.resume)

    total_estimated = len(stories) * COST_PER_STORY
    estimated_time = len(stories) * args.delay / 60

    print(f"\n{'=' * 60}")
    print(f"ClearSignal — Re-analysis {'(DRY RUN)' if not args.execute else '(LIVE)'}")
    print(f"{'=' * 60}")
    print(f"Target version:        {settings.current_analysis_version}")
    print(f"Stories to re-analyze: {len(stories)}")
    print(f"Estimated cost:        ~${total_estimated:.2f}")
    print(f"Estimated time:        ~{estimated_time:.0f} minutes")
    print(f"Delay between calls:   {args.delay}s")
    print(f"{'=' * 60}\n")

    if not stories:
        print("No stories need re-analysis.")
        return

    if not args.execute:
        print("DRY RUN — showing stories that would be re-analyzed:\n")
        for i, story in enumerate(stories, 1):
            version = story.get("analysis_version", 1)
            print(
                f"  {i:3d}. [{story.get('impact_score', 0):3.0f}] "
                f"{story.get('topic', '?')[:55]} "
                f"({story.get('article_count', 0)} articles, v{version})"
            )
        print("\nRe-run with --execute to actually process these stories.")
        return

    # Confirm
    confirm = input(f"This will re-analyze {len(stories)} stories (~${total_estimated:.2f}). Continue? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    # Process
    success = 0
    failed = 0

    for i, story in enumerate(stories, 1):
        topic = story.get("topic", f"story-{story['id']}")[:55]
        print(f"[{i}/{len(stories)}] Re-analyzing: {topic}...", end=" ", flush=True)

        if reanalyze_story(story):
            success += 1
            print("done")
        else:
            failed += 1
            print("FAILED")

        # Rate limit
        if i < len(stories):
            time.sleep(args.delay)

    print(f"\n{'=' * 60}")
    print(f"Complete: {success} succeeded, {failed} failed out of {len(stories)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
