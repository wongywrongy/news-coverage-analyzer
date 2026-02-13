"""
ClearSignal pipeline — CLI entry point and daemon scheduler.

Stages can be run individually or as a full pipeline.

Usage:
    python -m pipeline.main                  # full pipeline (all stages)
    python -m pipeline.main ingest           # ingest only
    python -m pipeline.main cluster          # cluster only
    python -m pipeline.main score            # score only
    python -m pipeline.main scrape           # scrape only
    python -m pipeline.main analyze          # analyze only
    python -m pipeline.main --daemon         # daemon mode (full, recurring)
    python -m pipeline.main --dry-run        # dry-run ingest (no DB writes)
    python -m pipeline.main ingest --dry-run # dry-run a specific stage
"""

from __future__ import annotations

import argparse
import importlib
import logging
import signal
import sys
import threading
import time
from datetime import UTC, datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

from config.settings import settings
from pipeline.ingest import run_ingestion
from pipeline.process import run_analysis, run_clustering, run_scoring, run_scraping, run_selection

logger = logging.getLogger(__name__)
console = Console()

# ── Dependency check ──────────────────────────────────────────────────────

REQUIRED_PACKAGES = [
    ("httpx", "httpx"),
    ("feedparser", "feedparser"),
    ("supabase", "supabase"),
    ("openai", "openai"),
    ("anthropic", "anthropic"),
    ("sentence_transformers", "sentence-transformers"),
    ("hdbscan", "hdbscan"),
    ("numpy", "numpy"),
    ("sklearn", "scikit-learn"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("apscheduler", "apscheduler"),
    ("rich", "rich"),
    ("nltk", "nltk"),
    ("trafilatura", "trafilatura"),
]


def check_dependencies() -> None:
    """Verify all required packages are importable before running the pipeline."""
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        console.print(f"\n[bold red]Missing dependencies:[/bold red] {', '.join(missing)}")
        console.print(f"[dim]Run:[/dim] pip install {' '.join(missing)}")
        sys.exit(1)

BANNER = r"""
   ___  _                  ___  _                    _
  / __\| |  ___   __ _  _ / __\(_)  __ _  _ __    __ _| |
 / /   | | / _ \ / _` || '__/\__ \ | / _` || '_ \  / _` || |
/ /___ | ||  __/| (_| || |   ___) || (_| || | | || (_| || |
\____/ |_| \___| \__,_||_|  |____/ \__, ||_| |_| \__,_||_|
                                    |___/
"""

STAGES = {
    "ingest":    "Fetch, normalize, deduplicate, embed, store",
    "cluster":   "Assign, discover, split, label, rename, merge, validate",
    "validate":  "Filter non-current topics (historical, evergreen)",
    "entities":  "Extract named entities from topics (GPT-4o-mini)",
    "graph":     "Update entity graph (edges, strengths, importance)",
    "score":     "Impact, coverage, attention, sentiment, timeline, gaps, ranking, insights",
    "heat":      "Recompute heat scores (front-page prominence, no AI)",
    "select":    "GPT-4o-mini editorial selection for analysis",
    "scrape":    "Extract article bodies via trafilatura",
    "analyze":   "Generate Claude-powered neutral analyses",
}


# ── Banner ─────────────────────────────────────────────────────────────────


def _print_banner(mode: str, stage: str | None = None) -> None:
    """Print the ClearSignal startup banner."""
    title = Text()
    title.append("ClearSignal", style="bold blue")
    title.append(" Pipeline", style="bold white")

    subtitle_parts = []
    if stage:
        subtitle_parts.append(f"Stage: [bold cyan]{stage}[/bold cyan]")
    else:
        subtitle_parts.append(f"Mode: [bold cyan]{mode}[/bold cyan]")
    subtitle_parts.append(f"Time: [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")

    console.print()
    console.print(Panel(
        "\n".join(subtitle_parts),
        title=title,
        border_style="blue",
        padding=(1, 3),
    ))
    console.print()


def _print_stage_header(name: str, description: str) -> None:
    """Print a stage header line."""
    console.rule(f"[bold]{name}[/bold]  [dim]{description}[/dim]")


def _print_done(duration: float | None = None) -> None:
    """Print completion message."""
    msg = "[bold green]Done.[/bold green]"
    if duration is not None:
        msg += f"  [dim]({duration:.1f}s)[/dim]"
    console.print(f"\n{msg}\n")


# ── Individual stage runners ───────────────────────────────────────────────


def stage_ingest(dry_run: bool = False) -> None:
    """Run the ingest stage."""
    _print_stage_header("Ingest", STAGES["ingest"])
    t0 = time.time()
    run_ingestion(dry_run=dry_run)
    _print_done(time.time() - t0)


def stage_cluster() -> None:
    """Run the cluster stage."""
    _print_stage_header("Cluster", STAGES["cluster"])
    t0 = time.time()
    run_clustering()
    _print_done(time.time() - t0)


def stage_validate() -> None:
    """Run the validate stage (standalone, outside of cluster)."""
    _print_stage_header("Validate", STAGES["validate"])
    t0 = time.time()
    from clustering.validate import validate_topics
    result = validate_topics()
    console.print(
        f"  Validated: {result['validated']}, "
        f"Rejected: {result['rejected']}, "
        f"Accepted: {result['accepted']}"
    )
    _print_done(time.time() - t0)


def stage_entities() -> None:
    """Run the entity extraction stage."""
    _print_stage_header("Entities", STAGES["entities"])
    t0 = time.time()
    from pipeline.extract_entities import extract_entities
    result = extract_entities()
    console.print(
        f"  Extracted: {result['extracted']}, "
        f"Entities found: {result['entities_found']}, "
        f"Errors: {result['errors']}"
    )
    _print_done(time.time() - t0)


def stage_graph() -> None:
    """Run the graph update stage."""
    _print_stage_header("Graph", STAGES["graph"])
    t0 = time.time()
    from pipeline.update_graph import update_graph
    result = update_graph()
    console.print(
        f"  Edges: {result['edges_created']}, "
        f"Strengths: {result['strengths_updated']}, "
        f"Entities updated: {result['entities_updated']}"
    )
    _print_done(time.time() - t0)


def stage_score() -> None:
    """Run the score stage."""
    _print_stage_header("Score", STAGES["score"])
    t0 = time.time()
    run_scoring()
    _print_done(time.time() - t0)


def stage_heat() -> None:
    """Run the heat scoring stage (standalone recompute)."""
    _print_stage_header("Heat", STAGES["heat"])
    t0 = time.time()
    from scoring.heat import score_heat
    result = score_heat()
    console.print(f"  Scored: {result['scored']} stories")
    _print_done(time.time() - t0)


def stage_select() -> dict:
    """Run the editorial selection stage."""
    _print_stage_header("Select", STAGES["select"])
    t0 = time.time()
    result = run_selection()
    _print_done(time.time() - t0)
    return result


def stage_scrape(selected_story_ids: list[int] | None = None) -> None:
    """Run the scrape stage."""
    _print_stage_header("Scrape", STAGES["scrape"])
    t0 = time.time()
    run_scraping(limit=50, selected_story_ids=selected_story_ids)
    _print_done(time.time() - t0)


def stage_analyze() -> None:
    """Run the analyze stage."""
    _print_stage_header("Analyze", STAGES["analyze"])
    t0 = time.time()
    run_analysis()
    _print_done(time.time() - t0)


STAGE_RUNNERS = {
    "ingest":    stage_ingest,
    "cluster":   stage_cluster,
    "validate":  stage_validate,
    "entities":  stage_entities,
    "graph":     stage_graph,
    "score":     stage_score,
    "heat":      stage_heat,
    "select":    stage_select,
    "scrape":    stage_scrape,
    "analyze":   stage_analyze,
}


# ── Pipeline functions ─────────────────────────────────────────────────────


def run_full(dry_run: bool = False) -> None:
    """Execute the full pipeline: ingest → cluster → score → select → scrape → analyze."""
    _print_banner("Full pipeline")
    t0 = time.time()

    result = run_ingestion(dry_run=dry_run)

    if not dry_run and result.new_stored > 0:
        stage_cluster()
        stage_score()

    if not dry_run:
        selection_result = stage_select()

        # Pass selected story IDs to scraper when selection succeeded
        selected_ids = None
        if (
            settings.selection_enabled
            and not selection_result.get("error")
            and not selection_result.get("disabled")
            and selection_result.get("selected", 0) > 0
        ):
            from db.queries import get_selected_story_ids
            selected_ids = get_selected_story_ids()

        stage_scrape(selected_story_ids=selected_ids)

    if not dry_run:
        stage_analyze()

    elapsed = time.time() - t0
    console.print()
    console.print(Panel(
        f"[bold]Fetched:[/bold] {result.total_fetched}  "
        f"[bold]Stored:[/bold] {result.new_stored}  "
        f"[bold]Errors:[/bold] {result.errors}  "
        f"[bold]Time:[/bold] {elapsed:.1f}s",
        title="[bold green]Pipeline Complete[/bold green]",
        border_style="green",
        padding=(0, 2),
    ))
    console.print()


def run_single_stage(stage: str, dry_run: bool = False) -> None:
    """Execute a single pipeline stage."""
    _print_banner("Single stage", stage=stage)
    runner = STAGE_RUNNERS[stage]
    if stage == "ingest":
        runner(dry_run=dry_run)
    else:
        runner()


def run_daemon(interval_minutes: int = 15) -> None:
    """Run the full pipeline on a recurring schedule."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    _print_banner("Daemon")
    console.print(
        f"  Schedule: every [bold]{interval_minutes}[/bold] minutes\n"
        f"  Press [bold]Ctrl+C[/bold] to stop\n",
    )

    shutdown = threading.Event()

    def _on_signal(signum: int, _frame: object) -> None:
        logger.info("Shutdown requested (signal %d) — finishing current cycle…", signum)
        shutdown.set()

    signal.signal(signal.SIGINT, _on_signal)
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (OSError, ValueError):
        pass

    scheduler = BackgroundScheduler()

    def _scheduled_cycle() -> None:
        run_full(dry_run=False)
        jobs = scheduler.get_jobs()
        if jobs and jobs[0].next_run_time:
            next_time = jobs[0].next_run_time.strftime("%H:%M:%S")
            console.print(f"\n[dim]Next run at: {next_time}[/dim]\n")

    scheduler.add_job(
        _scheduled_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="ingestion",
        name="ClearSignal pipeline",
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Scheduler started — interval=%d min", interval_minutes)

    while not shutdown.is_set():
        shutdown.wait(timeout=1.0)

    scheduler.shutdown(wait=True)
    console.print("\n[bold]Shutdown complete.[/bold]")


# ── CLI entry point ────────────────────────────────────────────────────────


def main() -> None:
    """Parse CLI arguments and dispatch."""
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.main",
        description="ClearSignal news pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "stages:\n"
            "  ingest    Fetch, normalize, deduplicate, embed, store\n"
            "  cluster   Assign, discover, split, label, rename, merge, validate\n"
            "  validate  Filter non-current topics (standalone)\n"
            "  entities  Extract named entities from topics\n"
            "  graph     Update entity graph (edges, strengths, importance)\n"
            "  score     Impact, coverage, attention, sentiment, timeline, gaps, ranking, insights\n"
            "  heat      Recompute heat scores (front-page prominence, no AI)\n"
            "  select    GPT-4o-mini editorial selection for analysis\n"
            "  scrape    Extract article bodies via trafilatura\n"
            "  analyze   Generate Claude-powered neutral analyses\n"
            "\n"
            "examples:\n"
            "  python -m pipeline.main                  Full pipeline\n"
            "  python -m pipeline.main ingest           Ingest only\n"
            "  python -m pipeline.main entities         Extract entities only\n"
            "  python -m pipeline.main graph            Update entity graph only\n"
            "  python -m pipeline.main select           Select only\n"
            "  python -m pipeline.main analyze          Analyze only\n"
            "  python -m pipeline.main --daemon         Daemon mode\n"
            "  python -m pipeline.main ingest --dry-run Dry-run ingest"
        ),
    )
    parser.add_argument(
        "stage",
        nargs="?",
        choices=list(STAGES.keys()),
        default=None,
        help="Run a specific pipeline stage (omit for full pipeline)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run full pipeline on a recurring schedule",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and process without DB writes",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        metavar="N",
        help="Minutes between daemon runs (default: 15)",
    )
    args = parser.parse_args()

    # ── Configure logging with Rich ─────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=console,
            rich_tracebacks=True,
            show_path=False,
        )],
    )

    # ── Dependency check ────────────────────────────────────────────────
    check_dependencies()

    # ── Dispatch ────────────────────────────────────────────────────────
    if args.daemon:
        run_daemon(interval_minutes=args.interval)
    elif args.stage:
        run_single_stage(args.stage, dry_run=args.dry_run)
    else:
        run_full(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
