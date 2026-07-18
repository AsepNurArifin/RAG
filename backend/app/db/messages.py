"""Message CRUD operations — PostgreSQL."""
import logging
from typing import Any

from app.core.postgres_client import fetch_one

logger = logging.getLogger(__name__)


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    confidence_score: float | None = None,
    action_items: list[dict] | None = None,
    latency_ms: int | None = None,
    model_used: str | None = None,
) -> dict[str, Any]:
    """Save message to conversation history."""
    import json

    query = """
        INSERT INTO messages (conversation_id, role, content, citations, confidence_score,
                              action_items, latency_ms, model_used)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, conversation_id, role, content, created_at
    """
    result = await fetch_one(
        query,
        conversation_id,
        role,
        content,
        json.dumps(citations or []),
        confidence_score,
        json.dumps(action_items or []),
        latency_ms,
        model_used,
    )
    return result
