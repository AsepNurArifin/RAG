"""
Graph Traversal — EnterpriseMind AI.

Cypher queries untuk entity lookup, path traversal, dan multi-hop reasoning.

Hanya diaktifkan untuk intent: analytical, comparison, comprehensive, ambiguous.
Ref: GRAPH_PLAN.md §5.4 & §7
"""

import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_TRAVERSAL_DEPTH = 3
GRAPH_INTENTS = {"analytical", "comparison", "comprehensive", "ambiguous"}


def should_use_graph(intent_type: str) -> bool:
    """Apakah query ini perlu graph traversal? Hanya untuk intent tertentu."""
    return intent_type in GRAPH_INTENTS


def extract_entities_from_query(query: str) -> list[str]:
    """
    Extract entity names from user query using LLM 8B.

    Args:
        query: User's natural language query

    Returns:
        List of entity name strings found in the query.
        Empty list if no entities detected.
    """
    from app.core.llm_provider import get_llm

    prompt = f"""Extract entity names from this query that match our knowledge base.

Our entity types: Skill, Training, SOP, Department, Position, Certificate, Policy

Query: {query}

Identify ALL entities mentioned. Return ONLY valid JSON array of strings.
Examples:
- "Apa hubungan Leadership dan Performance?" → ["Leadership", "Performance"]
- "Learning path menjadi HRBP" → ["HRBP"]
- "Berapa hari cuti tahunan?" → []

Respond: {{"entities": [...]}}"""

    try:
        llm = get_llm("fast", temperature=0.1, max_tokens=512)
        response = llm.invoke(prompt)
        raw = response.content.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        result = json.loads(raw)
        entities = result.get("entities", [])
        logger.info("[GraphQuery] Entities dari query '%s': %s", query[:50], entities)
        return entities
    except Exception as e:
        logger.warning("[GraphQuery] Gagal extract entities dari query: %s", e)
        return []


def find_entity_paths(entity_names: list[str], max_depth: int = MAX_TRAVERSAL_DEPTH) -> list[dict]:
    """
    Find paths between entities in the graph.

    For multiple entities: find connections between them.
    For single entity: find all related entities up to max_depth.

    Args:
        entity_names: List of entity name strings
        max_depth: Maximum traversal depth (default 3)

    Returns:
        List of path dicts with nodes, relationships, and depth.
        Empty list if no paths found or Neo4j unavailable.
    """
    if not entity_names:
        return []

    if not settings.NEO4J_ENABLED:
        logger.info("[GraphTraversal] Neo4j disabled, skipping.")
        return []

    try:
        from app.core.neo4j_client import get_neo4j
        driver = get_neo4j()
    except Exception as e:
        logger.warning("[GraphTraversal] Neo4j tidak tersedia: %s", e)
        return []

    paths = []

    with driver.session() as session:
        if len(entity_names) >= 2:
            paths.extend(_find_paths_between_entities(session, entity_names, max_depth))
        else:
            paths.extend(_find_paths_from_entity(session, entity_names[0], max_depth))

    logger.info("[GraphTraversal] %d paths ditemukan untuk %s", len(paths), entity_names)
    return paths


def _find_paths_between_entities(session, entity_names: list[str], max_depth: int) -> list[dict]:
    """Find paths connecting any pair of entities."""
    query = """
        MATCH path = (start:Entity)-[:PREREQUISITE_FOR|REQUIRES|PART_OF|GOVERNS*1..$max_depth]-(end:Entity)
        WHERE start.name IN $entities AND end.name IN $entities AND start.name < end.name
        RETURN
            [node IN nodes(path) | node.name] AS node_names,
            [rel IN relationships(path) | type(rel)] AS rel_types,
            length(path) AS depth
        ORDER BY depth ASC
        LIMIT 10
    """
    result = session.run(query, entities=entity_names, max_depth=max_depth)
    return [
        {
            "path": record["node_names"],
            "relationships": record["rel_types"],
            "depth": record["depth"],
        }
        for record in result
    ]


def _find_paths_from_entity(session, entity_name: str, max_depth: int) -> list[dict]:
    """Find all paths radiating from a single entity."""
    query = """
        MATCH path = (start:Entity {name: $entity})-[rels:PREREQUISITE_FOR|REQUIRES|PART_OF|GOVERNS*1..$max_depth]-(end:Entity)
        RETURN
            [node IN nodes(path) | node.name] AS node_names,
            [rel IN relationships(path) | type(rel)] AS rel_types,
            length(path) AS depth
        ORDER BY depth ASC
        LIMIT 20
    """
    result = session.run(query, entity=entity_name, max_depth=max_depth)
    return [
        {
            "path": record["node_names"],
            "relationships": record["rel_types"],
            "depth": record["depth"],
        }
        for record in result
    ]


def format_paths_for_context(paths: list[dict]) -> str:
    """
    Format graph paths menjadi konteks untuk LLM.

    Output:
    [GRAPH RELATIONS]
      Python --[PREREQUISITE_FOR]--> Data Analysis --[PREREQUISITE_FOR]--> Machine Learning
    """
    if not paths:
        return ""

    lines = ["[GRAPH RELATIONS]"]
    seen = set()

    for p in paths:
        path_names = p.get("path", [])
        rel_types = p.get("relationships", [])
        if len(path_names) < 2:
            continue

        parts = []
        for i in range(len(path_names) - 1):
            rel = rel_types[i] if i < len(rel_types) else "RELATES_TO"
            parts.append(f"{path_names[i]} --[{rel}]--> {path_names[i+1]}")

        line = " | ".join(parts)
        if line not in seen:
            seen.add(line)
            lines.append(f"  {line}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)
