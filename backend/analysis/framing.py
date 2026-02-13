"""Classify per-article editorial framing using Claude Haiku.

For each article in a story, classifies the framing approach:
- economic impact
- social/cultural impact
- policy/regulatory
- human interest
- geopolitical
- security/safety
- factual/wire

Also identifies notable inclusions and omissions relative to other articles
in the same cluster. Results are passed to the analysis generator as context.

Cost: ~$0.001 per article (Haiku input + output tokens).
"""

from __future__ import annotations

import json
import logging
import re

from anthropic import Anthropic

from config.settings import settings

logger = logging.getLogger(__name__)

_HAIKU_MODEL = settings.haiku_model
_MAX_TOKENS = 512
_MAX_BODY_WORDS = 300
_MAX_ARTICLES = 8  # Match analysis generator's article cap

_SYSTEM_PROMPT = (
    "You classify the editorial framing of a single news article. You "
    "describe WHAT the article emphasizes, not WHERE it falls on a political "
    "spectrum. You do not judge source credibility."
)


def _build_prompt(article: dict, other_articles: list[dict]) -> str:
    """Build the framing classification prompt for a single article."""
    source = article.get("source_name") or article.get("source_domain", "unknown")
    title = article.get("title", "(no title)")
    body = (article.get("body") or "").strip()
    words = body.split()
    excerpt = " ".join(words[:_MAX_BODY_WORDS])
    if len(words) > _MAX_BODY_WORDS:
        excerpt += "..."

    other_headlines = []
    for a in other_articles[:10]:
        other_source = a.get("source_name") or "unknown"
        other_title = a.get("title") or "(no title)"
        other_headlines.append(f"- {other_title} ({other_source})")

    return (
        f"Classify the framing of this article.\n\n"
        f"Source: {source}\n"
        f"Headline: {title}\n"
        f"Excerpt (first {_MAX_BODY_WORDS} words): {excerpt}\n\n"
        "Other articles on this story (for comparison):\n"
        + "\n".join(other_headlines)
        + "\n\n"
        "Framing categories (select all that apply):\n"
        '- "economic impact" — focuses on financial consequences, markets, costs, jobs\n'
        '- "social/cultural impact" — focuses on communities, identity groups, social norms\n'
        '- "policy/regulatory" — focuses on laws, rules, government action\n'
        '- "human interest" — focuses on individual people, personal stories\n'
        '- "geopolitical" — focuses on international relations, power dynamics\n'
        '- "security/safety" — focuses on threats, risks, protection\n'
        '- "factual/wire" — primarily factual reporting with minimal framing\n\n'
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "source": "' + source + '",\n'
        '  "framings": ["<all applicable categories>"],\n'
        '  "primary_framing": "<single dominant category>",\n'
        '  "notable_inclusions": "<facts, quotes, or angles present in this article '
        'but absent from others, or none identified>",\n'
        '  "notable_omissions": "<facts, quotes, or angles present in other articles '
        'but absent here, or none identified>"\n'
        "}"
    )


def classify_article_framings(
    articles: list[dict],
) -> list[dict]:
    """Classify framing for a list of articles in the same story.

    Returns a list of framing dicts, one per article, suitable for
    passing into the analysis generation prompt.

    Processes up to _MAX_ARTICLES articles to control costs.
    """
    if not articles:
        return []

    # Cap the number of articles we classify
    to_classify = articles[:_MAX_ARTICLES]
    results: list[dict] = []

    client = Anthropic(api_key=settings.anthropic_api_key)

    for article in to_classify:
        other_articles = [a for a in articles if a.get("id") != article.get("id")]

        try:
            prompt = _build_prompt(article, other_articles)
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

            # Ensure required fields
            framing = {
                "source": parsed.get("source", article.get("source_name", "unknown")),
                "framings": parsed.get("framings", []),
                "primary_framing": parsed.get("primary_framing", "factual/wire"),
                "notable_inclusions": parsed.get("notable_inclusions", "none identified"),
                "notable_omissions": parsed.get("notable_omissions", "none identified"),
            }
            results.append(framing)

            logger.debug(
                "Article '%s' (%s): primary_framing=%s",
                article.get("title", "?")[:40],
                framing["source"],
                framing["primary_framing"],
            )

        except Exception as exc:
            logger.warning(
                "Failed to classify framing for article %s: %s",
                article.get("id", "?"), exc,
            )
            # Return a fallback framing
            results.append({
                "source": article.get("source_name", "unknown"),
                "framings": ["factual/wire"],
                "primary_framing": "factual/wire",
                "notable_inclusions": "none identified",
                "notable_omissions": "none identified",
            })

    logger.info("Classified framing for %d articles.", len(results))
    return results
