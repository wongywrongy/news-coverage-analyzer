"""Business logic constants for the ClearSignal pipeline.

Centralizes magic numbers and thresholds used across pipeline stages.
Import from here instead of hardcoding values in individual modules.
"""
from __future__ import annotations

# ── Heat formula weights ─────────────────────────────────────────
HEAT_WEIGHT_IMPACT: float = 0.30
HEAT_WEIGHT_SOURCE_BREADTH: float = 0.25
HEAT_WEIGHT_VELOCITY: float = 0.25
HEAT_WEIGHT_DIVERGENCE: float = 0.20

# ── Recency decay (hours, multiplier) ────────────────────────────
RECENCY_TIERS: list[tuple[int, float]] = [
    (6, 1.0),
    (12, 0.85),
    (24, 0.65),
    (48, 0.4),
]
RECENCY_DEFAULT: float = 0.2

# ── Scoring ──────────────────────────────────────────────────────
ENTITY_BOOST_CAP: float = 15.0
ENTITY_BOOST_FACTOR: float = 0.15
COVERAGE_GAP_BADGE_THRESHOLD: int = 40

# ── Embedding ────────────────────────────────────────────────────
EMBEDDING_DIMENSIONS: int = 384
EMBEDDING_BATCH_SIZE: int = 100

# ── Pipeline thresholds ──────────────────────────────────────────
STALE_ANALYSIS_HOURS: int = 18
ARTICLE_GROWTH_THRESHOLD: float = 0.20  # 20% triggers re-analysis
RESCORE_HOURS: float = 6.0
RESCORE_GROWTH_THRESHOLD: float = 0.20

# ── Data freshness ───────────────────────────────────────────────
FRESHNESS_THRESHOLD_HOURS: int = 48

# ── Framing categories ───────────────────────────────────────────
TOTAL_FRAMING_CATEGORIES: int = 7

# ── Insights ─────────────────────────────────────────────────────
UNDERCOVERED_THRESHOLD: int = 15
SURGING_THRESHOLD: float = 0.20  # 20% increase
MIN_TOPICS_PER_CATEGORY: int = 3

# ── Clustering ───────────────────────────────────────────────────
MAX_HEADLINES_PER_LABEL: int = 15
MAX_LABEL_WORDS: int = 14
