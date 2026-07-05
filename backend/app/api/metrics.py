"""
Metrics API — EnterpriseMind AI.

Endpoint untuk dashboard admin (FR7.1).
Mengambil agregasi data performa (latency, cost, intent distribution).

Endpoints:
    GET /api/metrics — Metrik performa sistem
"""

import logging

from fastapi import APIRouter, HTTPException

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Metrics"])


@router.get("/metrics")
async def get_dashboard_metrics() -> dict:
    """
    Hitung dan kembalikan metrik dashboard utama.
    """
    try:
        client = get_supabase_client()
        
        # Ambil data dari query_logs
        # (Dalam skala besar, query agregasi SQL langsung lebih baik via RPC,
        # tapi untuk MVP kita tarik dan proses di Python)
        result = client.table("query_logs").select("*").execute()
        logs = result.data

        if not logs:
            return _empty_metrics()

        total_queries = len(logs)
        total_latency = sum(log.get("latency_ms") or 0 for log in logs)
        total_cost = sum(log.get("estimated_cost_usd") or 0 for log in logs)
        avg_confidence = sum(log.get("confidence_score") or 0 for log in logs) / total_queries
        
        # Hitung intent distribution
        intents = {}
        for log in logs:
            intent = log.get("intent") or "unknown"
            intents[intent] = intents.get(intent, 0) + 1

        # Hitung reflection rate
        reflections = sum(1 for log in logs if (log.get("reflection_count") or 0) > 0)
        reflection_rate = (reflections / total_queries) * 100

        return {
            "total_queries": total_queries,
            "avg_latency_ms": int(total_latency / total_queries),
            "avg_confidence_score": round(avg_confidence, 2),
            "total_estimated_cost_usd": round(total_cost, 4),
            "reflection_rate_percentage": round(reflection_rate, 1),
            "intent_distribution": intents,
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
    }
