"""
Metrics API — EnterpriseMind AI.

Endpoint untuk dashboard admin (FR7.1).
Mengambil agregasi data performa (latency, cost, intent distribution).

Endpoints:
    GET /api/metrics — Metrik performa sistem
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_admin
from app.core.postgres_client import fetch_all, fetch_val

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Metrics"])


@router.get("/metrics")
async def get_dashboard_metrics(admin: dict = Depends(require_admin)) -> dict:
    """Hitung dan kembalikan metrik dashboard utama."""
    try:
        # Aggregation queries (more efficient than fetching all rows)
        total_queries = await fetch_val("SELECT COUNT(*) FROM query_logs")

        if not total_queries or total_queries == 0:
            return _empty_metrics()

        avg_latency = await fetch_val("SELECT COALESCE(AVG(latency_ms), 0) FROM query_logs")
        avg_confidence = await fetch_val("SELECT COALESCE(AVG(confidence_score), 0) FROM query_logs")
        total_cost = await fetch_val("SELECT COALESCE(SUM(estimated_cost_usd), 0) FROM query_logs")

        # Reflection rate
        reflection_count = await fetch_val("SELECT COUNT(*) FROM query_logs WHERE reflection_count > 0")
        reflection_rate = (reflection_count / total_queries) * 100 if total_queries > 0 else 0

        # Intent distribution
        intent_rows = await fetch_all(
            "SELECT intent, COUNT(*) as count FROM query_logs GROUP BY intent ORDER BY count DESC"
        )
        intents = {row["intent"] or "unknown": row["count"] for row in intent_rows}

        # Recent logs
        recent_logs = await fetch_all(
            "SELECT id, query, intent, latency_ms, confidence_score, reflection_count, model_used, created_at "
            "FROM query_logs ORDER BY created_at DESC LIMIT 10"
        )

        # Total documents
        total_documents = await fetch_val("SELECT COUNT(*) FROM documents")

        return {
            "total_queries": total_queries,
            "avg_latency_ms": int(avg_latency),
            "avg_confidence_score": round(float(avg_confidence), 2),
            "total_estimated_cost_usd": round(float(total_cost), 4),
            "reflection_rate_percentage": round(reflection_rate, 1),
            "intent_distribution": intents,
            "total_documents": total_documents,
            "recent_logs": recent_logs,
        }

    except Exception as e:
        logger.exception("Gagal mengambil metrik")
        raise HTTPException(status_code=500, detail=str(e))


def _empty_metrics() -> dict:
    return {
        "total_queries": 0,
        "avg_latency_ms": 0,
        "avg_confidence_score": 0.0,
        "total_estimated_cost_usd": 0.0,
        "reflection_rate_percentage": 0.0,
        "intent_distribution": {},
        "total_documents": 0,
        "recent_logs": [],
    }
