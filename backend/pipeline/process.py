"""Wire clustering, scoring, and analysis modules together in the correct order.

This file contains NO business logic — just calls modules in sequence
and prints a summary.

Full pipeline order:
    INGEST -> CLUSTER -> SCORE -> ANALYZE

    Clustering: assign -> discover -> split -> label -> merge
    Scoring:    impact -> handle outliers -> attention -> sentiment -> timeline -> gaps
    Analysis:   staleness check -> generate (top 5 priority) -> store

Usage:
    python -m pipeline.process
"""

import logging
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from clustering.assign import assign_articles_to_stories
from clustering.discover import discover_new_clusters
from clustering.label import label_stories
from clustering.merge import merge_similar_stories
from clustering.split import split_oversized_stories
from db import queries as db
from scoring.attention import score_attention
from scoring.gaps import detect_gaps
from scoring.impact import score_impacts
from scoring.sentiment import analyze_sentiment
from scoring.timeline import update_timelines

logger = logging.getLogger(__name__)
console = Console()


def run_clustering() -> dict:
    """Execute full clustering pipeline.

    Order matters:
    1. Assign unassigned articles to existing stories (fast path, with size cap)
    2. Discover new clusters from remaining unassigned articles
    3. Split oversized stories into finer-grained sub-stories
    4. Label ALL stories that need it (new + split + old placeholders)
    5. Merge any stories that have become too similar

    Returns combined stats from all steps.
    """
    console.rule("[bold cyan]Clustering[/bold cyan]")

    # 1. Fast path — assign to known stories (with size cap)
    assign_result = assign_articles_to_stories()

    # 2. Discover new clusters from leftovers
    discover_result = discover_new_clusters()

    # 3. Split any mega-clusters
    split_result = split_oversized_stories()

    # 4. Label ALL stories that need it (not just new ones)
    label_result = label_stories()

    # 5. Merge converged stories
    merge_result = merge_similar_stories()

    # 6. Summary
    active_stories = db.get_active_stories()
    _print_summary(assign_result, discover_result, split_result, merge_result, len(active_stories))

    combined = {
        "assign": assign_result,
        "discover": discover_result,
        "split": split_result,
        "label": label_result,
        "merge": merge_result,
        "active_stories": len(active_stories),
    }

    logger.info(
        "Clustering complete: %d assigned, %d new clusters, %d split, %d labeled, %d merged, %d active.",
        assign_result["assigned"],
        discover_result["clusters_found"],
        split_result["stories_split"],
        label_result["labeled"],
        merge_result["merges_performed"],
        len(active_stories),
    )

    return combined


def _print_summary(
    assign: dict, discover: dict, split: dict, merge: dict, active_total: int
) -> None:
    """Print a rich summary panel."""
    noise = discover["articles_noise"] + assign["unassigned"] - discover["articles_clustered"]
    if noise < 0:
        noise = 0

    lines = Text()
    lines.append("Assigned to existing stories:  ", style="dim")
    lines.append(f"{assign['assigned']}\n", style="bold")
    lines.append("New clusters discovered:       ", style="dim")
    lines.append(f"{discover['clusters_found']}\n", style="bold")
    lines.append("Stories split:                 ", style="dim")
    lines.append(f"{split['stories_split']} ({split['new_stories_created']} new)\n", style="bold")
    lines.append("Articles still unassigned:     ", style="dim")
    lines.append(f"{noise} (noise)\n", style="bold")
    lines.append("Stories merged:                ", style="dim")
    lines.append(f"{merge['merges_performed']}\n", style="bold")
    lines.append("Active stories total:          ", style="dim")
    lines.append(f"{active_total}", style="bold green")

    console.print(Panel(lines, title="Clustering Summary", border_style="cyan"))


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING
# ═══════════════════════════════════════════════════════════════════════════════


def run_scoring() -> dict:
    """Execute full scoring pipeline.

    Order:
    1. Impact scoring (Claude Haiku + cluster validation)
    2. Handle outliers flagged by impact scoring
    3. Attention scoring (pure math)
    4. Sentiment analysis
    5. Timeline updates
    6. Gap detection (depends on impact + attention being complete)

    Returns combined stats.
    """
    console.rule("[bold magenta]Scoring[/bold magenta]")

    # Fetch all data ONCE — each scoring module would otherwise
    # independently call get_articles_for_story() for every story.
    all_stories = db.get_active_stories()
    story_articles: dict[int, list[dict]] = {}
    for story in all_stories:
        story_articles[story["id"]] = db.get_articles_for_story(story["id"])

    # 1. Impact scoring
    impact_result = score_impacts(story_articles=story_articles)

    # 2. Handle outliers — unassign misfit articles so they can be
    #    re-clustered in the next clustering cycle.
    outliers = impact_result.get("outlier_articles", [])
    for outlier in outliers:
        db.update_article_story(outlier["article_id"], None)
        logger.info(
            "Unassigned outlier article #%d from story #%d: %s",
            outlier["article_id"],
            outlier["story_id"],
            outlier["reason"],
        )

    # 3. Attention scoring
    attention_result = score_attention(story_articles=story_articles)

    # 4. Sentiment analysis
    sentiment_result = analyze_sentiment(story_articles=story_articles)

    # 5. Timeline updates
    timeline_result = update_timelines(story_articles=story_articles)

    # 6. Gap detection (requires impact + attention, not articles)
    gap_result = detect_gaps()

    # 7. Deactivate stale low-impact stories (>72h old, score <20)
    deactivated = 0
    now = datetime.now(timezone.utc)
    for story in all_stories:
        if story.get("status") != "stale" or (story.get("impact_score") or 0) >= 20:
            continue
        last_updated = story.get("last_updated") or story.get("updated_at")
        if not last_updated:
            continue
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            except ValueError:
                continue
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        hours_since = (now - last_updated).total_seconds() / 3600
        if hours_since > 72:
            db.deactivate_story(story["id"])
            deactivated += 1
            logger.info(
                "Deactivated stale low-impact story #%d: %s",
                story["id"], story.get("topic"),
            )

    # 8. Summary
    _print_scoring_summary(
        impact_result, outliers, attention_result,
        sentiment_result, timeline_result, gap_result,
    )

    combined = {
        "impact": impact_result,
        "outliers_handled": len(outliers),
        "attention": attention_result,
        "sentiment": sentiment_result,
        "timeline": timeline_result,
        "gaps": gap_result,
        "deactivated": deactivated,
    }

    logger.info(
        "Scoring complete: %d impact, %d outliers, %d attention, "
        "%d sentiment, %d timelines, %d/%d/%d buried/over/balanced.",
        impact_result["scored"],
        len(outliers),
        attention_result["scored"],
        sentiment_result["analyzed"],
        timeline_result["updated"],
        len(gap_result["buried"]),
        len(gap_result["overcovered"]),
        len(gap_result["balanced"]),
    )

    return combined


def _print_scoring_summary(
    impact: dict,
    outliers: list[dict],
    attention: dict,
    sentiment: dict,
    timeline: dict,
    gaps: dict,
) -> None:
    """Print a rich scoring summary panel + top buried/overcovered stories."""
    lines = Text()
    lines.append("Impact scores computed:     ", style="dim")
    lines.append(f"{impact['scored']}\n", style="bold")
    lines.append("Outlier articles flagged:   ", style="dim")
    lines.append(f"{len(outliers)}\n", style="bold")
    lines.append("Attention scores computed:  ", style="dim")
    lines.append(f"{attention['scored']}\n", style="bold")
    lines.append("Sentiment analyzed:         ", style="dim")
    lines.append(f"{sentiment['analyzed']}\n", style="bold")
    lines.append("Timelines updated:          ", style="dim")
    lines.append(f"{timeline['updated']}\n", style="bold")
    lines.append("\n", style="dim")
    lines.append("Buried stories:             ", style="dim")
    lines.append(f"{len(gaps['buried'])}\n", style="bold red")
    lines.append("Overcovered stories:        ", style="dim")
    lines.append(f"{len(gaps['overcovered'])}\n", style="bold yellow")
    lines.append("Balanced stories:           ", style="dim")
    lines.append(f"{len(gaps['balanced'])}", style="bold green")

    console.print(Panel(lines, title="Scoring Summary", border_style="magenta"))

    # Top 3 buried
    if gaps["buried"]:
        console.print("\n[bold red]BURIED (underreported):[/bold red]")
        for s in gaps["buried"][:3]:
            console.print(
                f"  [dim]\"{s['topic']}\"[/dim] — impact: {s['impact_score']}, "
                f"attention: {s['attention_score']}, gap: +{s['gap']}"
            )

    # Top 3 overcovered
    if gaps["overcovered"]:
        console.print("\n[bold yellow]OVERCOVERED (overreported):[/bold yellow]")
        for s in gaps["overcovered"][:3]:
            console.print(
                f"  [dim]\"{s['topic']}\"[/dim] — impact: {s['impact_score']}, "
                f"attention: {s['attention_score']}, gap: {s['gap']}"
            )

    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def run_analysis() -> dict:
    """Generate neutral analyses for stories that need them.

    1. Get priority list of stories needing analysis
    2. Generate analyses (capped at 5 per cycle)
    3. Print summary

    Returns: analysis generation stats
    """
    console.rule("[bold green]Analysis Generation[/bold green]")

    from analysis.staleness import get_stories_needing_analysis
    from analysis.generator import generate_analyses

    # Get priority list
    story_ids = get_stories_needing_analysis(max_results=5)

    if not story_ids:
        console.print("  No stories need analysis this cycle.")
        return {"generated": 0, "skipped": 0, "errors": 0}

    console.print(f"  {len(story_ids)} stories need analysis")

    # Generate
    result = generate_analyses(story_ids=story_ids)

    # Summary
    console.print(f"  Generated: {result['generated']}")
    console.print(f"  Errors: {result['errors']}")
    for a in result.get("analyses", []):
        console.print(f"    → {a.get('headline', '?')[:60]}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  __main__ — standalone test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    from rich.logging import RichHandler

    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    cluster_result = run_clustering()
    print(f"\nAssigned:        {cluster_result['assign']['assigned']}")
    print(f"New clusters:    {cluster_result['discover']['clusters_found']}")
    print(f"Stories split:   {cluster_result['split']['stories_split']}")
    print(f"Labels created:  {cluster_result['label']['labeled']}")
    print(f"Merges:          {cluster_result['merge']['merges_performed']}")
    print(f"Active stories:  {cluster_result['active_stories']}")

    scoring_result = run_scoring()
    print(f"\nImpact scored:   {scoring_result['impact']['scored']}")
    print(f"Outliers:        {scoring_result['outliers_handled']}")
    print(f"Attention:       {scoring_result['attention']['scored']}")
    print(f"Sentiment:       {scoring_result['sentiment']['analyzed']}")
    print(f"Timelines:       {scoring_result['timeline']['updated']}")
    print(f"Buried:          {len(scoring_result['gaps']['buried'])}")
    print(f"Overcovered:     {len(scoring_result['gaps']['overcovered'])}")
