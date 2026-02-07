"""Validate the analysis generation module WITHOUT calling the Anthropic API.

Checks imports, function signatures, prompt construction, DB queries,
JSON parsing, and pipeline wiring — all without spending a single API dollar.

Usage:
    python -m tests.test_analysis
"""

import logging
import os
import re

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
logger = logging.getLogger(__name__)

# ── Counters ────────────────────────────────────────────────────────────

counts = {"pass": 0, "warn": 0, "fail": 0, "skip": 0, "info": 0}


def PASS(msg: str) -> None:
    counts["pass"] += 1
    console.print(f"  [green]PASS[/green]  {msg}")


def WARN(msg: str) -> None:
    counts["warn"] += 1
    console.print(f"  [yellow]WARN[/yellow]  {msg}")


def FAIL(msg: str) -> None:
    counts["fail"] += 1
    console.print(f"  [red]FAIL[/red]  {msg}")


def SKIP(msg: str) -> None:
    counts["skip"] += 1
    console.print(f"  [dim]SKIP[/dim]  {msg}")


def INFO(msg: str) -> None:
    counts["info"] += 1
    console.print(f"  [blue]INFO[/blue]  {msg}")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 1: IMPORTS
# ═════════════════════════════════════════════════════════════════════════


def test_imports() -> None:
    console.rule("[bold]Section 1: Imports[/bold]")

    # 1.1 — generator
    try:
        from analysis.generator import generate_analyses  # noqa: F401
        PASS("Import generate_analyses")
    except Exception as e:
        FAIL(f"Import generate_analyses: {e}")

    # 1.2 — staleness
    try:
        from analysis.staleness import get_stories_needing_analysis  # noqa: F401
        PASS("Import get_stories_needing_analysis")
    except Exception as e:
        FAIL(f"Import get_stories_needing_analysis: {e}")

    # 1.3 — internal helpers
    try:
        from analysis.generator import (  # noqa: F401
            _needs_analysis,
            _build_sonnet_prompt,
            _parse_response,
        )
        PASS("Import internal helpers (_needs_analysis, _build_sonnet_prompt, _parse_response)")
    except Exception as e:
        FAIL(f"Import internal helpers: {e}")

    # 1.4 — orchestrator
    try:
        from pipeline.process import run_analysis  # noqa: F401
        PASS("Import run_analysis from pipeline.process")
    except Exception as e:
        FAIL(f"Import run_analysis: {e}")

    # 1.5 — Anthropic SDK
    try:
        from anthropic import Anthropic  # noqa: F401
        PASS("Anthropic SDK available")
    except Exception as e:
        FAIL(f"Anthropic SDK: {e}")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 2: DB CONNECTIVITY
# ═════════════════════════════════════════════════════════════════════════


def test_db() -> tuple[list[dict], int | None]:
    """Returns (active_stories, first_story_id) for use by later sections."""
    console.rule("[bold]Section 2: DB Connectivity[/bold]")

    from db import queries as db

    # 2.1 — get_active_stories
    stories: list[dict] = []
    try:
        stories = db.get_active_stories()
        if len(stories) > 0:
            PASS(f"get_active_stories: {len(stories)} active stories")
        else:
            FAIL("No active stories in DB")
    except Exception as e:
        FAIL(f"get_active_stories raised: {e}")
        return [], None

    first_id = stories[0]["id"] if stories else None

    # 2.2 — get_analysis
    try:
        result = db.get_analysis(first_id)
        if result is None or isinstance(result, dict):
            PASS(f"get_analysis(#{first_id}): returns {'dict' if result else 'None'}")
        else:
            FAIL(f"get_analysis returned unexpected type: {type(result)}")
    except Exception as e:
        FAIL(f"get_analysis raised: {e}")

    # 2.3 — get_stale_analyses
    try:
        result = db.get_stale_analyses(12.0)
        if isinstance(result, list):
            PASS(f"get_stale_analyses: {len(result)} stale")
        else:
            FAIL(f"get_stale_analyses returned {type(result)}, expected list")
    except Exception as e:
        FAIL(f"get_stale_analyses raised: {e}")

    # 2.4 — upsert + verify + cleanup
    if first_id is not None:
        test_data = {
            "story_id": first_id,
            "headline": "TEST HEADLINE \u2014 DELETE ME",
            "dateline": "TEST",
            "lede": "Test lede.",
            "context": "Test context.",
            "contrasts": [],
            "facts": [],
            "bottom_line": "Test.",
            "coverage_note": "Test.",
            "article_count_at_gen": 0,
        }

        # Save existing analysis to restore later
        existing_analysis = db.get_analysis(first_id)

        try:
            db.upsert_analysis(test_data)
            result = db.get_analysis(first_id)
            if result and result.get("headline") == "TEST HEADLINE \u2014 DELETE ME":
                PASS("upsert_analysis: test row created and verified")
            else:
                FAIL("upsert_analysis didn't persist correctly")

            # Cleanup: restore original or delete test row
            if existing_analysis:
                # Restore original analysis
                db.upsert_analysis(existing_analysis)
                PASS("Cleanup: original analysis restored")
            else:
                # Delete test row
                from db.client import get_client
                client = get_client()
                client.table("analyses").delete().eq(
                    "story_id", first_id
                ).execute()
                PASS("Cleanup: test row deleted")
        except Exception as e:
            FAIL(f"upsert_analysis raised: {e}")
    else:
        SKIP("upsert_analysis: no stories to test with")

    return stories, first_id


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 3: STALENESS CHECKER
# ═════════════════════════════════════════════════════════════════════════


def test_staleness(stories: list[dict]) -> list[int]:
    """Returns list of story IDs needing analysis."""
    console.rule("[bold]Section 3: Staleness Checker[/bold]")

    from analysis.staleness import get_stories_needing_analysis
    from db import queries as db

    # 3.1 — returns list
    ids: list[int] = []
    try:
        ids = get_stories_needing_analysis(max_results=10)
        if isinstance(ids, list):
            PASS(f"get_stories_needing_analysis: {len(ids)} stories need analysis")
        else:
            FAIL(f"Returned {type(ids)}, expected list")
            return []
    except Exception as e:
        FAIL(f"get_stories_needing_analysis raised: {e}")
        return []

    # 3.2 — valid story IDs
    active_ids = {s["id"] for s in stories}
    all_valid = True
    for sid in ids:
        if sid not in active_ids:
            FAIL(f"Story #{sid} returned by staleness checker but not in active stories")
            all_valid = False
    if all_valid and ids:
        PASS("All returned IDs are active stories")
    elif not ids:
        INFO("No stories need analysis — nothing to validate")

    # 3.3 — minimum article count
    all_above_min = True
    for sid in ids[:5]:  # check first 5 to avoid too many DB calls
        articles = db.get_articles_for_story(sid)
        if len(articles) < 3:
            FAIL(f"Story #{sid} has only {len(articles)} articles but was selected")
            all_above_min = False
    if all_above_min and ids:
        PASS("All selected stories have >= 3 articles")

    # 3.4 — priority ordering
    if len(ids) >= 2:
        story_data = {s["id"]: s for s in stories}
        first = story_data.get(ids[0], {})
        impact = first.get("impact_score", 0)
        topic = first.get("topic", "")[:40]
        if impact > 0:
            PASS(f"Top priority: #{ids[0]} impact={impact} topic='{topic}'")
        else:
            WARN(f"Top priority story #{ids[0]} has impact_score={impact}")
    elif len(ids) == 1:
        INFO("Only 1 story needs analysis — can't verify ordering")
    else:
        INFO("No stories need analysis — skipping priority check")

    return ids


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 4: PROMPT CONSTRUCTION
# ═════════════════════════════════════════════════════════════════════════


def test_prompt(stories: list[dict]) -> list[tuple[int, str, str]]:
    """Returns list of (story_id, system, user_msg) for cost estimation."""
    console.rule("[bold]Section 4: Prompt Construction[/bold]")

    from analysis.generator import _build_sonnet_prompt
    from db import queries as db

    if not stories:
        SKIP("No stories available for prompt construction test")
        return []

    top_story = max(stories, key=lambda s: s.get("impact_score") or 0)
    articles = db.get_articles_for_story(top_story["id"])

    if not articles:
        FAIL(f"No articles for top story #{top_story['id']}")
        return []

    # 4.1 — build prompt
    try:
        system_prompt, user_msg = _build_sonnet_prompt(top_story, articles)
        if system_prompt and user_msg:
            PASS(f"Built prompt for story #{top_story['id']} ({len(articles)} articles)")
        else:
            FAIL("Prompt returned empty strings")
            return []
    except Exception as e:
        FAIL(f"_build_sonnet_prompt raised: {e}")
        return []

    # 4.2 — system prompt key instructions
    sp_lower = system_prompt.lower()
    if "neutral" in sp_lower or "wire-service" in sp_lower:
        PASS("System prompt contains neutrality instructions")
    else:
        FAIL("System prompt missing neutrality instructions")

    if "json" in sp_lower:
        PASS("System prompt requires JSON output")
    else:
        FAIL("System prompt missing JSON output instruction")

    # 4.3 — user message contains story data
    um_lower = user_msg.lower()
    topic = top_story.get("topic", "")
    if topic and topic.lower() in um_lower:
        PASS(f"User message contains story topic")
    else:
        WARN(f"Story topic '{topic[:30]}' not found verbatim in user message")

    bias_checks = {
        "LEFT": "left" in um_lower,
        "RIGHT": "right" in um_lower,
        "CENTER": "center" in um_lower,
    }
    if all(bias_checks.values()):
        PASS("User message contains bias groupings (LEFT, RIGHT, CENTER)")
    else:
        missing = [k for k, v in bias_checks.items() if not v]
        FAIL(f"User message missing bias groupings: {missing}")

    # 4.4 — headlines distributed across bias groups
    group_headers = [
        "LEFT / FAR-LEFT",
        "LEFT-CENTER",
        "CENTER",
        "RIGHT-CENTER",
        "RIGHT / FAR-RIGHT",
    ]
    groups_present = sum(1 for h in group_headers if h in user_msg)
    if groups_present >= 3:
        PASS(f"{groups_present}/5 bias group headers present in prompt")
    elif groups_present >= 1:
        WARN(f"Only {groups_present}/5 bias groups — limited bias diversity in prompt")
    else:
        FAIL("No bias group headers found in prompt")

    # Check for "all CENTER" problem
    center_section = False
    non_center_has_headlines = False
    for header in group_headers:
        idx = user_msg.find(header)
        if idx == -1:
            continue
        # Find the next header or end
        next_idx = len(user_msg)
        for other in group_headers:
            oi = user_msg.find(other, idx + len(header))
            if oi != -1 and oi < next_idx:
                next_idx = oi
        section = user_msg[idx:next_idx]
        headline_count = section.count("- [")
        if header == "CENTER":
            center_section = headline_count > 0
        elif headline_count > 0:
            non_center_has_headlines = True

    if non_center_has_headlines:
        PASS("Headlines distributed across multiple bias groups (not all CENTER)")
    elif center_section and not non_center_has_headlines:
        FAIL(
            "All headlines grouped as CENTER — bias lookup may be broken. "
            "Check that _build_sonnet_prompt uses source_domain (not source_name) "
            "to look up SOURCE_BIAS."
        )
    else:
        WARN("Could not verify headline distribution across bias groups")

    # 4.5 — scoring data present
    for field in ("impact", "attention", "sentiment"):
        if field in um_lower:
            PASS(f"Prompt includes {field} data")
        else:
            WARN(f"Prompt doesn't include {field} — Sonnet won't have this data")

    # 4.6 — JSON structure requested
    json_fields = ["headline", "lede", "contrasts", "facts", "bottom_line", "coverage_note"]
    for field in json_fields:
        if field in user_msg:
            PASS(f"Prompt requests '{field}' in output JSON")
        else:
            FAIL(f"Prompt doesn't request '{field}' in output JSON")

    # 4.7 — headline count
    headline_lines = re.findall(r"^\s*-\s*\[", user_msg, re.MULTILINE)
    count = len(headline_lines)
    if 5 <= count <= 50:
        PASS(f"{count} headlines included in prompt")
    elif count < 5:
        WARN(f"Very few headlines in prompt ({count})")
    else:
        WARN(f"Too many headlines ({count}) — may hit token limits")

    # 4.8 — prompt size estimate
    est_tokens = len(user_msg) // 4
    INFO(f"Estimated prompt size: ~{est_tokens} tokens ({len(user_msg)} chars)")
    if est_tokens > 4000:
        WARN("Large prompt — consider reducing headline count")
    elif est_tokens < 1000:
        INFO("Small prompt — may not have enough context for rich analysis")

    return [(top_story["id"], system_prompt, user_msg)]


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 5: JSON PARSING
# ═════════════════════════════════════════════════════════════════════════


def test_parsing() -> None:
    console.rule("[bold]Section 5: JSON Parsing[/bold]")

    from analysis.generator import _parse_response

    # 5.1 — valid JSON
    mock_response = """
    {
      "headline": "Senate Advances Immigration Bill in Bipartisan Vote",
      "dateline": "WASHINGTON (ClearSignal)",
      "lede": "The U.S. Senate passed a comprehensive immigration reform bill Thursday in a 64-36 vote that drew support from both parties.",
      "context": "The bill has been debated for six months. It represents the first major immigration legislation since 2013.",
      "contrasts": [
        {
          "theme": "Economic impact framing",
          "sourceA": "CNN",
          "biasA": "left-center",
          "claimA": "Bill will boost GDP by providing path to citizenship for workers",
          "sourceB": "Fox News",
          "biasB": "right-center",
          "claimB": "Bill will depress wages for American workers"
        }
      ],
      "facts": [
        {
          "claim": "Bill grants amnesty to all undocumented immigrants",
          "reality": "Bill provides a 10-year pathway requiring background checks, employment, and tax payment",
          "verdict": "misleading"
        }
      ],
      "bottom_line": "If signed into law, the bill would affect an estimated 11 million undocumented immigrants and change hiring requirements for all U.S. employers.",
      "coverage_note": "Covered by 45 articles from 28 sources across the full political spectrum."
    }
    """

    try:
        parsed = _parse_response(mock_response)
        if parsed is not None:
            PASS("Parse valid JSON response")
        else:
            FAIL("Parser rejected valid JSON")
            return

        if parsed["headline"] == "Senate Advances Immigration Bill in Bipartisan Vote":
            PASS("Headline parsed correctly")
        else:
            FAIL(f"Headline mismatch: {parsed['headline']}")

        if isinstance(parsed["contrasts"], list) and len(parsed["contrasts"]) == 1:
            PASS("Contrasts parsed as list with 1 item")
        else:
            FAIL(f"Contrasts wrong: {type(parsed.get('contrasts'))}")

        if isinstance(parsed["facts"], list) and len(parsed["facts"]) == 1:
            PASS("Facts parsed as list with 1 item")
        else:
            FAIL(f"Facts wrong: {type(parsed.get('facts'))}")

        if parsed["facts"][0]["verdict"] == "misleading":
            PASS("Fact verdict parsed correctly")
        else:
            FAIL(f"Verdict wrong: {parsed['facts'][0].get('verdict')}")
    except Exception as e:
        FAIL(f"Parse valid JSON raised: {e}")

    # 5.2 — markdown-fenced JSON
    mock_fenced = "```json\n" + mock_response.strip() + "\n```"
    try:
        parsed = _parse_response(mock_fenced)
        if parsed is not None and parsed["headline"] == "Senate Advances Immigration Bill in Bipartisan Vote":
            PASS("Parse markdown-fenced JSON")
        else:
            FAIL("Parser doesn't handle markdown-fenced JSON")
    except Exception as e:
        FAIL(f"Fenced JSON raised: {e}")

    # 5.3 — invalid JSON
    try:
        parsed = _parse_response("This is not JSON at all")
        if parsed is None:
            PASS("Gracefully rejects invalid JSON")
        else:
            FAIL("Parser accepted invalid JSON")
    except Exception:
        FAIL("Invalid JSON raised exception instead of returning None")

    # 5.4 — truncated JSON
    try:
        parsed = _parse_response('{"headline": "Test", "lede": "Test lede", "context": "Te')
        if parsed is None:
            PASS("Gracefully rejects truncated JSON")
        else:
            FAIL("Parser accepted truncated JSON")
    except Exception:
        FAIL("Truncated JSON raised exception instead of returning None")

    # 5.5 — missing required fields
    try:
        parsed = _parse_response('{"headline": "Test", "lede": "Just a lede"}')
        # _parse_response requires headline + lede + bottom_line
        if parsed is None:
            PASS("Rejects JSON with missing required fields (bottom_line)")
            INFO("Parser enforces: headline + lede + bottom_line required")
        else:
            PASS("Accepts partial JSON (missing fields get defaults at storage)")
            WARN("Ensure missing fields get sensible defaults when stored")
    except Exception:
        FAIL("Partial JSON raised exception instead of returning None or dict")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 6: PIPELINE WIRING
# ═════════════════════════════════════════════════════════════════════════


def test_wiring() -> None:
    console.rule("[bold]Section 6: Pipeline Wiring[/bold]")

    from analysis.staleness import get_stories_needing_analysis

    # 6.1 — run_analysis exists
    try:
        from pipeline.process import run_analysis  # noqa: F401
        PASS("run_analysis exists in pipeline/process.py")
    except Exception as e:
        FAIL(f"run_analysis import: {e}")

    # 6.2 — main.py references run_analysis
    try:
        main_path = os.path.join(
            os.path.dirname(__file__), "..", "pipeline", "main.py"
        )
        with open(main_path, encoding="utf-8") as f:
            main_src = f.read()

        if "run_analysis" in main_src:
            # Check it's not commented out
            active_lines = [
                line for line in main_src.splitlines()
                if "run_analysis" in line and not line.strip().startswith("#")
            ]
            if active_lines:
                PASS("pipeline/main.py calls run_analysis (not commented out)")
            else:
                WARN("run_analysis appears in main.py but is commented out")
        else:
            FAIL("run_analysis not found in pipeline/main.py")
    except Exception as e:
        FAIL(f"Could not read pipeline/main.py: {e}")

    # 6.3 — run_analysis without API calls
    ids = get_stories_needing_analysis(max_results=5)
    if len(ids) == 0:
        try:
            from pipeline.process import run_analysis
            result = run_analysis()
            if result.get("generated", -1) == 0:
                PASS("Orchestrator short-circuits when no stories need analysis")
            else:
                WARN(f"run_analysis returned generated={result.get('generated')}")
        except Exception as e:
            FAIL(f"run_analysis raised: {e}")
    else:
        SKIP(
            f"{len(ids)} stories need analysis — skipping orchestrator test "
            "to avoid API costs"
        )
        INFO("Run 'python -m pipeline.main --once' to generate analyses (~$0.05)")


# ═════════════════════════════════════════════════════════════════════════
#  SECTION 7: COST ESTIMATE
# ═════════════════════════════════════════════════════════════════════════


def test_cost(stories: list[dict], needing_ids: list[int]) -> None:
    console.rule("[bold]Section 7: Cost Estimate[/bold]")

    from analysis.generator import _build_sonnet_prompt
    from analysis.staleness import get_stories_needing_analysis
    from db import queries as db

    # 7.1 — full count
    all_needing = get_stories_needing_analysis(max_results=100)
    INFO(f"{len(all_needing)} stories need analysis total")

    if not all_needing:
        INFO("No stories need analysis — cost is $0.00")
        return

    story_data = {s["id"]: s for s in stories}

    # 7.2 — estimate per story
    batch_cost = 0.0
    batch_size = min(5, len(all_needing))

    for sid in all_needing[:batch_size]:
        story = story_data.get(sid)
        if not story:
            continue
        articles = db.get_articles_for_story(sid)
        if not articles:
            continue

        system_prompt, user_msg = _build_sonnet_prompt(story, articles)
        input_tokens = (len(system_prompt) + len(user_msg)) // 4
        output_tokens = 800
        # Sonnet pricing: $3/M input, $15/M output
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
        batch_cost += cost
        topic = story.get("topic", "?")[:35]
        INFO(
            f"  Story #{sid} ({topic}): "
            f"~{input_tokens} in + ~{output_tokens} out = ~${cost:.4f}"
        )

    if batch_size > 0 and batch_cost > 0:
        total_est = batch_cost * (len(all_needing) / batch_size)
        console.print()
        INFO(f"First batch ({batch_size} stories): ~${batch_cost:.3f}")
        INFO(f"All {len(all_needing)} stories: ~${total_est:.3f}")
        monthly = batch_cost * 4 * 24 * 30
        INFO(f"Monthly at 4 cycles/hour: ~${monthly:.2f}/month (worst case)")


# ═════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s | %(message)s")

    console.print()
    console.rule("[bold blue]Analysis Module Validation[/bold blue]")
    console.print()

    # Section 1
    test_imports()

    # Section 2
    stories, first_id = test_db()

    # Section 3
    needing_ids = test_staleness(stories) if stories else []

    # Section 4
    test_prompt(stories)

    # Section 5
    test_parsing()

    # Section 6
    test_wiring()

    # Section 7
    test_cost(stories, needing_ids)

    # ── Summary ─────────────────────────────────────────────────────
    console.print()
    console.rule("[bold]Analysis Module Validation Summary[/bold]")

    summary = Text()
    summary.append(f"  PASS:  {counts['pass']}\n", style="bold green")
    summary.append(f"  WARN:  {counts['warn']}\n", style="bold yellow")
    summary.append(f"  FAIL:  {counts['fail']}\n", style="bold red")
    summary.append(f"  SKIP:  {counts['skip']}\n", style="dim")

    console.print(Panel(summary, border_style="blue"))

    if counts["fail"] == 0:
        console.print(
            "[bold green]Safe to run.[/bold green] Execute: "
            "[bold]python -m pipeline.main --once[/bold]"
        )
    else:
        console.print(
            "[bold red]Fix failures before running[/bold red] "
            "(to avoid wasting API budget)"
        )
    console.print()
