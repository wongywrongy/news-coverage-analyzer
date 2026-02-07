"""
Sentiment analysis by political lean for ClearSignal stories.

Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) from NLTK
to score article headlines, then aggregates by left/center/right lean.

VADER is tuned for social-media text and short headlines — a good fit
for news titles without needing a transformer model.

Depends on: db.queries (get_active_stories, get_articles_for_story,
            update_article_sentiment, update_story_metadata)
"""

import logging
from statistics import mean

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from config.sources import SOURCE_BIAS
from db.queries import (
    get_active_stories,
    get_articles_for_story,
    update_article_sentiment,
    update_story_metadata,
)

logger = logging.getLogger(__name__)

# ── Political-lean groupings ─────────────────────────────────────────────────

_LEFT_LABELS = frozenset({"far-left", "left", "left-center"})
_CENTER_LABELS = frozenset({"center"})
_RIGHT_LABELS = frozenset({"right-center", "right", "far-right"})


# ── VADER lazy singleton ─────────────────────────────────────────────────────

_sia: SentimentIntensityAnalyzer | None = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    """Return a cached SentimentIntensityAnalyzer, downloading the lexicon if needed."""
    global _sia
    if _sia is None:
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            logger.info("Downloading VADER lexicon …")
            nltk.download("vader_lexicon", quiet=True)
        _sia = SentimentIntensityAnalyzer()
    return _sia


# ── Core scoring ─────────────────────────────────────────────────────────────


def _compute_title_sentiment(title: str) -> float:
    """Simple rule-based sentiment scoring for a headline.

    Returns float from -1.0 (very negative) to 1.0 (very positive).

    Approach: VADER compound score — a normalised, weighted composite
    of lexicon ratings.  Designed for short social-media text, which
    makes it a good fit for news headlines.
    """
    sia = _get_analyzer()
    return sia.polarity_scores(title)["compound"]


def _lean_for_bias(bias_label: str) -> str | None:
    """Map a bias label to 'left', 'center', or 'right'.

    Returns None if the label is unknown.
    """
    if bias_label in _LEFT_LABELS:
        return "left"
    if bias_label in _CENTER_LABELS:
        return "center"
    if bias_label in _RIGHT_LABELS:
        return "right"
    return None


# ── Main entry point ─────────────────────────────────────────────────────────


def analyze_sentiment(
    story_ids: list[int] | None = None,
    story_articles: dict[int, list[dict]] | None = None,
) -> dict:
    """Compute sentiment breakdown by political lean for each story.

    For every story, scores each article headline with VADER, groups
    scores by left / center / right, and stores the per-group averages
    on the story row plus the per-article score on each article.

    Args:
        story_ids: Specific story IDs to analyse.  ``None`` means all
                   active stories.

    Returns:
        {
            "analyzed": int,
            "results": [
                {"story_id": int, "left": float|None,
                 "center": float|None, "right": float|None},
                …
            ]
        }
    """
    # Resolve which stories to process
    if story_ids is not None:
        stories = [{"id": sid} for sid in story_ids]
    else:
        stories = get_active_stories()

    results: list[dict] = []
    analyzed = 0

    for story in stories:
        story_id: int = story["id"]
        articles = (
            story_articles[story_id]
            if story_articles is not None and story_id in story_articles
            else get_articles_for_story(story_id)
        )

        if not articles:
            logger.debug("Story %d has no articles — skipping", story_id)
            continue

        # Buckets: lean → list of sentiment floats
        buckets: dict[str, list[float]] = {
            "left": [],
            "center": [],
            "right": [],
        }

        for article in articles:
            title = (article.get("title") or "").strip()
            if not title:
                continue

            sentiment = _compute_title_sentiment(title)

            # Persist per-article sentiment
            update_article_sentiment(article["id"], round(sentiment, 4))

            # Determine political lean from the article's source_bias field,
            # falling back to SOURCE_BIAS lookup by source_domain.
            bias_label = article.get("source_bias", "")
            if not bias_label:
                domain = article.get("source_domain", "")
                bias_label = SOURCE_BIAS.get(domain, {}).get("label", "")

            lean = _lean_for_bias(bias_label)
            if lean:
                buckets[lean].append(sentiment)

        # Compute averages (None when no data in a group)
        avg_left = round(mean(buckets["left"]), 4) if buckets["left"] else None
        avg_center = round(mean(buckets["center"]), 4) if buckets["center"] else None
        avg_right = round(mean(buckets["right"]), 4) if buckets["right"] else None

        # Persist on story row
        update_story_metadata(
            story_id,
            sentiment_left=avg_left,
            sentiment_center=avg_center,
            sentiment_right=avg_right,
        )

        results.append({
            "story_id": story_id,
            "left": avg_left,
            "center": avg_center,
            "right": avg_right,
        })
        analyzed += 1

        logger.info(
            "Story %d sentiment  L=%s  C=%s  R=%s  (%d articles)",
            story_id,
            f"{avg_left:+.3f}" if avg_left is not None else "n/a",
            f"{avg_center:+.3f}" if avg_center is not None else "n/a",
            f"{avg_right:+.3f}" if avg_right is not None else "n/a",
            len(articles),
        )

    return {"analyzed": analyzed, "results": results}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)-8s %(name)s: %(message)s")

    # Quick VADER sanity check before hitting the DB
    print("— VADER sanity check —")
    for sample in [
        "Economy grows at record pace, unemployment hits historic low",
        "Massive explosion kills dozens in devastating attack",
        "Senate passes bipartisan infrastructure bill",
        "President slams opponents in fiery speech",
        "Weather forecast: partly cloudy with a chance of rain",
    ]:
        score = _compute_title_sentiment(sample)
        print(f"  {score:+.3f}  {sample}")

    print()
    result = analyze_sentiment()
    print(f"\nAnalyzed {result['analyzed']} stories")
    for r in result["results"][:10]:
        left = f"{r['left']:.2f}" if r["left"] is not None else "n/a"
        center = f"{r['center']:.2f}" if r["center"] is not None else "n/a"
        r_val = f"{r['right']:.2f}" if r["right"] is not None else "n/a"
        print(f"  Story #{r['story_id']}: L={left} C={center} R={r_val}")
