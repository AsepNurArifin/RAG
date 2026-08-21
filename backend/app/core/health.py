"""
Health checks — EnterpriseMind AI.

Memisahkan liveness (proses hidup) dan readiness (dependency siap).

Prinsip:
- Probe harus ringan, paralel, dan memiliki timeout pendek.
- Tidak memanggil LLM berbayar pada setiap probe.
- Tidak memicu inisialisasi model embedding/reranker besar.
- LangFuse bersifat optional; kegagalannya tidak membuat aplikasi down.
"""

import asyncio
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _probe_with_timeout(name: str, coro, timeout: float = 5.0) -> dict:
    t0 = time.time()
    try:
        await asyncio.wait_for(coro, timeout=timeout)
        return {"status": "up", "latency_ms": int((time.time() - t0) * 1000)}
    except asyncio.TimeoutError:
        return {"status": "down", "latency_ms": int((time.time() - t0) * 1000), "error": "timeout"}
    except Exception as e:
        return {"status": "down", "latency_ms": int((time.time() - t0) * 1000), "error": str(e)[:200]}


async def check_postgres() -> dict:
    async def _probe():
        from app.core.postgres_client import fetch_val
        await fetch_val("SELECT 1")
    return await _probe_with_timeout("postgres", _probe())


async def check_milvus() -> dict:
    async def _probe():
        from pymilvus import connections, utility
        if not connections.has_connection("default"):
            connections.connect(alias="default", uri=settings.MILVUS_URI)
        utility.list_collections()
    return await _probe_with_timeout("milvus", _probe())


async def check_minio() -> dict:
    async def _probe():
        from app.core.minio_client import minio_client
        await asyncio.to_thread(minio_client.client.bucket_exists, settings.MINIO_BUCKET_DOCS)
    return await _probe_with_timeout("minio", _probe())


async def check_temporal() -> dict:
    async def _probe():
        from app.temporal.client import get_temporal_client
        client = await get_temporal_client()
        await client.service_client.check_health()
    return await _probe_with_timeout("temporal", _probe())


async def check_docling() -> dict:
    async def _probe():
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.DOCLING_URL}/health")
            resp.raise_for_status()
    return await _probe_with_timeout("docling", _probe())


def check_llm_config() -> dict:
    """Cek konfigurasi LLM tanpa melakukan request berbayar."""
    if settings.GROQ_API_KEY:
        return {"status": "up", "detail": "api_key_configured"}
    return {"status": "down", "detail": "api_key_missing"}


def check_langfuse_config() -> dict:
    if not settings.LANGFUSE_ENABLED:
        return {"status": "disabled", "detail": "not_enabled"}
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_HOST):
        return {"status": "degraded", "detail": "enabled_but_credentials_missing"}
    return {"status": "up", "detail": "configured"}


async def readiness() -> dict:
    """Jalankan probe dependency secara paralel."""
    postgres, milvus, minio, temporal = await asyncio.gather(
        check_postgres(),
        check_milvus(),
        check_minio(),
        check_temporal(),
    )
    docling = await check_docling()
    llm = check_llm_config()
    langfuse = check_langfuse_config()

    critical = {
        "postgres": postgres,
        "milvus": milvus,
        "minio": minio,
        "temporal": temporal,
    }
    optional = {
        "docling": docling,
        "llm": llm,
        "langfuse": langfuse,
    }

    critical_down = [k for k, v in critical.items() if v.get("status") != "up"]
    optional_down = [k for k, v in optional.items() if v.get("status") == "down"]

    status = "ready"
    if critical_down:
        status = "unavailable"
    elif optional_down:
        status = "degraded"

    return {
        "status": status,
        "dependencies": {**critical, **optional},
        "critical_down": critical_down,
        "optional_down": optional_down,
    }
