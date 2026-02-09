"""
One-off migration: fix truncated, vague, or overly long story headlines.

Uses the same Claude Haiku headline-rename prompt that the pipeline uses,
but applies broader selection criteria to catch stories created before
prompt improvements.

Usage:
    cd backend
    python -m scripts.migrate_headlines              # dry run (preview)
    python -m scripts.migrate_headlines --apply       # write changes
    python -m scripts.migrate_headlines --limit 10    # cap at 10 stories
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher

# Ensure backend/ is on the path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from anthropic import Anthropic

from config.settings import settings
from db.client import get_client
from db import queries as db

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 256
_SIMILARITY_THRESHOLD = 0.85
_RATE_LIMIT_SECONDS = 1.0

_SYSTEM_PROMPT = (
    "You rewrite vague or generic news story titles into specific, neutral "
    "headlines. You follow strict rules for neutrality."
)

_VAGUE_OPENERS = [
    "the last ",
    "the first ",
    "a new ",
    "the new ",
    "the latest ",
    "breaking:",
    "update:",
    "just in:",
    "report:",
    "exclusive:",
]

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "headline_migration_log.json",
)


def _needs_fix(headline: str) -> str | None:
    """Check if a headline needs fixing. Returns reason string or None."""
    if not headline or not headline.strip():
        return "empty"

    h = headline.strip()

    # Too short (likely truncated)
    if len(h) < 30:
        return f"too short ({len(h)} chars)"

    # Too long for card display
    if len(h) > 120:
        return f"too long ({len(h)} chars)"

    # Ends mid-word / mid-sentence: no proper ending and doesn't look like a title
    last_char = h.rstrip()[-1]
    if last_char not in ".?!)\"'" and not h[0].isupper():
        return "appears truncated (no ending punctuation, lowercase start)"

    # Check for truncation more broadly: ends mid-word without punctuation
    # and is suspiciously short for its content
    if last_char not in ".?!)\"'" and len(h.split()) <= 4:
        return f"likely truncated ({len(h.split())} words, no ending)"

    # Vague openers that suggest a copied article title
    h_lower = h.lower()
    for opener in _VAGUE_OPENERS:
        if h_lower.startswith(opener):
            return f"vague opener ('{opener.strip()}')"

    # Colon followed by a quote — suggests a pulled article headline
    if re.search(r':\s*["\u201c]', h):
        return "colon + quote (likely copied headline)"

    return None


def _build_prompt(topic: str, articles: list[dict]) -> str:
    """Build the rename prompt — same logic as analysis/headlines.py."""
    headlines = []
    for a in articles[:20]:
        source = a.get("source_name") or "unknown"
        title = a.get("title") or "(no title)"
        lede = (a.get("description") or "").strip()
        entry = f"- {title} ({source})"
        if lede:
            entry += f"\n  Lede: {lede}"
        headlines.append(entry)

    return (
        f"Rewrite this story title to be specific and neutral.\n\n"
        f"Current title: {topic}\n\n"
        f"Article headlines from this cluster:\n"
        + "\n".join(headlines)
        + "\n\n"
        "Rules:\n"
        "- Maximum 12 words.\n"
        "- Use factual, descriptive language only.\n"
        "- No emotional adjectives (devastating, controversial, unprecedented, "
        "alarming, historic, shocking).\n"
        "- No loaded framing: prefer 'X would change Y by Z' over 'X threatens Y' "
        "or 'X saves Y.'\n"
        "- Identify the most specific shared subject across articles.\n"
        "- If articles describe different angles of one event, lead with the "
        "event, not the angle.\n\n"
        'Respond ONLY with valid JSON:\n'
        '{\n'
        '  "headline": "<max 12 words, specific, neutral>",\n'
        '  "rationale": "<one sentence: what made the original vague and how this fixes it>"\n'
        '}'
    )


def _similarity(a: str, b: str) -> float:
    """Compute string similarity ratio (0-1)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def migrate(apply: bool = False, limit: int | None = None) -> None:
    supabase = get_client()

    # Fetch ALL stories (not just active), since we want to fix old ones too
    print("Scanning stories...")
    response = supabase.table("stories").select("id, topic").execute()
    all_stories = response.data or []
    print(f"Found {len(all_stories)} total stories.\n")

    # Flag stories that need headline fixes
    flagged = []
    for s in all_stories:
        headline = s.get("topic") or ""
        reason = _needs_fix(headline)
        if reason:
            flagged.append({"id": s["id"], "headline": headline, "reason": reason})

    if not flagged:
        print("No stories flagged for headline fixes.")
        return

    print(f"Flagged {len(flagged)} stories for review.\n")

    if limit:
        flagged = flagged[:limit]
        print(f"(Limited to {limit} stories)\n")

    client = Anthropic(api_key=settings.anthropic_api_key)
    migration_log = []
    updates_pending = 0
    skipped_similar = 0
    skipped_no_articles = 0
    errors = 0

    for i, entry in enumerate(flagged):
        story_id = entry["id"]
        old_headline = entry["headline"]
        reason = entry["reason"]

        print(f"[{i + 1}/{len(flagged)}] Story {story_id}")
        print(f"  OLD: \"{old_headline}\"")
        print(f"  Reason: {reason}")

        # Fetch articles for this story
        try:
            articles = db.get_articles_for_story(story_id)
        except Exception as exc:
            print(f"  ERROR fetching articles: {exc}")
            errors += 1
            continue

        if not articles:
            print(f"  Skipping (no articles)")
            skipped_no_articles += 1
            continue

        # Call Claude Haiku
        try:
            prompt = _build_prompt(old_headline, articles)
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            new_headline = parsed.get("headline", "").strip()
            rationale = parsed.get("rationale", "")

            if not new_headline or len(new_headline.split()) > 14:
                print(f"  ERROR: Haiku returned invalid headline: \"{new_headline}\"")
                errors += 1
                time.sleep(_RATE_LIMIT_SECONDS)
                continue

        except Exception as exc:
            print(f"  ERROR calling Haiku: {exc}")
            errors += 1
            time.sleep(_RATE_LIMIT_SECONDS)
            continue

        print(f"  NEW: \"{new_headline}\"")

        # Check similarity
        sim = _similarity(old_headline, new_headline)
        if sim > _SIMILARITY_THRESHOLD:
            print(f"  → Skipping (similar, {sim:.0%})")
            skipped_similar += 1
        else:
            log_entry = {
                "story_id": story_id,
                "old_headline": old_headline,
                "new_headline": new_headline,
                "rationale": rationale,
                "reason_flagged": reason,
                "similarity": round(sim, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            migration_log.append(log_entry)

            if apply:
                try:
                    db.update_story_metadata(story_id, topic=new_headline)
                    print(f"  → Updated")
                except Exception as exc:
                    print(f"  → WRITE ERROR: {exc}")
                    errors += 1
            else:
                print(f"  → Will update")
                updates_pending += 1

        print()
        time.sleep(_RATE_LIMIT_SECONDS)

    # Write migration log
    if migration_log:
        # Append to existing log if present
        existing_log = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    existing_log = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing_log = []

        existing_log.extend(migration_log)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_log, f, indent=2, ensure_ascii=False)
        print(f"Log written to {LOG_FILE}")

    # Summary
    print(f"\n{'='*50}")
    if apply:
        print(f"Done. {len(migration_log)} updated, "
              f"{skipped_similar} skipped (similar), "
              f"{skipped_no_articles} skipped (no articles), "
              f"{errors} errors.")
    else:
        print(f"Done. {updates_pending} updates pending. "
              f"{skipped_similar} skipped (similar), "
              f"{skipped_no_articles} skipped (no articles), "
              f"{errors} errors.")
        if updates_pending > 0:
            print(f"\nRun with --apply to write changes.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fix truncated, vague, or overly long story headlines"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write changes to Supabase (default: dry run)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max stories to process"
    )
    args = parser.parse_args()

    if not args.apply:
        print("DRY RUN — no changes will be written. Pass --apply to write.\n")

    migrate(apply=args.apply, limit=args.limit)
