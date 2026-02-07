"""
ClearSignal — One-time data cleanup script.

Fixes stale scores, bad labels, and historical content left over from
the source_name → source_domain bias-lookup bug.

Usage:
    cd backend
    .venv/Scripts/python.exe -m pipeline.cleanup           # full run
    .venv/Scripts/python.exe -m pipeline.cleanup --audit    # audit only
    .venv/Scripts/python.exe -m pipeline.cleanup --step 2   # run single step
"""

from __future__ import annotations

import argparse
import logging
import re
from datetime import datetime, timezone

from rich.console import Console
from rich.logging import RichHandler

from db import queries as db

logger = logging.getLogger(__name__)
console = Console()


# ── Step 1: Audit ────────────────────────────────────────────────────────────


def audit() -> None:
    """Print current state of all active stories for review."""

    stories = db.get_active_stories()
    console.print(f"\nActive stories: [bold]{len(stories)}[/bold]")

    # Bad labels
    bad_labels = _find_bad_labels(stories)
    console.print(f"Bad labels: [bold]{len(bad_labels)}[/bold]")
    for s in bad_labels:
        topic = (s.get("topic") or "")[:60]
        console.print(f"  #{s['id']}: '{topic}…'")

    # Stale stories
    stale = [s for s in stories if s.get("status") == "stale"]
    console.print(f"Stale stories: [bold]{len(stale)}[/bold]")

    # Lincoln check
    lincoln = [s for s in stories if "lincoln" in (s.get("topic") or "").lower()]
    for s in lincoln:
        articles = db.get_articles_for_story(s["id"])
        console.print(
            f"\nLincoln story #{s['id']} — {len(articles)} articles:"
        )
        for a in articles[:10]:
            pub = (a.get("published_at") or "?")[:10]
            title = (a.get("title") or "")[:80]
            console.print(f"  [{pub}] {a.get('source_domain')}: {title}")

    # Scoring gaps
    unscored = [s for s in stories if (s.get("impact_score") or 0) == 0]
    never_scored = [s for s in stories if s.get("impact_scored_at") is None]
    console.print(f"Stories with impact=0: [bold]{len(unscored)}[/bold]")
    console.print(f"Stories never scored: [bold]{len(never_scored)}[/bold]")


# ── Step 2: Fix labels ──────────────────────────────────────────────────────


def fix_labels() -> None:
    """Re-label every story that has a bad topic label."""

    stories = db.get_active_stories()
    bad = _find_bad_labels(stories)
    bad_ids = [s["id"] for s in bad]

    if not bad_ids:
        console.print("No bad labels found.")
        return

    for s in bad:
        topic = (s.get("topic") or "")[:60]
        console.print(f"  Bad label: #{s['id']}: '{topic}…'")

    console.print(f"\nRe-labeling {len(bad_ids)} stories…")
    from clustering.label import label_stories

    result = label_stories(story_ids=bad_ids)
    console.print(
        f"Labeled: {result['labeled']}, errors: {result['errors']}"
    )

    # Validate new labels — fall back to central article title if still bad
    for item in result.get("labels", []):
        new = item["new_topic"]
        if len(new) > 80 or "\n" in new or "#" in new:
            console.print(
                f"  Still bad after re-label: #{item['story_id']}: "
                f"'{new[:60]}'"
            )
            articles = db.get_articles_for_story(item["story_id"])
            if articles:
                fallback = (articles[0].get("title") or "")[:60]
                fallback = re.sub(
                    r"\s*[-|—]\s*[A-Z][\w\s.&']+$", "", fallback
                ).strip()
                if fallback:
                    db.update_story_metadata(
                        item["story_id"], topic=fallback
                    )
                    console.print(f"    Fallback label: '{fallback}'")


# ── Step 3: Clean stale ─────────────────────────────────────────────────────


def clean_stale() -> None:
    """Deactivate stories that are stale + low-impact, or very old."""

    stories = db.get_active_stories()
    deactivated = 0

    for s in stories:
        status = s.get("status")
        impact = s.get("impact_score") or 0
        article_count = s.get("article_count") or 0

        should_deactivate = False
        reason = ""

        # Stale + low impact + small cluster
        if status == "stale" and impact < 20 and article_count < 5:
            should_deactivate = True
            reason = (
                f"stale, low impact ({impact}), "
                f"small ({article_count} articles)"
            )

        # Very old with no recent activity
        last_updated = s.get("last_updated")
        if last_updated:
            if isinstance(last_updated, str):
                try:
                    last_updated = datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00")
                    )
                except ValueError:
                    last_updated = None
            if last_updated:
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                hours_since = (
                    datetime.now(timezone.utc) - last_updated
                ).total_seconds() / 3600
                if hours_since > 120 and impact < 30:
                    should_deactivate = True
                    reason = (
                        f"inactive {hours_since:.0f}h, "
                        f"low impact ({impact})"
                    )

        if should_deactivate:
            db.deactivate_story(s["id"])
            deactivated += 1
            topic = (s.get("topic") or "")[:50]
            console.print(
                f"  Deactivated #{s['id']}: '{topic}' — {reason}"
            )

    console.print(f"\nDeactivated {deactivated} stories")


# ── Step 4: Force re-score ───────────────────────────────────────────────────


def force_rescore() -> dict:
    """Re-run all scoring with corrected bias lookup."""

    console.rule("[bold]Force re-scoring all active stories[/bold]")

    # Impact
    from scoring.impact import score_impacts

    console.print("Running impact scoring (force=True)…")
    impact_result = score_impacts(force=True)
    console.print(f"  Scored: {impact_result['scored']}")
    console.print(f"  Outliers flagged: {impact_result['outliers_flagged']}")
    console.print(f"  Errors: {impact_result['errors']}")

    # Unassign outliers
    outliers = impact_result.get("outlier_articles", [])
    if outliers:
        console.print(f"\n  Unassigning {len(outliers)} outlier articles…")
        for o in outliers:
            db.update_article_story(o["article_id"], None)
            console.print(
                f"    Article #{o['article_id']} from story "
                f"#{o['story_id']}: {o['reason']}"
            )

    # Attention
    from scoring.attention import score_attention

    console.print("\nRunning attention scoring…")
    attention_result = score_attention()
    console.print(f"  Scored: {attention_result['scored']}")

    # Sentiment
    from scoring.sentiment import analyze_sentiment

    console.print("\nRunning sentiment analysis…")
    sentiment_result = analyze_sentiment()
    console.print(f"  Analyzed: {sentiment_result['analyzed']}")

    # Timeline
    from scoring.timeline import update_timelines

    console.print("\nUpdating timelines…")
    timeline_result = update_timelines()
    console.print(f"  Updated: {timeline_result['updated']}")

    # Gaps
    from scoring.gaps import detect_gaps

    console.print("\nDetecting gaps…")
    gap_result = detect_gaps()
    console.print(f"  Buried: {len(gap_result['buried'])}")
    console.print(f"  Overcovered: {len(gap_result['overcovered'])}")
    console.print(f"  Balanced: {len(gap_result['balanced'])}")

    return {
        "impact": impact_result,
        "attention": attention_result,
        "sentiment": sentiment_result,
        "gaps": gap_result,
    }


# ── Step 5: Validate ────────────────────────────────────────────────────────


def validate() -> None:
    """Print final state for human review."""

    stories = db.get_active_stories()
    console.rule(f"[bold]FINAL STATE: {len(stories)} active stories[/bold]")

    # Top 10 by impact
    by_impact = sorted(
        stories, key=lambda s: s.get("impact_score") or 0, reverse=True
    )
    console.print("\n[bold]TOP 10 BY IMPACT:[/bold]")
    for s in by_impact[:10]:
        console.print(
            f"  {s.get('impact_score', 0):5.0f} impact | "
            f"{s.get('attention_score', 0):5.1f} attention | "
            f"{s.get('article_count', 0):3d} articles | "
            f"{(s.get('topic') or '?')[:50]}"
        )

    # Top 5 buried
    buried = sorted(
        stories,
        key=lambda s: (s.get("impact_score") or 0)
        - (s.get("attention_score") or 0),
        reverse=True,
    )
    console.print("\n[bold]TOP 5 BURIED (underreported):[/bold]")
    for s in buried[:5]:
        gap = (s.get("impact_score") or 0) - (s.get("attention_score") or 0)
        if gap < 20:
            break
        console.print(
            f"  gap +{gap:.0f} | impact={s.get('impact_score', 0):.0f} "
            f"attention={s.get('attention_score', 0):.0f} | "
            f"{(s.get('topic') or '?')[:50]}"
        )

    # Top 5 overcovered
    overcovered = sorted(
        stories,
        key=lambda s: (s.get("impact_score") or 0)
        - (s.get("attention_score") or 0),
    )
    console.print("\n[bold]TOP 5 OVERCOVERED (overreported):[/bold]")
    for s in overcovered[:5]:
        gap = (s.get("impact_score") or 0) - (s.get("attention_score") or 0)
        if gap > -20:
            break
        console.print(
            f"  gap {gap:.0f} | impact={s.get('impact_score', 0):.0f} "
            f"attention={s.get('attention_score', 0):.0f} | "
            f"{(s.get('topic') or '?')[:50]}"
        )

    # Sentiment divergence
    console.print("\n[bold]SENTIMENT DIVERGENCE (left vs right):[/bold]")
    with_sentiment = [
        s
        for s in stories
        if s.get("sentiment_left") is not None
        and s.get("sentiment_right") is not None
    ]
    by_divergence = sorted(
        with_sentiment,
        key=lambda s: abs(
            (s.get("sentiment_left") or 0) - (s.get("sentiment_right") or 0)
        ),
        reverse=True,
    )
    for s in by_divergence[:5]:
        left = s.get("sentiment_left", 0)
        right = s.get("sentiment_right", 0)
        console.print(
            f"  L={left:+.2f} R={right:+.2f} "
            f"(div={abs(left - right):.2f}) | "
            f"{(s.get('topic') or '?')[:50]}"
        )

    # Remaining bad labels
    bad = [
        s
        for s in stories
        if len(s.get("topic", "") or "") > 80
        or "\n" in (s.get("topic") or "")
        or "#" in (s.get("topic") or "")
    ]
    if bad:
        console.print(f"\n[red]{len(bad)} stories still have bad labels[/red]")
    else:
        console.print("\n[green]All labels look clean[/green]")

    # Sentiment coverage check
    left_count = sum(
        1 for s in stories if s.get("sentiment_left") is not None
    )
    right_count = sum(
        1 for s in stories if s.get("sentiment_right") is not None
    )
    console.print(
        f"\nSentiment coverage: {left_count} stories with left data, "
        f"{right_count} with right data"
    )
    if left_count < len(stories) * 0.3:
        console.print(
            "  [yellow]Less than 30% have left sentiment "
            "— bias lookup may still be broken[/yellow]"
        )
    if right_count < len(stories) * 0.3:
        console.print(
            "  [yellow]Less than 30% have right sentiment "
            "— bias lookup may still be broken[/yellow]"
        )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _find_bad_labels(stories: list[dict]) -> list[dict]:
    """Return stories whose topic label looks malformed."""
    bad = []
    for s in stories:
        topic = s.get("topic") or ""
        if any(
            [
                not topic,
                len(topic) > 80,
                "\n" in topic,
                "#" in topic,
                topic.count(",") > 2,
                len(topic.split()) < 2,
                len(topic.split()) > 10,
                " - " in topic,
                " | " in topic,
                "..." in topic,
                '"' in topic,
                "captures" in topic.lower(),
                topic.lower().startswith("this "),
            ]
        ):
            bad.append(s)
    return bad


# ── Main ─────────────────────────────────────────────────────────────────────

STEPS = {
    1: ("AUDIT", audit),
    2: ("FIX LABELS", fix_labels),
    3: ("CLEAN STALE", clean_stale),
    4: ("FORCE RE-SCORE", force_rescore),
    5: ("VALIDATE", validate),
}


def main() -> None:
    """Run full cleanup sequence (or a single step)."""

    parser = argparse.ArgumentParser(
        prog="python -m pipeline.cleanup",
        description="ClearSignal — one-time data cleanup",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Run audit only (step 1)",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=list(STEPS.keys()),
        help="Run a single step (1-5)",
    )
    args = parser.parse_args()

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True, show_path=False)
        ],
    )

    console.rule("[bold blue]ClearSignal — Data Cleanup[/bold blue]")

    if args.audit:
        audit()
        return

    if args.step:
        name, fn = STEPS[args.step]
        console.print(f"\n--- STEP {args.step}: {name} ---")
        fn()
        return

    # Full run
    for step_num, (name, fn) in STEPS.items():
        console.print(f"\n--- STEP {step_num}: {name} ---")
        fn()

    console.rule("[bold green]CLEANUP COMPLETE[/bold green]")


if __name__ == "__main__":
    main()
