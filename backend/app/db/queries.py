"""Query log operations for dashboard metrics — PostgreSQL."""
import json
import logging
from typing import Any

from app.core.postgres_client import fetch_one

logger = logging.getLogger(__name__)


async def log_query(
    query: str,
    intent: str | None = None,
    agents_activated: list[str] | None = None,
    latency_ms: int | None = None,
    confidence_score: float | None = None,
    reflection_count: int = 0,
    model_used: str | None = None,
    estimated_cost_usd: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    usage_details: dict | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    status: str = "completed",
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Log query untuk dashboard metrics + audit trail."""
    sql = """
        INSERT INTO query_logs (query, intent, agents_activated, latency_ms,
                                confidence_score, reflection_count, model_used,
                                estimated_cost_usd, input_tokens, output_tokens,
                                total_tokens, usage_details,
                                request_id, trace_id, status, session_id, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        RETURNING id, query, intent, created_at
    """
    result = await fetch_one(
        sql,
        query,
        intent,
        json.dumps(agents_activated or []),
        latency_ms,
        confidence_score,
        reflection_count,
        model_used,
        estimated_cost_usd,
        input_tokens,
        output_tokens,
        total_tokens,
        json.dumps(usage_details or {}),
        request_id,
        trace_id,
        status,
        session_id,
        user_id,
    )
    return result
