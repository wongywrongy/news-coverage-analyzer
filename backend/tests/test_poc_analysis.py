"""Pre-execution validator for POC analysis generation.

Checks DB schema, story selection, prompt quality, cost math, and API key
WITHOUT making a single Anthropic API call. Spends $0.00.

Usage:
    python -m tests.test_poc_analysis

If 0 FAIL -> safe to run: python -m pipeline.poc_analysis
"""

from __future__ import annotations

import logging
import os
import re

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ── Counters ────────────────────────────────────────────────────────────

counts = {"pass": 0, "warn": 0, "fail": 0, "skip": 0, "info": 0}
failures: list[str] = []


def PASS(msg: str) -> None:
    counts["pass"] += 1
    console.print(f"  [green]PASS[/green]  {msg}")


def WARN(msg: str) -> None:
    counts["warn"] += 1
    console.print(f"  [yellow]WARN[/yellow]  {msg}")


def FAIL(msg: str) -> None:
    counts["fail"] += 1
    failures.append(msg)
    console.print(f"  [red]FAIL[/red]  {msg}")


def SKIP(msg: str) -> None:
    counts["skip"] += 1
    console.print(f"  [dim]SKIP[/dim]  {msg}")


def INFO(msg: str) -> None:
    counts["info"] += 1
    console.print(f"  [blue]INFO[/blue]  {msg}")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 1: FIX VERIFICATION
# ═════════════════════════════════════════════════════════════════════════


def test_fixes() -> list[dict]:
    """Verify all pre-flight fixes. Returns active stories for later use."""
    console.rule("[bold]Section 1: Fix Verification[/bold]")

    from db import queries as db
    from db.client import get_client

    stories = db.get_active_stories()
    if not stories:
        FAIL("No active stories in DB")
        return []

    first_id = stories[0]["id"]

    # 1.1 — article_count_at_gen column exists
    # Save any existing analysis for this story
    existing = db.get_analysis(first_id)
    test_data = {
        "story_id": first_id,
        "headline": "__VALIDATOR_TEST__",
        "dateline": "TEST",
        "lede": "Test.",
        "context": "Test.",
        "contrasts": [],
        "facts": [],
        "bottom_line": "Test.",
        "coverage_note": "Test.",
        "article_count_at_gen": 0,
    }

    try:
        db.upsert_analysis(test_data)
        saved = db.get_analysis(first_id)
        if saved and saved.get("headline") == "__VALIDATOR_TEST__":
            PASS("article_count_at_gen column exists and upsert works")
        else:
            FAIL("upsert_analysis didn't persist — check column exists")
    except Exception as e:
        if "article_count_at_gen" in str(e):
            FAIL(
                "article_count_at_gen column missing. Run:\n"
                "      ALTER TABLE analyses ADD COLUMN IF NOT EXISTS "
                "article_count_at_gen INT DEFAULT 0;\n"
                "      NOTIFY pgrst, 'reload schema';"
            )
        else:
            FAIL(f"upsert_analysis error: {e}")
    finally:
        try:
            if existing:
                db.upsert_analysis(existing)
            else:
                client = get_client()
                client.table("analyses").delete().eq(
                    "story_id", first_id
                ).execute()
        except Exception:
            pass

    # 1.2 — Staleness checker filters small stories
    from analysis.staleness import get_stories_needing_analysis

    ids = get_stories_needing_analysis(max_results=100)
    small_leaked = False
    for sid in ids:
        actual = len(db.get_articles_for_story(sid))
        if actual < 3:
            FAIL(
                f"Story #{sid} has {actual} actual articles but passed "
                "staleness filter — staleness checker not filtering"
            )
            small_leaked = True
    if not small_leaked:
        PASS("Staleness checker correctly excludes stories with < 3 actual articles")

    # 1.3 — Generator has article count guard
    gen_path = os.path.join(os.path.dirname(__file__), "..", "analysis", "generator.py")
    try:
        with open(gen_path, encoding="utf-8") as f:
            gen_src = f.read()
        if re.search(r"(MIN_ARTICLES|< 3|<= 2|< min)", gen_src, re.IGNORECASE) and (
            "skip" in gen_src.lower() or "continue" in gen_src.lower()
        ):
            PASS("Generator has article count guard")
        else:
            FAIL("Generator missing article count guard")
    except Exception as e:
        FAIL(f"Could not read generator.py: {e}")

    return stories


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 2: POC SCRIPT VALIDATION
# ═════════════════════════════════════════════════════════════════════════


def test_poc_script(
    stories: list[dict],
) -> tuple[list[tuple[dict, str, str]], dict[int, int]]:
    """Validate POC script selection logic. Returns selected + actual_counts."""
    console.rule("[bold]Section 2: POC Script Validation[/bold]")

    from db import queries as db

    # 2.1 — imports
    try:
        from pipeline.poc_analysis import (  # noqa: F401
            _gap,
            _is_eligible,
            _sentiment_divergence,
            main,
            select_stories,
        )
        PASS("poc_analysis.py imports successfully")
    except Exception as e:
        FAIL(f"poc_analysis.py import failed: {e}")
        return [], {}

    from pipeline.poc_analysis import (
        _gap,
        _sentiment_divergence,
        select_stories,
    )

    # Get actual article counts
    actual_counts: dict[int, int] = {}
    for s in stories:
        actual_counts[s["id"]] = len(db.get_articles_for_story(s["id"]))

    # 2.2 — selects exactly 10
    selected = select_stories(stories, actual_counts)
    if len(selected) == 10:
        PASS("Selected exactly 10 stories")
    else:
        FAIL(f"{len(selected)} stories selected (expected 10)")
        if not selected:
            return [], actual_counts

    # 2.3 — all have >= 3 actual articles
    all_above_min = True
    for story, cat, _ in selected:
        actual = actual_counts.get(story["id"], 0)
        if actual < 3:
            FAIL(f"Selected story #{story['id']} has only {actual} articles")
            all_above_min = False
    if all_above_min:
        PASS("All selected stories have >= 3 actual articles")

    # 2.4 — all scored
    all_scored = True
    for story, cat, _ in selected:
        impact = story.get("impact_score") or 0
        attention = story.get("attention_score") or 0
        if impact <= 0 or attention <= 0:
            FAIL(
                f"Story #{story['id']} not scored: "
                f"impact={impact} attention={attention}"
            )
            all_scored = False
    if all_scored:
        PASS("All selected stories have been scored")

    # 2.5 — covers all 5 categories
    cats = {cat for _, cat, _ in selected}
    has_buried = any(_gap(s) >= 30 for s, _, _ in selected)
    has_overcovered = any(_gap(s) <= -30 for s, _, _ in selected)
    has_high_impact = any(
        (s.get("impact_score") or 0) >= 60 and actual_counts.get(s["id"], 0) >= 10
        for s, _, _ in selected
    )
    has_partisan = any(_sentiment_divergence(s) >= 0.3 for s, _, _ in selected)
    has_balanced = any(-30 < _gap(s) < 30 for s, _, _ in selected)

    coverage_checks = {
        "Buried (gap >= 30)": has_buried,
        "Overcovered (gap <= -30)": has_overcovered,
        "High-impact (impact >= 60, articles >= 10)": has_high_impact,
        "Partisan (sentiment divergence >= 0.3)": has_partisan,
        "Balanced (-30 < gap < 30)": has_balanced,
    }

    missing_cats = [k for k, v in coverage_checks.items() if not v]
    if not missing_cats:
        PASS("All 5 test categories represented")
    else:
        for mc in missing_cats:
            WARN(f"Missing category: {mc}")

    cat_counts = {}
    for _, cat, _ in selected:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat_name, cnt in sorted(cat_counts.items()):
        INFO(f"  {cat_name}: {cnt} stories")

    # 2.6 — no garbage labels
    all_clean = True
    for story, _, _ in selected:
        topic = story.get("topic") or ""
        if len(topic) > 80 or "\n" in topic or "#" in topic:
            FAIL(f"Story #{story['id']} has bad label: '{topic[:50]}...'")
            all_clean = False
    if all_clean:
        PASS("No garbage labels in selected stories")

    return selected, actual_counts


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 3: PROMPT QUALITY
# ═════════════════════════════════════════════════════════════════════════


def test_prompts(
    selected: list[tuple[dict, str, str]],
    actual_counts: dict[int, int],
) -> list[dict]:
    """Build and validate prompts for all selected stories. Returns prompt stats."""
    console.rule("[bold]Section 3: Prompt Quality[/bold]")

    from analysis.generator import _build_sonnet_prompt
    from config.sources import SOURCE_BIAS
    from db import queries as db

    LEFT_LABELS = {"far-left", "left", "left-center"}
    RIGHT_LABELS = {"right-center", "right", "far-right"}

    prompt_stats: list[dict] = []

    for story, category, _ in selected:
        sid = story["id"]
        topic = (story.get("topic") or "?")[:35]
        articles = db.get_articles_for_story(sid)

        stat = {
            "story_id": sid,
            "topic": topic,
            "left": 0,
            "center": 0,
            "right": 0,
            "tokens": 0,
            "ok": True,
        }

        # 3.X.1 — builds without error
        try:
            system, user_msg = _build_sonnet_prompt(story, articles)
            if not system or not user_msg:
                FAIL(f"Story #{sid}: prompt returned empty strings")
                stat["ok"] = False
                prompt_stats.append(stat)
                continue
            PASS(f"Story #{sid} ({topic}): prompt built")
        except Exception as e:
            FAIL(f"Story #{sid} ({topic}): prompt build failed: {e}")
            stat["ok"] = False
            prompt_stats.append(stat)
            continue

        # 3.X.2 — headlines distributed across bias groups
        # Parse headline counts per macro-group from the user_msg
        left_count = 0
        center_count = 0
        right_count = 0

        # Split by group headers and count headlines (lines with "- [")
        group_headers = [
            "LEFT / FAR-LEFT",
            "LEFT-CENTER",
            "CENTER",
            "RIGHT-CENTER",
            "RIGHT / FAR-RIGHT",
        ]

        for i_h, header in enumerate(group_headers):
            idx = user_msg.find(header)
            if idx == -1:
                continue
            # Find next header or end
            next_idx = len(user_msg)
            for other in group_headers:
                if other == header:
                    continue
                oi = user_msg.find(other, idx + len(header))
                if oi != -1 and oi < next_idx:
                    next_idx = oi
            section = user_msg[idx:next_idx]
            headline_count = section.count("- [")

            if header in ("LEFT / FAR-LEFT", "LEFT-CENTER"):
                left_count += headline_count
            elif header == "CENTER":
                center_count += headline_count
            else:
                right_count += headline_count

        stat["left"] = left_count
        stat["center"] = center_count
        stat["right"] = right_count

        groups_with_headlines = sum(
            1 for c in (left_count, center_count, right_count) if c > 0
        )

        total_headlines = left_count + center_count + right_count
        if groups_with_headlines >= 2:
            PASS(
                f"  Headlines distributed: L={left_count} C={center_count} "
                f"R={right_count}"
            )
        elif groups_with_headlines == 1:
            which = (
                "LEFT" if left_count else "CENTER" if center_count else "RIGHT"
            )
            WARN(f"  One-sided coverage (all in {which}) — Sonnet can't contrast")
        else:
            WARN("  No headlines found in prompt")

        # 3.X.3 — bias placement correct (spot-check one from each side)
        bias_ok = True
        for header, expected_labels in [
            ("LEFT / FAR-LEFT", LEFT_LABELS),
            ("RIGHT / FAR-RIGHT", RIGHT_LABELS),
        ]:
            idx = user_msg.find(header)
            if idx == -1:
                continue
            # Find a headline "- [domain]"
            section_start = idx
            next_idx = len(user_msg)
            for other in group_headers:
                if other == header:
                    continue
                oi = user_msg.find(other, idx + len(header))
                if oi != -1 and oi < next_idx:
                    next_idx = oi
            section = user_msg[section_start:next_idx]
            match = re.search(r"-\s*\[([^\]]+)\]", section)
            if match:
                domain = match.group(1)
                bias_info = SOURCE_BIAS.get(domain)
                if bias_info:
                    actual_label = bias_info["label"]
                    if actual_label not in expected_labels:
                        FAIL(
                            f"  {domain} (bias: {actual_label}) placed in "
                            f"{header} — lookup broken"
                        )
                        bias_ok = False

        if bias_ok:
            PASS("  Bias placement correct (source_domain lookup)")

        # 3.X.4 — scores in prompt
        impact_val = str(int(story.get("impact_score") or 0))
        attention_val = str(int(story.get("attention_score") or 0))
        if impact_val in user_msg and attention_val in user_msg:
            PASS(f"  Scores included (impact={impact_val}, attention={attention_val})")
        else:
            FAIL("  Scores missing from prompt")

        # 3.X.5 — token estimate
        input_tokens = (len(system) + len(user_msg)) // 4
        stat["tokens"] = input_tokens
        if input_tokens > 4000:
            WARN(f"  ~{input_tokens} input tokens — large prompt")
        elif input_tokens < 200:
            WARN(f"  ~{input_tokens} input tokens — very small prompt")
        else:
            PASS(f"  ~{input_tokens} input tokens")

        prompt_stats.append(stat)

    # Summary table
    console.print()
    table = Table(title="Prompt Summary", border_style="dim")
    table.add_column("Story", justify="right")
    table.add_column("Topic", max_width=35)
    table.add_column("L", justify="right")
    table.add_column("C", justify="right")
    table.add_column("R", justify="right")
    table.add_column("Tokens", justify="right")

    for s in prompt_stats:
        table.add_row(
            f"#{s['story_id']}",
            s["topic"],
            str(s["left"]),
            str(s["center"]),
            str(s["right"]),
            f"~{s['tokens']}",
        )
    console.print(table)

    return prompt_stats


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 4: COST VERIFICATION
# ═════════════════════════════════════════════════════════════════════════


def test_cost(
    selected: list[tuple[dict, str, str]],
    prompt_stats: list[dict],
) -> float:
    """Calculate per-story and total cost. Returns total cost."""
    console.rule("[bold]Section 4: Cost Verification[/bold]")

    from analysis.generator import _build_sonnet_prompt
    from db import queries as db

    total_cost = 0.0
    OUTPUT_TOKENS = 800

    for story, cat, _ in selected:
        sid = story["id"]
        articles = db.get_articles_for_story(sid)
        system, user_msg = _build_sonnet_prompt(story, articles)
        input_tokens = (len(system) + len(user_msg)) // 4

        # Sonnet pricing: $3/M input, $15/M output
        input_cost = input_tokens * 3 / 1_000_000
        output_cost = OUTPUT_TOKENS * 15 / 1_000_000
        story_cost = input_cost + output_cost
        total_cost += story_cost

        topic = (story.get("topic") or "?")[:35]
        INFO(
            f"  #{sid} ({topic}): "
            f"{input_tokens} in + {OUTPUT_TOKENS} out = ${story_cost:.4f}"
        )

    console.print()

    # 4.2 — total cost
    if total_cost < 0.25:
        PASS(f"Total estimated cost: ${total_cost:.3f}")
    elif total_cost < 0.50:
        WARN(f"Total estimated cost: ${total_cost:.3f} — higher than expected")
    else:
        FAIL(f"Total estimated cost: ${total_cost:.3f} — prompts may be bloated")

    # 4.3 — no duplicates
    selected_ids = [s["id"] for s, _, _ in selected]
    if len(set(selected_ids)) == len(selected_ids):
        PASS("No duplicate story IDs in selection")
    else:
        FAIL("Duplicate story IDs in selection")

    return total_cost


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 5: API KEY VALIDATION
# ═════════════════════════════════════════════════════════════════════════


def test_api_key() -> None:
    console.rule("[bold]Section 5: API Key Validation[/bold]")

    from config.settings import settings

    # 5.1 — key is set
    key = settings.anthropic_api_key
    if key and len(key) > 10 and key not in ("your-anthropic-key-here", "sk-ant-xxx"):
        PASS("Anthropic API key is set")
    else:
        FAIL("Anthropic API key not set or is placeholder")
        return

    # 5.2 — key format
    if key.startswith("sk-ant-"):
        PASS("API key format looks valid (sk-ant- prefix)")
    else:
        WARN("Unusual key format (doesn't start with sk-ant-) — may still work")

    # 5.3 — client initializes
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        PASS("Anthropic client initialized successfully")
    except Exception as e:
        FAIL(f"Client init failed: {e}")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 6: RESPONSE HANDLING
# ═════════════════════════════════════════════════════════════════════════


def test_response_handling(selected: list[tuple[dict, str, str]]) -> None:
    console.rule("[bold]Section 6: Response Handling[/bold]")

    from db import queries as db
    from db.client import get_client

    if not selected:
        SKIP("No selected stories — can't test response handling")
        return

    story = selected[0][0]
    sid = story["id"]

    # Save existing for restore
    existing = db.get_analysis(sid)

    mock_analysis = {
        "story_id": sid,
        "headline": "Test Headline for Validator",
        "dateline": "WASHINGTON (ClearSignal)",
        "lede": "This is a test lede.",
        "context": "This is test context.",
        "contrasts": [
            {
                "theme": "test",
                "sourceA": "CNN",
                "biasA": "left-center",
                "claimA": "claim A",
                "sourceB": "Fox News",
                "biasB": "right-center",
                "claimB": "claim B",
            }
        ],
        "facts": [
            {
                "claim": "test claim",
                "reality": "test reality",
                "verdict": "confirmed",
            }
        ],
        "bottom_line": "Test bottom line.",
        "coverage_note": "Test coverage note.",
        "article_count_at_gen": 5,
    }

    try:
        db.upsert_analysis(mock_analysis)
        saved = db.get_analysis(sid)

        if saved is None:
            FAIL("Could not retrieve stored analysis")
            return

        if saved.get("headline") == "Test Headline for Validator":
            PASS("Analysis stored and retrieved correctly")
        else:
            FAIL(f"Headline mismatch: {saved.get('headline')}")

        # 6.2 — JSONB round-trip
        contrasts = saved.get("contrasts")
        facts = saved.get("facts")

        if isinstance(contrasts, list):
            PASS("contrasts round-trips as list (JSONB working)")
        elif isinstance(contrasts, str):
            FAIL("contrasts came back as string — JSONB column may still be TEXT")
        else:
            WARN(f"contrasts type: {type(contrasts)}")

        if isinstance(facts, list):
            PASS("facts round-trips as list (JSONB working)")
        elif isinstance(facts, str):
            FAIL("facts came back as string — JSONB column may still be TEXT")
        else:
            WARN(f"facts type: {type(facts)}")

        if isinstance(contrasts, list) and len(contrasts) > 0:
            if contrasts[0].get("theme") == "test":
                PASS("Nested JSONB data preserved (contrasts[0].theme == 'test')")
            else:
                FAIL(f"JSONB data corrupted: {contrasts[0]}")

    except Exception as e:
        FAIL(f"Response handling error: {e}")
    finally:
        # Restore original state
        try:
            if existing:
                db.upsert_analysis(existing)
            else:
                client = get_client()
                client.table("analyses").delete().eq("story_id", sid).execute()
            PASS("Cleanup successful")
        except Exception:
            WARN("Cleanup may have failed — check analyses table")


# ═════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s | %(message)s")

    console.print()
    console.rule("[bold blue]POC Analysis Pre-Execution Validator[/bold blue]")
    console.print()

    # Section 1
    stories = test_fixes()

    # Section 2
    if stories:
        selected, actual_counts = test_poc_script(stories)
    else:
        selected, actual_counts = [], {}

    # Section 3
    if selected:
        prompt_stats = test_prompts(selected, actual_counts)
    else:
        prompt_stats = []

    # Section 4
    if selected:
        total_cost = test_cost(selected, prompt_stats)
    else:
        total_cost = 0.0

    # Section 5
    test_api_key()

    # Section 6
    test_response_handling(selected)

    # ── Summary ─────────────────────────────────────────────────────
    console.print()
    console.rule("[bold]POC Analysis Pre-Execution Summary[/bold]")

    summary = Text()
    summary.append(f"  PASS:  {counts['pass']}\n", style="bold green")
    summary.append(f"  WARN:  {counts['warn']}\n", style="bold yellow")
    summary.append(f"  FAIL:  {counts['fail']}\n", style="bold red")
    console.print(Panel(summary, border_style="blue"))

    console.print(f"  STORIES SELECTED:  {len(selected)}")
    console.print(f"  ESTIMATED COST:    ${total_cost:.3f}")
    console.print()

    # Category coverage
    if selected:

        cat_counts: dict[str, int] = {}
        for _, cat, _ in selected:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        console.print("  CATEGORY COVERAGE:")
        for cat_name, cnt in sorted(cat_counts.items()):
            console.print(f"    {cat_name:15s}  {cnt} stories")
        console.print()

    # Bias distribution
    if prompt_stats:
        full_spectrum = sum(
            1 for s in prompt_stats if s["left"] > 0 and s["center"] > 0 and s["right"] > 0
        )
        two_groups = sum(
            1 for s in prompt_stats
            if sum(1 for c in (s["left"], s["center"], s["right"]) if c > 0) == 2
        )
        one_group = sum(
            1 for s in prompt_stats
            if sum(1 for c in (s["left"], s["center"], s["right"]) if c > 0) <= 1
        )
        console.print("  BIAS DISTRIBUTION IN PROMPTS:")
        console.print(f"    Left+Center+Right:  {full_spectrum}/10")
        console.print(f"    Only 2 groups:      {two_groups}/10")
        console.print(f"    Only 1 group:       {one_group}/10")
        console.print()

    # Verdict
    if counts["fail"] == 0:
        console.print(
            "[bold green]All checks passed. Safe to run:[/bold green]\n"
            f"   [bold]python -m pipeline.poc_analysis[/bold]\n"
            f"   Estimated cost: ${total_cost:.3f}"
        )
    else:
        console.print(
            "[bold red]Fix failures before running. "
            "Each failure could waste API budget.[/bold red]"
        )
        console.print()
        for i, f in enumerate(failures, 1):
            console.print(f"  [red]{i}.[/red] {f}")

    console.print()
