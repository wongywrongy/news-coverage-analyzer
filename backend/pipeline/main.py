"""
ClearSignal pipeline — CLI entry point and daemon scheduler.

Usage:
    python -m pipeline.main              # daemon mode (default)
    python -m pipeline.main --once       # single run, then exit
    python -m pipeline.main --dry-run    # fetch only, no DB writes
    python -m pipeline.main --interval 5 # custom interval in minutes
"""

import argparse
import logging
import signal
import threading
from datetime import datetime, timezone

from rich.console import Console
from rich.logging import RichHandler

from config.settings import settings
from pipeline.ingest import run_ingestion
from pipeline.process import run_analysis, run_clustering, run_scoring

logger = logging.getLogger(__name__)
console = Console()


# ── Pipeline functions ────────────────────────────────────────────────────


def run_once(dry_run: bool = False) -> None:
    """Execute a single ingestion cycle.

    Args:
        dry_run: If True, fetch and process without DB writes.
    """
    console.rule("[bold blue]ClearSignal — Ingestion Cycle[/bold blue]")

    result = run_ingestion(dry_run=dry_run)

    # ── Clustering + Scoring ────────────────────────────────────────
    if not dry_run and result.new_stored > 0:
        run_clustering()
        run_scoring()

    # ── Analysis — always check, even without new articles ────────
    # Stories may need analysis due to staleness or first-run population
    if not dry_run:
        run_analysis()

    logger.info(
        "Cycle complete: %d fetched, %d stored, %d errors (%.1fs)",
        result.total_fetched,
        result.new_stored,
        result.errors,
        result.duration_seconds,
    )


def run_daemon(interval_minutes: int = 15) -> None:
    """Run the ingestion pipeline on a recurring schedule.

    Uses APScheduler with an IntervalTrigger.  Runs immediately on start,
    then every *interval_minutes* minutes.  Shuts down cleanly on Ctrl+C.

    Args:
        interval_minutes: Minutes between ingestion runs (default 15).
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    console.rule("[bold blue]ClearSignal — Daemon Mode[/bold blue]")
    console.print(
        f"  Schedule: every [bold]{interval_minutes}[/bold] minutes\n"
        f"  Press [bold]Ctrl+C[/bold] to stop\n",
    )

    # ── Graceful shutdown via signal handler ──────────────────────────
    shutdown = threading.Event()

    def _on_signal(signum: int, _frame: object) -> None:
        logger.info(
            "Shutdown requested (signal %d) — finishing current cycle…",
            signum,
        )
        shutdown.set()

    signal.signal(signal.SIGINT, _on_signal)
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (OSError, ValueError):
        pass  # SIGTERM not reliably available on all platforms

    # ── Configure scheduler ───────────────────────────────────────────
    scheduler = BackgroundScheduler()

    def _scheduled_cycle() -> None:
        """Run one cycle and print next scheduled time."""
        run_once(dry_run=False)
        jobs = scheduler.get_jobs()
        if jobs and jobs[0].next_run_time:
            next_time = jobs[0].next_run_time.strftime("%H:%M:%S")
            console.print(f"\n[dim]Next run at: {next_time}[/dim]\n")

    scheduler.add_job(
        _scheduled_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="ingestion",
        name="ClearSignal ingestion",
        next_run_time=datetime.now(timezone.utc),  # run immediately
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Scheduler started — interval=%d min", interval_minutes)

    # ── Block main thread until shutdown signal ───────────────────────
    while not shutdown.is_set():
        shutdown.wait(timeout=1.0)

    scheduler.shutdown(wait=True)
    console.print("\n[bold]Shutdown complete.[/bold]")


# ── CLI entry point ───────────────────────────────────────────────────────


def main() -> None:
    """Parse CLI arguments and dispatch to run_once or run_daemon."""
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.main",
        description="ClearSignal news ingestion pipeline",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ingestion cycle and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and process without DB writes (implies --once)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        metavar="N",
        help="Minutes between daemon runs (default: 15)",
    )
    args = parser.parse_args()

    # ── Configure logging with Rich ───────────────────────────────────
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

    # ── Dispatch ──────────────────────────────────────────────────────
    if args.dry_run:
        run_once(dry_run=True)
    elif args.once:
        run_once(dry_run=False)
    else:
        run_daemon(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
