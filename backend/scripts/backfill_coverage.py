"""One-time backfill of coverage_score for all existing active stories.

Computes the 4-factor coverage score (article_count_norm, source_diversity,
recency, velocity) for every active story and stores it in stories.coverage_score.

Usage:
    cd backend && .venv/Scripts/python.exe -m scripts.backfill_coverage
"""

from __future__ import annotations

import logging

from scoring.coverage import score_coverage

logging.basicConfig(level="INFO", format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def backfill():
    logger.info("Backfilling coverage scores for all active stories...")
    result = score_coverage()
    logger.info("Done: %d stories scored", result["scored"])

    if result["scores"]:
        top = sorted(result["scores"], key=lambda x: x["score"], reverse=True)[:10]
        for s in top:
            b = s["breakdown"]
            logger.info(
                "  Story #%d: coverage=%d  (articles=%d  sources=%d  recency=%d  velocity=%d)",
                s["story_id"], s["score"],
                b["article_count_norm"], b["source_diversity"],
                b["recency"], b["velocity"],
            )


if __name__ == "__main__":
    backfill()
