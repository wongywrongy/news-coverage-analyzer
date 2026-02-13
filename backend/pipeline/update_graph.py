"""Entity graph update — compute relationship edges and entity importance.

Runs after entity extraction. Does three things:
1. Create/strengthen relationship edges between co-occurring entities
2. Compute relationship strength (co-occurrence * recency * avg topic importance)
3. Run PageRank-style importance propagation (3 iterations)

No AI calls — purely database reads and writes.

Usage:
    python -m pipeline.update_graph
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import UTC, datetime

from db.queries import (
    get_active_stories,
    get_all_entities,
    get_all_entity_relationships,
    get_entities_for_topic,
    get_topics_for_entity,
    update_entity_importance,
    update_relationship_strength,
    upsert_entity_relationship,
)

logger = logging.getLogger(__name__)

_IMPORTANCE_ITERATIONS = 3
_DIRECT_WEIGHT = 0.6
_NEIGHBOR_WEIGHT = 0.4


def _recency_weight(last_linked_at: str | None) -> float:
    """Compute recency weight based on how recently the edge was last active."""
    if not last_linked_at:
        return 0.2
    try:
        if isinstance(last_linked_at, str):
            dt = datetime.fromisoformat(last_linked_at.replace("Z", "+00:00"))
        else:
            dt = last_linked_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        days_ago = (datetime.now(UTC) - dt).total_seconds() / 86400
        if days_ago < 7:
            return 1.0
        elif days_ago < 30:
            return 0.7
        elif days_ago < 90:
            return 0.4
        else:
            return 0.2
    except (ValueError, TypeError):
        return 0.2


def _build_edges(stories: list[dict]) -> dict:
    """Build/update edges between all entities that co-occur in topics.

    Returns stats dict.
    """
    stats = {"edges_created": 0, "edges_updated": 0}

    for story in stories:
        sid = story["id"]
        entities = get_entities_for_topic(sid)
        if len(entities) < 2:
            continue

        entity_ids = [e["id"] for e in entities]

        # Create edges between every pair
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                upsert_entity_relationship(entity_ids[i], entity_ids[j])
                stats["edges_created"] += 1

    return stats


def _compute_strengths(stories: list[dict]) -> int:
    """Compute relationship strength for all edges.

    strength = co_occurrence * recency_weight * avg_topic_importance

    Returns count of edges updated.
    """
    # Build a map of story_id → impact_score for avg computation
    story_score_map = {}
    for s in stories:
        story_score_map[s["id"]] = s.get("impact_score") or s.get("significance_score") or 0

    # Get all entities and their topic links for co-occurrence scoring
    all_entities = get_all_entities()
    entity_topics: dict[int, set[int]] = {}
    for ent in all_entities:
        eid = ent["id"]
        topics = get_topics_for_entity(eid)
        entity_topics[eid] = set(topics)

    # Get all edges and compute strength
    all_edges = get_all_entity_relationships()
    updated = 0

    for edge in all_edges:
        eid_a = edge["entity_a_id"]
        eid_b = edge["entity_b_id"]
        co_occ = edge.get("co_occurrence", 1)

        # Find topics where both entities appear
        topics_a = entity_topics.get(eid_a, set())
        topics_b = entity_topics.get(eid_b, set())
        shared_topics = topics_a & topics_b

        # Average impact score of shared topics
        if shared_topics:
            scores = [story_score_map.get(tid, 0) for tid in shared_topics]
            avg_importance = sum(scores) / len(scores) if scores else 0
        else:
            avg_importance = 0

        recency = _recency_weight(edge.get("last_linked_at"))

        # Normalize avg_importance to 0-1 range (scores are 0-100)
        norm_importance = avg_importance / 100.0 if avg_importance > 0 else 0.01

        strength = co_occ * recency * norm_importance
        update_relationship_strength(edge["id"], round(strength, 4))
        updated += 1

    return updated


def _propagate_importance(stories: list[dict]) -> int:
    """Run PageRank-style importance propagation.

    Each entity's importance is:
        0.6 * direct_score + 0.4 * neighbor_score

    direct_score = avg(impact_score of connected topics) * log(topic_count + 1)
    neighbor_score = weighted avg of neighbor importances by edge strength

    Runs _IMPORTANCE_ITERATIONS iterations.
    Returns count of entities updated.
    """
    # Build story score lookup
    story_score_map = {}
    for s in stories:
        story_score_map[s["id"]] = s.get("impact_score") or s.get("significance_score") or 0

    # Load all entities and their topic links
    all_entities = get_all_entities()
    if not all_entities:
        return 0

    entity_map = {e["id"]: e for e in all_entities}
    entity_topics: dict[int, list[int]] = {}
    for ent in all_entities:
        eid = ent["id"]
        entity_topics[eid] = get_topics_for_entity(eid)

    # Load all edges for neighbor lookups
    all_edges = get_all_entity_relationships()
    # Build adjacency: entity_id → [(neighbor_id, strength)]
    adjacency: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for edge in all_edges:
        a, b = edge["entity_a_id"], edge["entity_b_id"]
        s = edge.get("strength", 0)
        adjacency[a].append((b, s))
        adjacency[b].append((a, s))

    # Initialize importance scores
    importance: dict[int, float] = {eid: e.get("importance", 0) for eid, e in entity_map.items()}

    for iteration in range(_IMPORTANCE_ITERATIONS):
        new_importance: dict[int, float] = {}

        for eid in entity_map:
            # Direct score: avg topic score * log(topic_count + 1)
            topics = entity_topics.get(eid, [])
            topic_count = len(topics)
            if topic_count > 0:
                topic_scores = [story_score_map.get(tid, 0) for tid in topics]
                avg_score = sum(topic_scores) / len(topic_scores)
                direct_score = avg_score * math.log(topic_count + 1)
            else:
                direct_score = 0

            # Neighbor score: weighted avg of neighbor importances
            neighbors = adjacency.get(eid, [])
            if neighbors:
                total_weight = sum(s for _, s in neighbors)
                if total_weight > 0:
                    neighbor_score = sum(
                        importance.get(nid, 0) * s for nid, s in neighbors
                    ) / total_weight
                else:
                    neighbor_score = 0
            else:
                neighbor_score = 0

            new_importance[eid] = _DIRECT_WEIGHT * direct_score + _NEIGHBOR_WEIGHT * neighbor_score

        importance = new_importance
        logger.debug("Importance propagation iteration %d complete", iteration + 1)

    # Persist updated importance scores
    updated = 0
    for eid, imp in importance.items():
        topic_count = len(entity_topics.get(eid, []))
        update_entity_importance(eid, round(imp, 2), topic_count)
        updated += 1

    return updated


def update_graph(story_ids: list[int] | None = None) -> dict:
    """Run the full graph update: edges → strengths → importance.

    Returns stats dict.
    """
    stats = {
        "edges_created": 0,
        "strengths_updated": 0,
        "entities_updated": 0,
        "errors": 0,
    }

    stories = get_active_stories()
    if not stories:
        logger.info("No active stories for graph update")
        return stats

    if story_ids is not None:
        id_set = set(story_ids)
        stories = [s for s in stories if s["id"] in id_set]

    try:
        # 1. Build/update edges
        edge_stats = _build_edges(stories)
        stats["edges_created"] = edge_stats.get("edges_created", 0)

        # 2. Compute relationship strengths (needs all stories for scoring context)
        all_stories = get_active_stories()
        stats["strengths_updated"] = _compute_strengths(all_stories)

        # 3. Propagate importance (needs all stories)
        stats["entities_updated"] = _propagate_importance(all_stories)

    except Exception as exc:
        logger.error("Graph update failed: %s", exc)
        stats["errors"] += 1

    logger.info(
        "Graph update complete: %d edges, %d strengths, %d entities updated",
        stats["edges_created"], stats["strengths_updated"], stats["entities_updated"],
    )
    return stats


if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logging.basicConfig(level="INFO", format="%(levelname)s  %(name)s  %(message)s")

    result = update_graph()
    print(f"\nEdges created/updated: {result['edges_created']}")
    print(f"Strengths updated: {result['strengths_updated']}")
    print(f"Entities updated: {result['entities_updated']}")
    print(f"Errors: {result['errors']}")
