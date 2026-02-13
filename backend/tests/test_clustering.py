"""Live integration validator for the clustering pipeline.

Runs against real Supabase data — NOT mocked.
Sections 3-7 actually run clustering modules and MUTATE data.

Usage:
    cd backend
    python -m tests.test_clustering
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.table import Table

console = Console()

# ── Result tracking ─────────────────────────────────────────────────────────

_results: list[dict] = []


def _record(
    check_id: str,
    status: str,
    message: str,
    *,
    critical: bool = False,
) -> None:
    """Record a check result and print it."""
    _results.append({
        "id": check_id,
        "status": status,
        "message": message,
        "critical": critical,
    })
    icon = {"PASS": "[green]✅ PASS[/green]",
            "WARN": "[yellow]⚠️  WARN[/yellow]",
            "FAIL": "[red]❌ FAIL[/red]",
            "INFO": "[blue]ℹ️  INFO[/blue]"}[status]
    console.print(f"  {icon}  {check_id}  {message}")


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 1: PRE-CONDITIONS
# ═════════════════════════════════════════════════════════════════════════════


def section_1_preconditions() -> None:
    console.rule("[bold]Section 1: Pre-conditions[/bold]")

    from db.client import get_client

    client = get_client()

    # 1.1 — Articles with embeddings
    try:
        result = (
            client.table("articles")
            .select("id", count="exact")
            .not_.is_("embedding", "null")
            .execute()
        )
        count = result.count or 0
        if count >= 100:
            _record("1.1", "PASS", f"Articles with embeddings: {count}")
        else:
            _record("1.1", "FAIL",
                    f"Not enough embedded articles for meaningful clustering ({count})",
                    critical=True)
    except Exception as exc:
        _record("1.1", "FAIL", f"Query error: {exc}", critical=True)

    # 1.2 — Articles with source bias labels
    try:
        result = (
            client.table("articles")
            .select("id", count="exact")
            .is_("source_bias", "null")
            .execute()
        )
        missing = result.count or 0
        if missing == 0:
            _record("1.2", "PASS", "All articles have bias labels")
        else:
            _record("1.2", "WARN", f"{missing} articles missing bias labels")

        # Print bias distribution
        dist_result = (
            client.table("articles")
            .select("source_bias")
            .not_.is_("source_bias", "null")
            .execute()
        )
        counts: dict[str, int] = {}
        for row in (dist_result.data or []):
            bias = row.get("source_bias") or "unknown"
            counts[bias] = counts.get(bias, 0) + 1
        dist_str = ", ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))
        _record("1.2", "INFO", f"Bias distribution: {dist_str}")
    except Exception as exc:
        _record("1.2", "FAIL", f"Query error: {exc}")

    # 1.3 — Embedding dimensions
    try:
        result = (
            client.table("articles")
            .select("embedding")
            .not_.is_("embedding", "null")
            .limit(5)
            .execute()
        )
        rows = result.data or []
        all_ok = True
        for row in rows:
            emb = row.get("embedding")
            if isinstance(emb, str):
                emb = json.loads(emb)
            dim = len(emb) if emb else 0
            if dim != 384:
                _record("1.3", "FAIL",
                        f"Embedding dimension mismatch: expected 384, got {dim}",
                        critical=True)
                all_ok = False
                break
        if all_ok:
            _record("1.3", "PASS", "All sampled embeddings are 384-dim")
    except Exception as exc:
        _record("1.3", "FAIL", f"Query error: {exc}", critical=True)

    # 1.4 — Stories table accessible
    try:
        result = (
            client.table("stories")
            .select("id", count="exact")
            .execute()
        )
        count = result.count or 0
        _record("1.4", "INFO", f"Existing stories: {count}")
    except Exception as exc:
        _record("1.4", "FAIL", f"Stories table inaccessible: {exc}", critical=True)


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 2: MODULE IMPORTS
# ═════════════════════════════════════════════════════════════════════════════


def section_2_imports() -> None:
    console.rule("[bold]Section 2: Module Imports[/bold]")

    modules = [
        ("2.1", "clustering.assign", "assign_articles_to_stories"),
        ("2.2", "clustering.discover", "discover_new_clusters"),
        ("2.3", "clustering.merge", "merge_similar_stories"),
        ("2.4", "clustering.label", "label_stories"),
        ("2.5", "pipeline.process", "run_clustering"),
    ]
    for check_id, module, func_name in modules:
        try:
            mod = __import__(module, fromlist=[func_name])
            getattr(mod, func_name)
            _record(check_id, "PASS", f"from {module} import {func_name}")
        except Exception as exc:
            _record(check_id, "FAIL", f"Import failed: {exc}", critical=True)


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 3: ASSIGNMENT MODULE
# ═════════════════════════════════════════════════════════════════════════════


def section_3_assignment() -> dict:
    console.rule("[bold]Section 3: Assignment Module[/bold]")

    from clustering.assign import assign_articles_to_stories
    from db import queries as db

    # Count unassigned before
    before_count = len(db.get_unassigned_articles())

    # 3.1 — Return shape
    try:
        result = assign_articles_to_stories()
    except Exception as exc:
        _record("3.1", "FAIL", f"assign_articles_to_stories() raised: {exc}", critical=True)
        return {}

    expected_keys = {"assigned", "unassigned", "stories_updated"}
    if isinstance(result, dict) and expected_keys.issubset(result.keys()):
        _record("3.1", "PASS",
                f"assigned={result['assigned']}, unassigned={result['unassigned']}, "
                f"stories_updated={result['stories_updated']}")
    else:
        _record("3.1", "FAIL",
                f"Missing keys or wrong type. Got: {result}", critical=True)
        return result if isinstance(result, dict) else {}

    # 3.2 — assigned + unassigned = before count
    total = result["assigned"] + result["unassigned"]
    if total == before_count:
        _record("3.2", "PASS",
                f"Math checks out: {result['assigned']} + {result['unassigned']} = {before_count}")
    else:
        _record("3.2", "FAIL",
                f"Assignment math doesn't add up: {before_count} != "
                f"{result['assigned']} + {result['unassigned']}")

    # 3.3 — No article assigned to inactive/nonexistent story
    try:
        from db.client import get_client
        client = get_client()
        # Find articles whose story_id points to a non-active or non-existent story
        all_assigned = (
            client.table("articles")
            .select("id, story_id")
            .not_.is_("story_id", "null")
            .execute()
        )
        bad_count = 0
        if all_assigned.data:
            active_stories = db.get_active_stories()
            active_ids = {s["id"] for s in active_stories}
            # Also count inactive stories (they exist but are deactivated)
            all_stories_result = (
                client.table("stories")
                .select("id, active")
                .execute()
            )
            all_story_ids = {s["id"] for s in (all_stories_result.data or [])}
            inactive_ids = all_story_ids - active_ids

            for row in all_assigned.data:
                sid = row["story_id"]
                if sid not in all_story_ids:
                    bad_count += 1  # points to nonexistent story
                elif sid in inactive_ids:
                    bad_count += 1  # points to inactive story

        if bad_count == 0:
            _record("3.3", "PASS", "No articles assigned to invalid stories")
        else:
            _record("3.3", "FAIL",
                    f"{bad_count} articles assigned to invalid/inactive stories")
    except Exception as exc:
        _record("3.3", "FAIL", f"Query error: {exc}")

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 4: CLUSTER DISCOVERY
# ═════════════════════════════════════════════════════════════════════════════


def section_4_discovery() -> dict:
    console.rule("[bold]Section 4: Cluster Discovery[/bold]")

    from clustering.discover import discover_new_clusters
    from db.client import get_client

    # 4.1 — Return shape
    try:
        result = discover_new_clusters()
    except Exception as exc:
        _record("4.1", "FAIL", f"discover_new_clusters() raised: {exc}", critical=True)
        return {}

    expected_keys = {"clusters_found", "articles_clustered", "articles_noise", "new_stories"}
    if isinstance(result, dict) and expected_keys.issubset(result.keys()):
        _record("4.1", "PASS",
                f"clusters={result['clusters_found']}, "
                f"clustered={result['articles_clustered']}, "
                f"noise={result['articles_noise']}")
    else:
        _record("4.1", "FAIL",
                f"Missing keys or wrong type. Got keys: {list(result.keys()) if isinstance(result, dict) else type(result)}",
                critical=True)
        return result if isinstance(result, dict) else {}

    new_stories = result.get("new_stories", [])

    if not new_stories:
        _record("4.2", "INFO", "No new stories created — skipping centroid/count checks")
        _record("4.3", "INFO", "No new stories created")
        _record("4.4", "INFO", "No new stories created")
    else:
        client = get_client()

        # 4.2 — New stories have valid centroids
        all_centroids_ok = True
        for story in new_stories:
            sid = story["story_id"]
            row = (
                client.table("stories")
                .select("centroid")
                .eq("id", sid)
                .maybe_single()
                .execute()
            )
            centroid = (row.data or {}).get("centroid")
            if isinstance(centroid, str):
                centroid = json.loads(centroid)
            if centroid and len(centroid) == 384:
                continue
            else:
                _record("4.2", "FAIL",
                        f"Story #{sid} has invalid centroid "
                        f"(len={len(centroid) if centroid else 'NULL'})")
                all_centroids_ok = False
        if all_centroids_ok:
            _record("4.2", "PASS",
                    f"All {len(new_stories)} new stories have valid 384-dim centroids")

        # 4.3 — Article counts match
        all_counts_ok = True
        for story in new_stories:
            sid = story["story_id"]
            actual_result = (
                client.table("articles")
                .select("id", count="exact")
                .eq("story_id", sid)
                .execute()
            )
            actual = actual_result.count or 0
            story_row = (
                client.table("stories")
                .select("article_count")
                .eq("id", sid)
                .maybe_single()
                .execute()
            )
            stored = (story_row.data or {}).get("article_count", 0)
            if actual == stored:
                continue
            else:
                _record("4.3", "FAIL",
                        f"Story #{sid}: article_count={stored} but actual articles={actual}")
                all_counts_ok = False
        if all_counts_ok:
            _record("4.3", "PASS",
                    f"All {len(new_stories)} stories have correct article counts")

        # 4.4 — Reasonable metadata
        all_meta_ok = True
        for story in new_stories:
            sid = story["story_id"]
            row = (
                client.table("stories")
                .select("*")
                .eq("id", sid)
                .maybe_single()
                .execute()
            )
            s = row.data or {}
            problems = []
            if not s.get("first_seen"):
                problems.append("first_seen is NULL")
            if not s.get("last_updated"):
                problems.append("last_updated is NULL")
            if s.get("first_seen") and s.get("last_updated"):
                if s["last_updated"] < s["first_seen"]:
                    problems.append("last_updated < first_seen")
            if (s.get("source_count") or 0) < 1:
                problems.append(f"source_count={s.get('source_count')}")
            if (s.get("article_count") or 0) < 3:
                problems.append(f"article_count={s.get('article_count')} (min=3)")
            if not (s.get("topic") or "").strip():
                _record("4.4", "WARN", f"Story #{sid}: topic is empty/NULL")

            if problems:
                _record("4.4", "FAIL", f"Story #{sid}: {'; '.join(problems)}")
                all_meta_ok = False

        if all_meta_ok:
            _record("4.4", "PASS",
                    f"All {len(new_stories)} stories have reasonable metadata")

    # 4.5 — No article belongs to multiple stories
    # (With a single story_id column this is structural, but validate anyway)
    try:
        client = get_client()
        dup_result = (
            client.table("articles")
            .select("id, story_id")
            .not_.is_("story_id", "null")
            .execute()
        )
        # Since story_id is a single column, duplicates mean duplicate rows
        seen_ids: set[int] = set()
        dups = 0
        for row in (dup_result.data or []):
            aid = row["id"]
            if aid in seen_ids:
                dups += 1
            seen_ids.add(aid)
        if dups == 0:
            _record("4.5", "PASS", "No article belongs to multiple stories")
        else:
            _record("4.5", "FAIL", f"{dups} articles have duplicate rows")
    except Exception as exc:
        _record("4.5", "FAIL", f"Query error: {exc}")

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 5: TOPIC LABELING
# ═════════════════════════════════════════════════════════════════════════════


def section_5_labeling() -> None:
    console.rule("[bold]Section 5: Topic Labeling[/bold]")

    from clustering.label import label_stories
    from db.client import get_client

    client = get_client()

    # Find a story to label — pick the one with most articles
    stories_result = (
        client.table("stories")
        .select("id, topic, article_count")
        .eq("active", True)
        .order("article_count", desc=True)
        .limit(1)
        .execute()
    )
    stories = stories_result.data or []
    if not stories:
        _record("5.1", "INFO", "No active stories — skipping labeling checks")
        return

    story_id = stories[0]["id"]

    # 5.1 — label_stories runs without error
    try:
        result = label_stories(story_ids=[story_id])
    except Exception as exc:
        _record("5.1", "FAIL", f"label_stories raised: {exc}", critical=True)
        return

    if "labeled" in result:
        _record("5.1", "PASS",
                f"labeled={result['labeled']}, skipped={result.get('skipped', 0)}, "
                f"errors={result.get('errors', 0)}")
    else:
        _record("5.1", "FAIL", f"Missing 'labeled' key. Got: {list(result.keys())}")
        return

    # 5.2 — Generated label is reasonable
    labels = result.get("labels", [])
    if not labels:
        _record("5.2", "INFO", "No labels generated (story may have been skipped)")
        _record("5.3", "INFO", "No labels to verify persistence")
        return

    new_topic = labels[0].get("new_topic", "")
    problems = []
    if len(new_topic) < 3 or len(new_topic) > 80:
        problems.append(f"length={len(new_topic)} (expected 3-80)")
    if " - " in new_topic or " | " in new_topic:
        problems.append("contains headline artifacts")
    if '"' in new_topic or "'" in new_topic:
        problems.append("contains quotation marks")

    if problems:
        _record("5.2", "FAIL", f"Label issues: {'; '.join(problems)}. Label: '{new_topic}'")
    else:
        if len(new_topic) > 50:
            _record("5.2", "WARN", f"Label might be verbose ({len(new_topic)} chars): '{new_topic}'")
        else:
            _record("5.2", "PASS", f"Label: '{new_topic}'")

    # 5.3 — Label persisted to DB
    row = (
        client.table("stories")
        .select("topic")
        .eq("id", story_id)
        .maybe_single()
        .execute()
    )
    db_topic = (row.data or {}).get("topic", "")
    if db_topic == new_topic:
        _record("5.3", "PASS", "Label saved to DB correctly")
    else:
        _record("5.3", "FAIL",
                f"Label not saved to DB. Expected '{new_topic}', got '{db_topic}'")


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 6: CLUSTER MERGING
# ═════════════════════════════════════════════════════════════════════════════


def section_6_merging() -> dict:
    console.rule("[bold]Section 6: Cluster Merging[/bold]")

    from clustering.merge import merge_similar_stories
    from db.client import get_client

    # 6.1 — Return shape
    try:
        result = merge_similar_stories()
    except Exception as exc:
        _record("6.1", "FAIL", f"merge_similar_stories() raised: {exc}", critical=True)
        return {}

    expected_keys = {"pairs_checked", "merges_performed", "stories_absorbed"}
    if isinstance(result, dict) and expected_keys.issubset(result.keys()):
        _record("6.1", "PASS",
                f"pairs_checked={result['pairs_checked']}, "
                f"merges={result['merges_performed']}, "
                f"absorbed={len(result['stories_absorbed'])}")
    else:
        _record("6.1", "FAIL",
                f"Missing keys. Got: {list(result.keys()) if isinstance(result, dict) else type(result)}",
                critical=True)
        return result if isinstance(result, dict) else {}

    # 6.2 — Absorbed stories are deactivated
    absorbed = result.get("stories_absorbed", [])
    if not absorbed:
        _record("6.2", "INFO", "No merges occurred — nothing to check")
    else:
        client = get_client()
        all_deactivated = True
        for sid in absorbed:
            row = (
                client.table("stories")
                .select("active")
                .eq("id", sid)
                .maybe_single()
                .execute()
            )
            is_active = (row.data or {}).get("active", True)
            if is_active:
                _record("6.2", "FAIL", f"Absorbed story #{sid} is still active")
                all_deactivated = False
        if all_deactivated:
            _record("6.2", "PASS",
                    f"All {len(absorbed)} absorbed stories are deactivated")

    # 6.3 — No orphaned articles after merge
    try:
        client = get_client()
        # Get all story ids that exist
        all_stories_result = (
            client.table("stories")
            .select("id")
            .execute()
        )
        all_story_ids = {s["id"] for s in (all_stories_result.data or [])}

        # Get all articles with a story_id
        assigned_result = (
            client.table("articles")
            .select("id, story_id")
            .not_.is_("story_id", "null")
            .execute()
        )
        orphaned = 0
        for row in (assigned_result.data or []):
            if row["story_id"] not in all_story_ids:
                orphaned += 1

        if orphaned == 0:
            _record("6.3", "PASS", "No orphaned articles after merge")
        else:
            _record("6.3", "FAIL",
                    f"{orphaned} articles reference non-existent stories")
    except Exception as exc:
        _record("6.3", "FAIL", f"Query error: {exc}")

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 7: ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════


def section_7_orchestrator() -> None:
    console.rule("[bold]Section 7: Orchestrator[/bold]")

    # 7.1 — run_clustering executes without error
    try:
        from pipeline.process import run_clustering

        result = run_clustering()
        _record("7.1", "PASS",
                f"run_clustering completed. active_stories={result.get('active_stories', '?')}")
    except Exception as exc:
        _record("7.1", "FAIL", f"run_clustering() raised: {exc}", critical=True)

    # 7.2 — Pipeline is wired into main.py
    try:
        main_path = os.path.join(os.path.dirname(__file__), "..", "pipeline", "main.py")
        with open(main_path, encoding="utf-8") as f:
            source = f.read()

        import_line = "from pipeline.process import run_clustering"
        if import_line in source:
            # Check it's not commented out
            lines = source.split("\n")
            found_active = False
            for line in lines:
                stripped = line.strip()
                if import_line in stripped and not stripped.startswith("#"):
                    found_active = True
                    break
            if found_active:
                _record("7.2", "PASS", "Clustering is wired into pipeline/main.py")
            else:
                _record("7.2", "WARN", "Import exists but is commented out")
        else:
            _record("7.2", "FAIL",
                    "pipeline/main.py doesn't import run_clustering")
    except Exception as exc:
        _record("7.2", "FAIL", f"Could not read pipeline/main.py: {exc}")


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 8: DATA QUALITY POST-CLUSTERING
# ═════════════════════════════════════════════════════════════════════════════


def section_8_data_quality() -> None:
    console.rule("[bold]Section 8: Data Quality Post-Clustering[/bold]")

    import numpy as np

    from db.client import get_client

    client = get_client()

    # 8.1 — Story count is reasonable
    try:
        result = (
            client.table("stories")
            .select("id", count="exact")
            .eq("active", True)
            .execute()
        )
        count = result.count or 0
        if 5 <= count <= 100:
            _record("8.1", "PASS", f"Active stories: {count}")
        elif count < 5:
            _record("8.1", "WARN",
                    f"Very few stories ({count}) — clustering may be too strict")
        else:
            _record("8.1", "WARN",
                    f"Too many stories ({count}) — clustering may be too loose")
    except Exception as exc:
        _record("8.1", "FAIL", f"Query error: {exc}")

    # 8.2 — Assignment coverage
    try:
        total_result = (
            client.table("articles")
            .select("id", count="exact")
            .not_.is_("embedding", "null")
            .execute()
        )
        total_articles = total_result.count or 0

        assigned_result = (
            client.table("articles")
            .select("id", count="exact")
            .not_.is_("story_id", "null")
            .execute()
        )
        assigned = assigned_result.count or 0

        pct = (assigned / total_articles * 100) if total_articles > 0 else 0
        msg = f"{assigned}/{total_articles} articles assigned ({pct:.1f}%)"
        if pct > 95:
            _record("8.2", "WARN", f"Suspiciously high assignment rate. {msg}")
        elif pct > 30:
            _record("8.2", "PASS", msg)
        else:
            _record("8.2", "WARN", f"Low assignment rate — check similarity threshold. {msg}")
    except Exception as exc:
        _record("8.2", "FAIL", f"Query error: {exc}")

    # 8.3 — Stories have diverse sources
    try:
        top_result = (
            client.table("stories")
            .select("id, topic, source_count, article_count")
            .eq("active", True)
            .order("article_count", desc=True)
            .limit(10)
            .execute()
        )
        top_stories = top_result.data or []

        table = Table(title="Top 10 Stories by Article Count", show_lines=False)
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Topic", max_width=45)
        table.add_column("Articles", justify="right")
        table.add_column("Sources", justify="right")

        single_source_warnings = []
        for s in top_stories:
            table.add_row(
                str(s["id"]),
                (s.get("topic") or "—")[:45],
                str(s.get("article_count", 0)),
                str(s.get("source_count", 0)),
            )
            if (s.get("article_count") or 0) >= 5 and (s.get("source_count") or 0) < 2:
                single_source_warnings.append(
                    f"Story '{(s.get('topic') or '?')[:40]}' has "
                    f"{s['article_count']} articles but only "
                    f"{s.get('source_count', 0)} source(s)")

        console.print(table)

        if single_source_warnings:
            for w in single_source_warnings:
                _record("8.3", "WARN", w)
        else:
            _record("8.3", "PASS",
                    "All top stories with 5+ articles have diverse sources")
    except Exception as exc:
        _record("8.3", "FAIL", f"Query error: {exc}")

    # 8.4 — No centroid drift
    try:
        top5_result = (
            client.table("stories")
            .select("id, topic, centroid")
            .eq("active", True)
            .not_.is_("centroid", "null")
            .order("article_count", desc=True)
            .limit(5)
            .execute()
        )
        top5 = top5_result.data or []
        all_fresh = True

        for s in top5:
            sid = s["id"]
            stored_centroid = s.get("centroid")
            if isinstance(stored_centroid, str):
                stored_centroid = json.loads(stored_centroid)
            if not stored_centroid:
                continue

            # Fetch article embeddings
            articles_result = (
                client.table("articles")
                .select("embedding")
                .eq("story_id", sid)
                .not_.is_("embedding", "null")
                .execute()
            )
            embeddings = []
            for a in (articles_result.data or []):
                emb = a.get("embedding")
                if isinstance(emb, str):
                    emb = json.loads(emb)
                if emb:
                    embeddings.append(emb)

            if not embeddings:
                continue

            # Compute actual centroid
            actual = np.mean(embeddings, axis=0)
            stored = np.array(stored_centroid)

            # Cosine similarity
            dot = np.dot(actual, stored)
            norm_a = np.linalg.norm(actual)
            norm_s = np.linalg.norm(stored)
            similarity = dot / (norm_a * norm_s) if (norm_a * norm_s) > 0 else 0

            topic = (s.get("topic") or f"#{sid}")[:30]
            if similarity > 0.95:
                pass  # OK
            elif similarity > 0.85:
                _record("8.4", "WARN",
                        f"Story '{topic}' centroid slightly stale (sim={similarity:.3f})")
                all_fresh = False
            else:
                _record("8.4", "FAIL",
                        f"Story '{topic}' centroid significantly outdated (sim={similarity:.3f})")
                all_fresh = False

        if all_fresh:
            _record("8.4", "PASS", "Top story centroids are fresh (sim > 0.95)")
    except Exception as exc:
        _record("8.4", "FAIL", f"Query error: {exc}")

    # 8.5 — Bias coverage per story
    try:
        top5_result = (
            client.table("stories")
            .select("id, topic")
            .eq("active", True)
            .order("article_count", desc=True)
            .limit(5)
            .execute()
        )
        top5 = top5_result.data or []

        for s in top5:
            sid = s["id"]
            topic = (s.get("topic") or f"#{sid}")[:35]
            bias_result = (
                client.table("articles")
                .select("source_bias")
                .eq("story_id", sid)
                .execute()
            )
            bias_counts: dict[str, int] = {}
            for row in (bias_result.data or []):
                bias = row.get("source_bias") or "unknown"
                bias_counts[bias] = bias_counts.get(bias, 0) + 1

            dist_str = ", ".join(f"{k}={v}" for k, v in sorted(bias_counts.items()))
            _record("8.5", "INFO", f"Story '{topic}': {dist_str}")

            # Check for missing major perspectives
            major = {"left", "center", "right", "left-center", "right-center"}
            present = set(bias_counts.keys())
            missing = major - present
            if missing:
                missing_str = ", ".join(sorted(missing))
                _record("8.5", "WARN",
                        f"Story '{topic}' missing perspectives: {missing_str}")
    except Exception as exc:
        _record("8.5", "FAIL", f"Query error: {exc}")


# ═════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═════════════════════════════════════════════════════════════════════════════


def print_summary() -> None:
    console.print()
    console.rule("[bold]CLUSTERING VALIDATION SUMMARY[/bold]", style="bold")

    pass_count = sum(1 for r in _results if r["status"] == "PASS")
    warn_count = sum(1 for r in _results if r["status"] == "WARN")
    fail_count = sum(1 for r in _results if r["status"] == "FAIL")

    console.print(f"  [green]PASS:  {pass_count}[/green]")
    console.print(f"  [yellow]WARN:  {warn_count}[/yellow]")
    console.print(f"  [red]FAIL:  {fail_count}[/red]")

    console.rule(style="bold")

    failures = [r for r in _results if r["status"] == "FAIL"]
    warnings = [r for r in _results if r["status"] == "WARN"]

    if failures:
        console.print("\n[bold red]CRITICAL FAILURES:[/bold red]")
        for f in failures:
            console.print(f"  - {f['id']}: {f['message']}")

    if warnings:
        console.print("\n[bold yellow]WARNINGS:[/bold yellow]")
        for w in warnings:
            console.print(f"  - {w['id']}: {w['message']}")

    console.print()
    if fail_count == 0:
        console.print("[bold green]✅ All checks passed. Safe to proceed to scoring.[/bold green]")
    else:
        console.print("[bold red]❌ Fix failures before proceeding to scoring.[/bold red]")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════


def main() -> None:
    console.rule("[bold cyan]ClearSignal — Clustering Validation[/bold cyan]")
    console.print()

    section_1_preconditions()
    section_2_imports()
    section_3_assignment()
    section_4_discovery()
    section_5_labeling()
    section_6_merging()
    section_7_orchestrator()
    section_8_data_quality()
    print_summary()


if __name__ == "__main__":
    import logging

    from rich.logging import RichHandler

    logging.basicConfig(
        level="WARNING",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )
    main()
