"""GPT-4o-mini significance scoring, cluster validation, and topic renaming.

Three sub-steps:
  1. Significance scoring — score each active story 0-100 for public significance
  2. Cluster validation — check if high-significance stories are coherent
  3. Topic renaming — fix vague topic labels

Usage:
    cd backend
    python -m scripts.filter_topics                 # full run
    python -m scripts.filter_topics --dry-run       # score but don't write
    python -m scripts.filter_topics --limit 50      # only process 50 stories
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from openai import OpenAI

from config.settings import settings
from db import queries as db

logger = logging.getLogger(__name__)

MIN_SIGNIFICANCE = settings.min_significance_score  # 45


# ── Step 1: Significance scoring ─────────────────────────────────────────────


def score_significance(
    stories: list[dict],
    client: OpenAI,
    dry_run: bool = False,
) -> dict:
    """Score each story 0-100 for public significance using GPT-4o-mini.

    Returns: {"scored": int, "deactivated": int, "errors": int}
    """
    stats = {"scored": 0, "deactivated": 0, "errors": 0}

    # Batch stories into groups of 10 for efficiency
    batch_size = 10
    for i in range(0, len(stories), batch_size):
        batch = stories[i : i + batch_size]
        batch_items = []
        for s in batch:
            articles = db.get_articles_for_story(s["id"])
            headlines = [a.get("title", "") for a in articles[:3]]
            batch_items.append({
                "id": s["id"],
                "topic": s.get("topic", ""),
                "article_count": s.get("article_count", 0),
                "source_count": s.get("source_count", 0),
                "headlines": headlines,
            })

        prompt = (
            "Rate each news story's PUBLIC SIGNIFICANCE from 0-100.\n"
            "Consider: How many people are affected? How serious are the consequences?\n"
            "Does it affect policy, safety, health, rights, or money?\n\n"
            "Celebrity gossip, sports scores, entertainment = 0-25\n"
            "Local/niche business news = 25-45\n"
            "National policy, health, economics, rights = 50-80\n"
            "Major crisis, war, constitutional change = 80-100\n\n"
            "Stories:\n"
            + json.dumps(batch_items, indent=2)
            + "\n\nRespond with JSON array: [{\"id\": N, \"score\": N}]"
        )

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences
            if raw.startswith("```"):
                lines = raw.split("\n")
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                raw = "\n".join(lines).strip()

            scores = json.loads(raw)
        except Exception as exc:
            logger.exception("GPT scoring failed for batch starting at index %d: %s", i, exc)
            stats["errors"] += len(batch)
            continue

        for entry in scores:
            sid = entry.get("id")
            score = entry.get("score", 0)
            if sid is None:
                continue

            stats["scored"] += 1

            if dry_run:
                logger.info("Story #%d: significance=%d (dry run)", sid, score)
                continue

            # Write score to DB
            try:
                db.get_client().table("stories").update(
                    {"significance_score": score}
                ).eq("id", sid).execute()
            except Exception as exc:
                logger.warning("Failed to update significance for story #%d: %s", sid, exc)
                stats["errors"] += 1
                continue

            # Deactivate low-significance stories
            if score < MIN_SIGNIFICANCE:
                try:
                    db.deactivate_story(sid)
                    stats["deactivated"] += 1
                    logger.info("Deactivated story #%d (significance=%d)", sid, score)
                except Exception as exc:
                    logger.warning("Failed to deactivate story #%d: %s", sid, exc)

    return stats


# ── Step 2: Cluster validation ───────────────────────────────────────────────


def validate_clusters(
    stories: list[dict],
    client: OpenAI,
    dry_run: bool = False,
) -> dict:
    """Check if high-significance stories are coherent clusters.

    Returns: {"checked": int, "incoherent": int, "errors": int}
    """
    stats = {"checked": 0, "incoherent": 0, "errors": 0}

    for s in stories:
        sig = s.get("significance_score") or 0
        if sig < MIN_SIGNIFICANCE:
            continue

        articles = db.get_articles_for_story(s["id"])
        if len(articles) < 3:
            continue

        headlines = [a.get("title", "") for a in articles[:10]]
        prompt = (
            f"Topic: {s.get('topic', '')}\n"
            f"Headlines:\n" + "\n".join(f"- {h}" for h in headlines) + "\n\n"
            "Are these headlines about the SAME specific event or development? "
            "Answer JSON: {\"coherent\": true/false, \"reason\": \"brief explanation\"}"
        )

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                raw = "\n".join(lines).strip()

            result = json.loads(raw)
            stats["checked"] += 1

            if not result.get("coherent", True):
                stats["incoherent"] += 1
                logger.info(
                    "Incoherent cluster #%d (%s): %s",
                    s["id"],
                    s.get("topic", ""),
                    result.get("reason", ""),
                )
                if not dry_run:
                    db.deactivate_story(s["id"])

        except Exception as exc:
            logger.debug("Cluster validation failed for story #%d: %s", s["id"], exc)
            stats["errors"] += 1

    return stats


# ── Step 3: Topic renaming ───────────────────────────────────────────────────


def _is_vague_topic(topic: str) -> bool:
    """Check if topic label is vague and needs renaming."""
    if not topic:
        return True
    words = topic.split()
    if len(words) > 6:
        return True
    vague_markers = ["various", "multiple", "several", "different", "related", "update"]
    if any(m in topic.lower() for m in vague_markers):
        return True
    return False


def rename_topics(
    stories: list[dict],
    client: OpenAI,
    dry_run: bool = False,
) -> dict:
    """Fix vague topic labels using GPT-4o-mini.

    Returns: {"renamed": int, "skipped": int, "errors": int}
    """
    stats = {"renamed": 0, "skipped": 0, "errors": 0}

    vague = [s for s in stories if _is_vague_topic(s.get("topic", ""))]

    if not vague:
        logger.info("No vague topics found")
        return stats

    # Batch for efficiency
    batch_size = 10
    for i in range(0, len(vague), batch_size):
        batch = vague[i : i + batch_size]
        items = []
        for s in batch:
            articles = db.get_articles_for_story(s["id"])
            headlines = [a.get("title", "") for a in articles[:5]]
            items.append({
                "id": s["id"],
                "current_topic": s.get("topic", ""),
                "headlines": headlines,
            })

        prompt = (
            "For each story, write a clear, specific topic label (max 8 words). "
            "It should read like a newspaper section header.\n\n"
            "Stories:\n" + json.dumps(items, indent=2)
            + "\n\nRespond with JSON array: [{\"id\": N, \"topic\": \"New Topic\"}]"
        )

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                raw = "\n".join(lines).strip()

            results = json.loads(raw)
        except Exception as exc:
            logger.exception("Topic rename failed for batch starting at index %d: %s", i, exc)
            stats["errors"] += len(batch)
            continue

        for entry in results:
            sid = entry.get("id")
            new_topic = entry.get("topic", "").strip()
            if not sid or not new_topic:
                stats["skipped"] += 1
                continue

            stats["renamed"] += 1
            if dry_run:
                logger.info("Story #%d: '%s' → '%s' (dry run)", sid,
                            next((s.get("topic") for s in batch if s["id"] == sid), "?"),
                            new_topic)
            else:
                try:
                    db.update_story_metadata(sid, topic=new_topic)
                except Exception as exc:
                    logger.warning("Failed to rename story #%d: %s", sid, exc)
                    stats["errors"] += 1

    return stats


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    from rich.console import Console
    from rich.logging import RichHandler

    console = Console()

    parser = argparse.ArgumentParser(
        prog="python -m scripts.filter_topics",
        description="Score significance, validate clusters, rename topics",
    )
    parser.add_argument("--dry-run", action="store_true", help="Score without writing to DB")
    parser.add_argument("--limit", type=int, default=0, help="Max stories to process (0=all)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    console.rule("[bold blue]Topic Filtering[/bold blue]")

    client = OpenAI(api_key=settings.openai_api_key)
    stories = db.get_active_stories()

    if args.limit > 0:
        stories = stories[: args.limit]

    console.print(f"  Active stories: {len(stories)}")
    if args.dry_run:
        console.print("  [yellow]DRY RUN — no writes[/yellow]")

    # Step 1: Significance scoring
    console.print("\n[bold]Step 1: Significance Scoring[/bold]")
    sig_result = score_significance(stories, client, dry_run=args.dry_run)
    console.print(f"  Scored: {sig_result['scored']}")
    console.print(f"  Deactivated: {sig_result['deactivated']}")
    console.print(f"  Errors: {sig_result['errors']}")

    # Refresh stories (some may have been deactivated)
    if not args.dry_run:
        stories = db.get_active_stories()
        if args.limit > 0:
            stories = stories[: args.limit]

    # Step 2: Cluster validation
    console.print("\n[bold]Step 2: Cluster Validation[/bold]")
    val_result = validate_clusters(stories, client, dry_run=args.dry_run)
    console.print(f"  Checked: {val_result['checked']}")
    console.print(f"  Incoherent: {val_result['incoherent']}")
    console.print(f"  Errors: {val_result['errors']}")

    # Refresh again
    if not args.dry_run:
        stories = db.get_active_stories()
        if args.limit > 0:
            stories = stories[: args.limit]

    # Step 3: Topic renaming
    console.print("\n[bold]Step 3: Topic Renaming[/bold]")
    rename_result = rename_topics(stories, client, dry_run=args.dry_run)
    console.print(f"  Renamed: {rename_result['renamed']}")
    console.print(f"  Skipped: {rename_result['skipped']}")
    console.print(f"  Errors: {rename_result['errors']}")

    console.rule("[bold green]Done[/bold green]")


if __name__ == "__main__":
    main()
