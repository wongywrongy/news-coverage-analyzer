"""Proof-of-concept analysis generation — 10 hand-picked stories.

Selects 10 stories across different test scenarios (buried, overcovered,
partisan, high-impact, medium) and generates analyses for human review.

NOT part of the regular pipeline. One-time test to evaluate quality
before generating for all stories.

Usage:
    python -m pipeline.poc_analysis
"""

import logging
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from analysis.generator import generate_analyses
from db import queries as db

logger = logging.getLogger(__name__)
console = Console()

MIN_ARTICLES = 3


# ── Selection helpers ───────────────────────────────────────────────


def _is_eligible(story: dict, actual_counts: dict[int, int]) -> bool:
    """Hard filters — must pass ALL to be considered."""
    sid = story["id"]
    actual = actual_counts.get(sid, 0)
    if actual < MIN_ARTICLES:
        return False
    if (story.get("impact_score") or 0) <= 0:
        return False
    if (story.get("attention_score") or 0) <= 0:
        return False
    topic = story.get("topic", "")
    if len(topic) > 80 or "#" in topic:
        return False
    return True


def _gap(story: dict) -> float:
    """Compute coverage gap: positive = buried, negative = overcovered."""
    return (story.get("impact_score") or 0) - (story.get("attention_score") or 0)


def _sentiment_divergence(story: dict) -> float:
    """Compute left-vs-right sentiment spread."""
    left = story.get("sentiment_left")
    right = story.get("sentiment_right")
    if left is None or right is None:
        return 0.0
    return abs(left - right)


def select_stories(
    stories: list[dict], actual_counts: dict[int, int]
) -> list[tuple[dict, str, str]]:
    """Pick 10 stories across test categories.

    Returns: [(story_dict, category, reason), ...]
    """
    eligible = [s for s in stories if _is_eligible(s, actual_counts)]
    if not eligible:
        console.print("[red]No eligible stories found![/red]")
        return []

    selected: list[tuple[dict, str, str]] = []
    used_ids: set[int] = set()

    def _pick(pool: list[dict], n: int, category: str, reason_fn) -> None:
        for s in pool:
            if s["id"] in used_ids:
                continue
            used_ids.add(s["id"])
            selected.append((s, category, reason_fn(s)))
            if len([x for x in selected if x[1] == category]) >= n:
                break

    # a) 2 BURIED — highest positive gap
    buried = sorted(eligible, key=_gap, reverse=True)
    _pick(
        buried, 2, "BURIED",
        lambda s: (
            f"High impact ({s.get('impact_score'):.0f}), low coverage "
            f"({s.get('attention_score'):.0f}) — gap +{_gap(s):.0f}"
        ),
    )

    # b) 2 OVERCOVERED — highest negative gap
    overcovered = sorted(eligible, key=_gap)
    _pick(
        overcovered, 2, "OVERCOVERED",
        lambda s: (
            f"Low impact ({s.get('impact_score'):.0f}), high coverage "
            f"({s.get('attention_score'):.0f}) — gap {_gap(s):.0f}"
        ),
    )

    # c) 2 HIGH-IMPACT — highest impact, article_count >= 10
    high_impact = sorted(
        [s for s in eligible if actual_counts.get(s["id"], 0) >= 10],
        key=lambda s: s.get("impact_score") or 0,
        reverse=True,
    )
    _pick(
        high_impact, 2, "HIGH-IMPACT",
        lambda s: (
            f"Impact {s.get('impact_score'):.0f}, "
            f"{actual_counts.get(s['id'], 0)} articles — large multi-source story"
        ),
    )

    # d) 2 PARTISAN — highest sentiment divergence
    partisan = sorted(eligible, key=_sentiment_divergence, reverse=True)
    _pick(
        partisan, 2, "PARTISAN",
        lambda s: (
            f"Sentiment left={s.get('sentiment_left')}, "
            f"right={s.get('sentiment_right')} — divergence {_sentiment_divergence(s):.2f}"
        ),
    )

    # e) 2 MEDIUM — balanced gap (closest to 0), 5-15 articles
    medium = sorted(
        [s for s in eligible if 5 <= actual_counts.get(s["id"], 0) <= 15],
        key=lambda s: abs(_gap(s)),
    )
    _pick(
        medium, 2, "MEDIUM",
        lambda s: (
            f"Balanced gap ({_gap(s):+.0f}), "
            f"{actual_counts.get(s['id'], 0)} articles — baseline quality test"
        ),
    )

    # If we still need more (some categories may be empty), fill from top impact
    if len(selected) < 10:
        remaining = sorted(
            eligible,
            key=lambda s: s.get("impact_score") or 0,
            reverse=True,
        )
        _pick(
            remaining, 10 - len(selected), "FILL",
            lambda s: f"Impact {s.get('impact_score'):.0f} — filling to reach 10",
        )

    return selected


# ── Display helpers ─────────────────────────────────────────────────


def print_selection(selected: list[tuple[dict, str, str]], actual_counts: dict[int, int]) -> None:
    """Print the selected stories grouped by category."""
    console.print()
    console.rule("[bold blue]PROOF OF CONCEPT — 10 STORIES FOR ANALYSIS[/bold blue]")
    console.print()

    current_cat = ""
    for i, (story, category, reason) in enumerate(selected, 1):
        if category != current_cat:
            current_cat = category
            style = {
                "BURIED": "red",
                "OVERCOVERED": "yellow",
                "HIGH-IMPACT": "green",
                "PARTISAN": "magenta",
                "MEDIUM": "cyan",
                "FILL": "dim",
            }.get(category, "white")
            console.print(f"\n[bold {style}]{category}:[/bold {style}]")

        sid = story["id"]
        actual = actual_counts.get(sid, 0)
        source_count = story.get("source_count") or 0
        console.print(
            f"  [bold]#{i}[/bold]  Story #{sid}: "
            f"[dim]\"{story.get('topic', '?')[:55]}\"[/dim]"
        )
        console.print(
            f"      impact={story.get('impact_score', 0):.0f}  "
            f"attention={story.get('attention_score', 0):.0f}  "
            f"gap={_gap(story):+.0f}  |  "
            f"{actual} articles, {source_count} sources"
        )
        console.print(f"      [dim]WHY: {reason}[/dim]")

    est_cost = len(selected) * 0.014
    console.print(f"\n[bold]Estimated cost: ~${est_cost:.2f}[/bold]")
    console.print()


def print_analysis(story: dict, category: str, analysis: dict) -> None:
    """Print a single analysis for human review."""
    console.print()
    header = Text()
    header.append(f"STORY: {story.get('topic', '?')}\n", style="bold")
    header.append(f"CATEGORY: {category}\n", style="bold")
    header.append(
        f"SCORES: impact={story.get('impact_score', 0):.0f}  "
        f"attention={story.get('attention_score', 0):.0f}  "
        f"gap={_gap(story):+.0f}",
        style="bold",
    )
    console.print(Panel(header, border_style="blue"))

    console.print(f"[bold]HEADLINE:[/bold] {analysis.get('headline', '(none)')}")
    console.print(f"[bold]DATELINE:[/bold] {analysis.get('dateline', '(none)')}")

    console.print(f"\n[bold]LEDE:[/bold]")
    console.print(f"  {analysis.get('lede', '(none)')}")

    console.print(f"\n[bold]CONTEXT:[/bold]")
    console.print(f"  {analysis.get('context', '(none)')}")

    contrasts = analysis.get("contrasts") or []
    if contrasts:
        console.print(f"\n[bold]CONTRASTS:[/bold]")
        for c in contrasts:
            console.print(f"  [bold]THEME:[/bold] {c.get('theme', '?')}")
            console.print(
                f"  {c.get('sourceA', '?')} ({c.get('biasA', '?')}): "
                f"{c.get('claimA', '?')}"
            )
            console.print("  vs.")
            console.print(
                f"  {c.get('sourceB', '?')} ({c.get('biasB', '?')}): "
                f"{c.get('claimB', '?')}"
            )
            console.print()

    facts = analysis.get("facts") or []
    if facts:
        console.print(f"[bold]FACT CHECKS:[/bold]")
        for f in facts:
            console.print(f"  [bold]CLAIM:[/bold] {f.get('claim', '?')}")
            console.print(f"  [bold]REALITY:[/bold] {f.get('reality', '?')}")
            verdict = f.get("verdict", "?")
            v_style = {
                "confirmed": "green",
                "misleading": "red",
                "lacks context": "yellow",
                "unverified": "dim",
            }.get(verdict, "white")
            console.print(f"  [bold]VERDICT:[/bold] [{v_style}]{verdict}[/{v_style}]")
            console.print()

    console.print(f"[bold]BOTTOM LINE:[/bold]")
    console.print(f"  {analysis.get('bottom_line', '(none)')}")

    console.print(f"\n[bold]COVERAGE NOTE:[/bold]")
    console.print(f"  {analysis.get('coverage_note', '(none)')}")


def print_checklist() -> None:
    """Print quality review checklist."""
    console.print()
    console.rule("[bold]QUALITY REVIEW CHECKLIST[/bold]")
    items = [
        "Headline is neutral (no opinion words)",
        "Lede answers who/what/when/where",
        "Contrasts pair real outlets from different political leans",
        "Fact verdicts are defensible",
        "Bottom line describes concrete impact on people",
        "Coverage note references actual numbers",
        "Buried stories note the under-coverage",
        "Overcovered stories note the disproportionate coverage",
        "Partisan stories present both sides without taking one",
    ]
    for item in items:
        console.print(f"  [ ] {item}")
    console.print()


# ── Main ────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
    )

    console.rule("[bold blue]ClearSignal — POC Analysis Generation[/bold blue]")
    console.print()

    # 1. Load all active stories
    stories = db.get_active_stories()
    if not stories:
        console.print("[red]No active stories found.[/red]")
        sys.exit(1)

    console.print(f"Loaded {len(stories)} active stories")

    # 2. Get actual article counts (stories.article_count can be stale)
    console.print("Checking actual article counts...")
    actual_counts: dict[int, int] = {}
    for s in stories:
        actual_counts[s["id"]] = len(db.get_articles_for_story(s["id"]))

    eligible = sum(
        1 for s in stories if _is_eligible(s, actual_counts)
    )
    console.print(f"Eligible stories (>= {MIN_ARTICLES} articles, scored, clean label): {eligible}")

    # 3. Select 10
    selected = select_stories(stories, actual_counts)
    if not selected:
        console.print("[red]Could not select any stories.[/red]")
        sys.exit(1)

    print_selection(selected, actual_counts)

    # 4. Generate analyses
    selected_ids = [s["id"] for s, _, _ in selected]
    console.rule("[bold green]Generating Analyses[/bold green]")
    console.print(f"Calling Claude Sonnet for {len(selected_ids)} stories...\n")

    result = generate_analyses(
        story_ids=selected_ids,
        max_per_cycle=len(selected_ids),
        force=True,
    )

    console.print(
        f"\n[bold]Result:[/bold] generated={result['generated']}  "
        f"skipped={result['skipped']}  errors={result['errors']}"
    )

    # 5. Display each analysis
    if result["generated"] > 0:
        console.rule("[bold blue]Generated Analyses[/bold blue]")

        # Build category lookup
        cat_lookup = {s["id"]: (cat, s) for s, cat, _ in selected}

        for entry in result["analyses"]:
            sid = entry["story_id"]
            analysis = db.get_analysis(sid)
            if not analysis:
                console.print(f"[red]Could not retrieve analysis for story #{sid}[/red]")
                continue
            cat, story = cat_lookup.get(sid, ("?", {}))
            print_analysis(story, cat, analysis)

    # 6. Summary
    console.print()
    console.rule("[bold]GENERATION SUMMARY[/bold]")
    console.print(f"  Generated:  {result['generated']}")
    console.print(f"  Skipped:    {result['skipped']} (< {MIN_ARTICLES} actual articles)")
    console.print(f"  Errors:     {result['errors']}")

    if result["skipped"] > 0:
        console.print(
            f"\n  [yellow]Note: {result['skipped']} stories were skipped because "
            f"their actual article count is below {MIN_ARTICLES}.[/yellow]"
        )

    # 7. Checklist
    print_checklist()


if __name__ == "__main__":
    main()
