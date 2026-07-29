"""Graph draft CRUD — PostgreSQL for draft-then-review."""

import json
import logging
from typing import Any

from app.core.postgres_client import execute_query, fetch_all, fetch_one

logger = logging.getLogger(__name__)


async def save_graph_draft(
    document_id: str,
    filename: str,
    draft_data: dict,
) -> dict[str, Any]:
    """Save graph extraction draft ke PostgreSQL."""
    query = """
        INSERT INTO graph_drafts (document_id, filename, draft_data)
        VALUES ($1, $2, $3)
        RETURNING id, document_id, filename, status, created_at
    """
    result = await fetch_one(
        query,
        document_id,
        filename,
        json.dumps(draft_data),
    )
    logger.info("[GraphDraft] Saved draft for '%s': %d entities, %d relationships",
                filename,
                len(draft_data.get("entities", [])),
                len(draft_data.get("relationships", [])))
    return result


async def get_pending_drafts() -> list[dict]:
    """Get all pending graph drafts."""
    query = """
        SELECT id, document_id, filename, draft_data, status, created_at
        FROM graph_drafts
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """
    return await fetch_all(query)


async def get_draft_by_id(draft_id: str) -> dict | None:
    """Get single draft by ID."""
    query = """
        SELECT id, document_id, filename, draft_data, status, created_at
        FROM graph_drafts
        WHERE id = $1
    """
    return await fetch_one(query, draft_id)


async def commit_graph_draft(draft_id: str, reviewer_id: str | None = None) -> bool:
    """
    Commit draft ke Neo4j.
    Baca draft_data dari PostgreSQL, insert ke Neo4j, update status.
    """
    draft = await get_draft_by_id(draft_id)
    if not draft:
        logger.warning("[GraphDraft] Draft %s tidak ditemukan", draft_id)
        return False

    from app.core.neo4j_client import get_neo4j

    draft_data = draft["draft_data"]
    if isinstance(draft_data, str):
        draft_data = json.loads(draft_data)

    driver = get_neo4j()

    with driver.session() as session:
        # Insert entities
        for ent in draft_data.get("entities", []):
            session.run(
                """
                MERGE (e:Entity {name: $name})
                SET e.type = $type
                """,
                name=ent["name"],
                type=ent["type"],
            )

        # Insert relationships
        for rel in draft_data.get("relationships", []):
            if rel["type"] == "MENTIONED_IN":
                session.run(
                    """
                    MATCH (e:Entity {name: $source})
                    MERGE (d:Document {id: $target})
                    MERGE (e)-[:MENTIONED_IN {context: $context}]->(d)
                    """,
                    source=rel["source"],
                    target=rel["target"],
                    context=rel.get("context", ""),
                )
            else:
                session.run(
                    """
                    MATCH (a:Entity {name: $source})
                    MATCH (b:Entity {name: $target})
                    MERGE (a)-[r:$rel_type {context: $context}]->(b)
                    """.replace("$rel_type", rel["type"]),
                    source=rel["source"],
                    target=rel["target"],
                    context=rel.get("context", ""),
                )

    # Update status
    await execute_query(
        "UPDATE graph_drafts SET status = 'committed', reviewed_at = NOW() WHERE id = $1",
        draft_id,
    )

    logger.info("[GraphDraft] Draft %s committed to Neo4j: %d entities, %d relationships",
                draft_id,
                len(draft_data.get("entities", [])),
                len(draft_data.get("relationships", [])))
    return True


async def reject_graph_draft(draft_id: str) -> bool:
    """Reject draft (hapus atau set status rejected)."""
    await execute_query(
        "UPDATE graph_drafts SET status = 'rejected', reviewed_at = NOW() WHERE id = $1",
        draft_id,
    )
    logger.info("[GraphDraft] Draft %s rejected", draft_id)
    return True
