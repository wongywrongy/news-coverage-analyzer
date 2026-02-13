"""
Supabase health check — verifies database connectivity, table integrity,
data freshness, scoring health, and source spectrum coverage.

Usage (from backend/):
    python -m scripts.health_check
    python -m scripts.health_check --verbose
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import UTC, datetime

# Ensure backend/ is on sys.path so `db.*` and `config.*` resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Terminal formatting (matches scripts/audit.py) ───────────────────────────


class Style:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def header(title: str) -> None:
    width = 60
    print(f"\n{Style.BLUE}{'=' * width}{Style.RESET}")
    print(f"  {Style.BOLD}{title}{Style.RESET}")
    print(f"{Style.BLUE}{'=' * width}{Style.RESET}\n")


def subheader(title: str) -> None:
    print(f"  {Style.CYAN}{Style.BOLD}{title}{Style.RESET}")


def row_ok(label: str, detail: str = "") -> None:
    suffix = f"  {Style.DIM}{detail}{Style.RESET}" if detail else ""
    print(f"    {Style.GREEN}PASS{Style.RESET}  {label}{suffix}")


def row_warn(label: str, detail: str = "") -> None:
    suffix = f"  {Style.DIM}{detail}{Style.RESET}" if detail else ""
    print(f"    {Style.YELLOW}WARN{Style.RESET}  {label}{suffix}")


def row_fail(label: str, detail: str = "") -> None:
    suffix = f"  {Style.DIM}{detail}{Style.RESET}" if detail else ""
    print(f"    {Style.RED}FAIL{Style.RESET}  {label}{suffix}")


def row_info(label: str, detail: str = "") -> None:
    suffix = f"  {Style.DIM}{detail}{Style.RESET}" if detail else ""
    print(f"    {Style.DIM} -- {Style.RESET}  {label}{suffix}")


def divider() -> None:
    print(f"  {Style.DIM}{'_' * 50}{Style.RESET}")


def mask(value: str | None) -> str:
    """Mask a secret value, showing only the first 4 and last 4 characters."""
    if not value:
        return "(not set)"
    if len(value) <= 12:
        return value[:2] + "*" * (len(value) - 2)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


# ── Health check engine ──────────────────────────────────────────────────────


class HealthCheck:
    """Runs all checks and tracks pass / warn / fail counts."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.passed = 0
        self.warned = 0
        self.failed = 0
        self._client = None

    # -- result tracking helpers --

    def _pass(self, label: str, detail: str = "") -> None:
        self.passed += 1
        row_ok(label, detail)

    def _warn(self, label: str, detail: str = "") -> None:
        self.warned += 1
        row_warn(label, detail)

    def _fail(self, label: str, detail: str = "") -> None:
        self.failed += 1
        row_fail(label, detail)

    # ══════════════════════════════════════════════════════════════════════
    #  1. Environment variables
    # ══════════════════════════════════════════════════════════════════════

    def check_env(self) -> None:
        header("\U0001f511 Environment Variables")

        env_vars = [
            ("SUPABASE_URL", os.environ.get("SUPABASE_URL")),
            ("SUPABASE_KEY", os.environ.get("SUPABASE_KEY")),
            ("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY")),
            ("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY")),
        ]

        # Also try loading from settings (which reads .env)
        try:
            from config.settings import settings
            if not env_vars[0][1]:
                env_vars[0] = ("SUPABASE_URL", settings.supabase_url)
            if not env_vars[1][1]:
                env_vars[1] = ("SUPABASE_KEY", settings.supabase_key)
            if not env_vars[2][1]:
                env_vars[2] = ("OPENAI_API_KEY", settings.openai_api_key)
            if not env_vars[3][1]:
                env_vars[3] = ("ANTHROPIC_API_KEY", settings.anthropic_api_key)
        except Exception:
            pass  # settings may not be loadable yet; fall through to env check

        for name, value in env_vars:
            if value:
                self._pass(f"{name:<24s} {mask(value)}")
            else:
                self._fail(f"{name:<24s} (not set)")

    # ══════════════════════════════════════════════════════════════════════
    #  2. Supabase connection
    # ══════════════════════════════════════════════════════════════════════

    def check_connection(self) -> bool:
        header("\U0001f50c Supabase Connection")

        try:
            from db.client import get_client
            self._client = get_client()
            # Smoke test: count articles
            result = self._client.table("articles").select("count", count="exact").execute()
            self._pass(
                "Connected to Supabase",
                f"articles count = {result.count}",
            )
            return True
        except Exception as exc:
            self._fail("Cannot connect to Supabase", str(exc))
            return False

    # ══════════════════════════════════════════════════════════════════════
    #  3. Table existence and row counts
    # ══════════════════════════════════════════════════════════════════════

    def check_tables(self) -> None:
        header("\U0001f4cb Table Existence & Row Counts")

        required_tables = ["articles", "stories", "analyses", "story_daily_counts"]
        optional_tables = ["entities", "topic_entities", "entity_relationships"]

        subheader("Required tables")
        for table in required_tables:
            self._check_table(table, required=True)
        print()

        subheader("Optional tables")
        for table in optional_tables:
            self._check_table(table, required=False)

    def _check_table(self, table: str, required: bool) -> None:
        try:
            result = self._client.table(table).select("count", count="exact").execute()
            count = result.count if result.count is not None else 0
            self._pass(f"{table:<28s} {count:>8,} rows")
        except Exception as exc:
            err_str = str(exc)
            # Detect "relation does not exist" as table-not-found
            if "does not exist" in err_str or "404" in err_str or "relation" in err_str:
                if required:
                    self._fail(f"{table:<28s} TABLE NOT FOUND")
                else:
                    self._warn(f"{table:<28s} table not found (optional)")
            else:
                if required:
                    self._fail(f"{table:<28s} query error", err_str[:80])
                else:
                    self._warn(f"{table:<28s} query error", err_str[:80])

    # ══════════════════════════════════════════════════════════════════════
    #  4. Data freshness
    # ══════════════════════════════════════════════════════════════════════

    def check_freshness(self) -> None:
        header("\U0001f552 Data Freshness")

        # Latest article age
        subheader("Latest article")
        try:
            result = (
                self._client.table("articles")
                .select("title, published_at, source_name")
                .order("published_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                pub = row.get("published_at")
                title = (row.get("title") or "")[:60]
                source = row.get("source_name") or ""
                if pub:
                    dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    age = datetime.now(UTC) - dt
                    hours = age.total_seconds() / 3600
                    age_str = f"{hours:.1f}h ago"
                    if hours < 2:
                        self._pass(f"Latest article: {age_str}", f"{title} ({source})")
                    elif hours < 12:
                        self._warn(f"Latest article: {age_str}", f"{title} ({source})")
                    else:
                        self._fail(f"Latest article: {age_str} -- pipeline may be stalled", f"{title} ({source})")
                else:
                    self._warn("Latest article has no published_at")
            else:
                self._fail("No articles found in database")
        except Exception as exc:
            self._fail("Could not query latest article", str(exc)[:80])

        print()

        # Hottest topic heat score
        subheader("Hottest topic (by heat score)")
        try:
            result = (
                self._client.table("stories")
                .select("id, topic, heat")
                .eq("active", True)
                .order("heat", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                heat = row.get("heat") or 0
                topic = (row.get("topic") or "")[:50]
                story_id = row.get("id")
                if heat > 0:
                    self._pass(f"Top heat: {heat:.1f}", f"Story #{story_id}: {topic}")
                else:
                    self._warn(f"Top heat: {heat:.1f} -- all stories have zero heat")
            else:
                self._warn("No active stories found")
        except Exception as exc:
            self._warn("Could not query heat scores", str(exc)[:80])

    # ══════════════════════════════════════════════════════════════════════
    #  5. Scoring health
    # ══════════════════════════════════════════════════════════════════════

    def check_scoring(self) -> None:
        header("\U0001f4ca Scoring Health")

        try:
            result = (
                self._client.table("stories")
                .select("id, impact_score, coverage_score")
                .eq("active", True)
                .execute()
            )
            stories = result.data or []
        except Exception as exc:
            self._fail("Could not query stories for scoring health", str(exc)[:80])
            return

        if not stories:
            self._warn("No active stories to evaluate scoring")
            return

        total = len(stories)

        # Impact score distribution
        subheader("Impact score distribution")
        impacts = [s.get("impact_score") or 0 for s in stories]
        scored = [v for v in impacts if v > 0]
        unscored = total - len(scored)

        if scored:
            avg_impact = sum(scored) / len(scored)
            max_impact = max(scored)
            min_impact = min(scored)
            self._pass(
                f"{len(scored)}/{total} stories have impact scores",
                f"min={min_impact:.0f}  avg={avg_impact:.0f}  max={max_impact:.0f}",
            )
            if self.verbose:
                # Histogram buckets
                buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
                for v in scored:
                    if v <= 20:
                        buckets["0-20"] += 1
                    elif v <= 40:
                        buckets["21-40"] += 1
                    elif v <= 60:
                        buckets["41-60"] += 1
                    elif v <= 80:
                        buckets["61-80"] += 1
                    else:
                        buckets["81-100"] += 1
                for bucket, count in buckets.items():
                    bar = "#" * min(count, 30)
                    row_info(f"  {bucket:>6s}  {count:>4d}  {bar}")
        else:
            self._fail("No stories have impact scores")

        if unscored > 0:
            self._warn(f"{unscored} active stories have no impact score")

        print()

        # Coverage score distribution
        subheader("Coverage score distribution")
        coverages = [s.get("coverage_score") or 0 for s in stories]
        cov_scored = [v for v in coverages if v > 0]

        if cov_scored:
            avg_cov = sum(cov_scored) / len(cov_scored)
            max_cov = max(cov_scored)
            self._pass(
                f"{len(cov_scored)}/{total} stories have coverage scores",
                f"avg={avg_cov:.1f}  max={max_cov:.1f}",
            )
        else:
            self._warn("No stories have coverage scores")

    # ══════════════════════════════════════════════════════════════════════
    #  6. Analysis coverage
    # ══════════════════════════════════════════════════════════════════════

    def check_analysis_coverage(self) -> None:
        header("\U0001f4dd Analysis Coverage")

        try:
            # Get active story count
            stories_result = (
                self._client.table("stories")
                .select("id", count="exact")
                .eq("active", True)
                .execute()
            )
            total_stories = stories_result.count or 0

            # Get analyses count
            analyses_result = (
                self._client.table("analyses")
                .select("story_id", count="exact")
                .execute()
            )
            total_analyses = analyses_result.count or 0

        except Exception as exc:
            self._fail("Could not query analysis coverage", str(exc)[:80])
            return

        if total_stories == 0:
            self._warn("No active stories to evaluate analysis coverage")
            return

        pct = (total_analyses / total_stories) * 100 if total_stories > 0 else 0
        detail = f"{total_analyses}/{total_stories} active stories have analyses"

        if pct >= 80:
            self._pass(f"Analysis coverage: {pct:.0f}%", detail)
        elif pct >= 50:
            self._warn(f"Analysis coverage: {pct:.0f}%", detail)
        else:
            self._fail(f"Analysis coverage: {pct:.0f}%", detail)

        if self.verbose and total_analyses > 0:
            # Check analysis freshness
            print()
            subheader("Analysis freshness")
            try:
                result = (
                    self._client.table("analyses")
                    .select("story_id, generated_at")
                    .order("generated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    row = result.data[0]
                    gen_at = row.get("generated_at")
                    if gen_at:
                        dt = datetime.fromisoformat(str(gen_at).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=UTC)
                        age = datetime.now(UTC) - dt
                        hours = age.total_seconds() / 3600
                        row_info(f"Newest analysis: {hours:.1f}h ago (story #{row.get('story_id')})")
            except Exception:
                pass  # non-critical verbose check

    # ══════════════════════════════════════════════════════════════════════
    #  7. Source spectrum coverage
    # ══════════════════════════════════════════════════════════════════════

    def check_source_spectrum(self) -> None:
        header("\U0001f30d Source Spectrum Coverage")

        try:
            from config.sources import SOURCE_BIAS
        except ImportError:
            self._fail("Cannot import SOURCE_BIAS from config.sources")
            return

        # Classify sources into left / center / right buckets
        spectrum: dict[str, list[str]] = {
            "left": [],
            "center": [],
            "right": [],
        }
        for domain, meta in SOURCE_BIAS.items():
            score = meta.get("score", 0)
            if score < -0.15:
                spectrum["left"].append(domain)
            elif score > 0.15:
                spectrum["right"].append(domain)
            else:
                spectrum["center"].append(domain)

        subheader("Configured sources (from config/sources.py)")
        total_sources = len(SOURCE_BIAS)
        for bucket in ("left", "center", "right"):
            count = len(spectrum[bucket])
            pct = (count / total_sources * 100) if total_sources > 0 else 0
            self._pass(f"{bucket:<8s}  {count:>3d} sources ({pct:.0f}%)")

        print()

        # Check actual article ingestion by bias group in the DB
        subheader("Ingested articles by spectrum")
        try:
            # Fetch all articles (Supabase defaults to 1000 rows)
            all_articles: list[dict] = []
            page_size = 1000
            offset = 0
            while True:
                result = (
                    self._client.table("articles")
                    .select("source_domain")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                batch = result.data or []
                all_articles.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            articles = all_articles
        except Exception as exc:
            self._warn("Could not query articles for spectrum check", str(exc)[:80])
            return

        if not articles:
            self._warn("No articles in database to check spectrum coverage")
            return

        # Count articles per spectrum bucket
        bucket_counts: Counter = Counter()
        domain_counts: Counter = Counter()
        for a in articles:
            domain = a.get("source_domain") or ""
            domain_counts[domain] += 1
            meta = SOURCE_BIAS.get(domain)
            if meta:
                score = meta.get("score", 0)
                if score < -0.15:
                    bucket_counts["left"] += 1
                elif score > 0.15:
                    bucket_counts["right"] += 1
                else:
                    bucket_counts["center"] += 1
            else:
                bucket_counts["unknown"] += 1

        total_articles = len(articles)
        for bucket in ("left", "center", "right"):
            count = bucket_counts.get(bucket, 0)
            pct = (count / total_articles * 100) if total_articles > 0 else 0
            if pct >= 10:
                self._pass(f"{bucket:<8s}  {count:>6,} articles ({pct:.0f}%)")
            elif pct >= 5:
                self._warn(f"{bucket:<8s}  {count:>6,} articles ({pct:.0f}%) -- thin coverage")
            else:
                self._fail(f"{bucket:<8s}  {count:>6,} articles ({pct:.0f}%) -- weak representation")

        unknown = bucket_counts.get("unknown", 0)
        if unknown > 0:
            unk_pct = (unknown / total_articles * 100) if total_articles > 0 else 0
            self._warn(f"unknown   {unknown:>6,} articles ({unk_pct:.0f}%) -- not in SOURCE_BIAS")

        if self.verbose:
            print()
            subheader("Top 15 sources by article count")
            for domain, count in domain_counts.most_common(15):
                meta = SOURCE_BIAS.get(domain)
                label = meta.get("label", "?") if meta else "?"
                pct = (count / total_articles * 100) if total_articles > 0 else 0
                row_info(f"{domain:<30s}  {count:>5,} ({pct:4.1f}%)  [{label}]")

    # ══════════════════════════════════════════════════════════════════════
    #  Summary
    # ══════════════════════════════════════════════════════════════════════

    def print_summary(self) -> None:
        header("\U0001f3c1 Summary")

        total = self.passed + self.warned + self.failed
        print(f"    {Style.GREEN}{self.passed:>4d}{Style.RESET}  passed")
        print(f"    {Style.YELLOW}{self.warned:>4d}{Style.RESET}  warnings")
        print(f"    {Style.RED}{self.failed:>4d}{Style.RESET}  failed")
        print(f"    {Style.DIM}{total:>4d}{Style.RESET}  total checks")
        print()

        if self.failed == 0 and self.warned == 0:
            print(f"  {Style.GREEN}{Style.BOLD}All systems healthy.{Style.RESET}")
        elif self.failed == 0:
            print(f"  {Style.YELLOW}{Style.BOLD}Healthy with warnings.{Style.RESET}")
        else:
            print(f"  {Style.RED}{Style.BOLD}Issues detected -- review failures above.{Style.RESET}")
        print()

    # ══════════════════════════════════════════════════════════════════════
    #  Runner
    # ══════════════════════════════════════════════════════════════════════

    def run(self) -> int:
        """Run all health checks. Returns exit code (0 = healthy, 1 = failures)."""
        print(f"\n{Style.BOLD}  ClearSignal -- Supabase Health Check{Style.RESET}")
        print(f"  {Style.DIM}{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}{Style.RESET}")

        # 1. Environment variables
        self.check_env()

        # 2. Connection
        connected = self.check_connection()
        if not connected:
            print(f"\n  {Style.RED}Cannot continue without a database connection.{Style.RESET}\n")
            self.print_summary()
            return 1

        # 3. Tables
        self.check_tables()

        # 4. Freshness
        self.check_freshness()

        # 5. Scoring
        self.check_scoring()

        # 6. Analysis coverage
        self.check_analysis_coverage()

        # 7. Source spectrum
        self.check_source_spectrum()

        # Summary
        self.print_summary()

        return 1 if self.failed > 0 else 0


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ClearSignal Supabase health check",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show extra detail (histograms, top sources, analysis freshness)",
    )
    args = parser.parse_args()

    hc = HealthCheck(verbose=args.verbose)
    exit_code = hc.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
