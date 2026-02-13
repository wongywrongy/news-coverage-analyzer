"""
One-time script to generate analyses for all scored stories
that don't have one yet. Run manually when budget allows.

Usage:
    cd backend
    python -m scripts.backfill_analyses              # all eligible
    python -m scripts.backfill_analyses --limit 20   # just 20
    python -m scripts.backfill_analyses --min-impact 60  # impact >= 60 only
    python -m scripts.backfill_analyses --force --limit 23  # regenerate existing
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure backend/ is on the path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from analysis.generator import generate_analyses
from db.client import get_client


def backfill(limit: int | None = None, min_impact: int = 0, force: bool = False) -> None:
    supabase = get_client()

    # Get all active stories above the impact threshold with enough articles
    query = (
        supabase.table("stories")
        .select("id, topic, impact_score, article_count")
        .eq("active", True)
        .gte("impact_score", min_impact)
        .gte("article_count", 3)
        .order("impact_score", desc=True)
    )
    stories = query.execute().data

    if force:
        # Regenerate all, including stories that already have analyses
        todo = stories
    else:
        # Filter out stories that already have analyses
        existing = supabase.table("analyses").select("story_id").execute().data
        existing_ids = {r["story_id"] for r in existing}
        todo = [s for s in stories if s["id"] not in existing_ids]

    if limit:
        todo = todo[:limit]

    if not todo:
        print("No stories need backfill.")
        return

    mode = "FORCE regenerating" if force else "Generating"
    print(f"{mode} analyses for {len(todo)} stories...")
    print(f"Estimated cost: ~${len(todo) * 0.01:.2f}")
    print()

    generated = 0
    errors = 0
    for i, s in enumerate(todo):
        try:
            print(f"  [{i + 1}/{len(todo)}] {s['topic'][:60]}...")
            result = generate_analyses(story_ids=[s["id"]], max_per_cycle=1, force=force)
            if result["generated"] > 0:
                generated += 1
            else:
                print("    Skipped (no articles or already fresh)")
        except Exception as e:
            print(f"    ERROR: {e}")
            errors += 1

    print(f"\nDone: {generated} generated, {errors} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill analyses for scored stories")
    parser.add_argument("--limit", type=int, default=None, help="Max stories to process")
    parser.add_argument("--min-impact", type=int, default=0, help="Minimum impact_score threshold")
    parser.add_argument("--force", action="store_true", help="Regenerate even if analysis exists")
    args = parser.parse_args()
    backfill(limit=args.limit, min_impact=args.min_impact, force=args.force)
