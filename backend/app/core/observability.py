"""
Observability — EnterpriseMind AI.

Terpusat untuk tracing (LangFuse optional) dan token/cost tracking.

Prinsip:
- LangFuse bersifat OPTIONAL dan NON-CRITICAL. Jika credential tidak ada,
  sistem berjalan dalam no-op mode (hanya logging lokal). Kegagalan
  observability TIDAK boleh menggagalkan query.
- Semua secret TIDAK boleh masuk logger atau trace.
- Cost dihitung dari settings pricing (per 1M token).
"""

import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_trace_id_counter = 0
_usage_by_request: dict[str, dict] = {}


def _trace_id() -> str:
    global _trace_id_counter
    _trace_id_counter += 1
    return f"trace_{int(time.time() * 1000)}_{_trace_id_counter}"


class ObservabilityClient:
    """No-op by default. LangFuse diaktifkan jika LANGFUSE_ENABLED dan credential ada."""

    def __init__(self) -> None:
        self._langfuse = None
        self._enabled = False
        self._init_langfuse()

    def _init_langfuse(self) -> None:
        if not settings.LANGFUSE_ENABLED:
            logger.info("LangFuse disabled (LANGFUSE_ENABLED=false).")
            return
        if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_HOST):
            logger.warning("LANGFUSE_ENABLED=true tapi credential tidak lengkap. Mode no-op.")
            return
        try:
            from langfuse import Langfuse
            self._langfuse = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            self._enabled = True
            logger.info("LangFuse client aktif: host=%s", settings.LANGFUSE_HOST)
        except Exception as e:
            logger.warning("Gagal inisialisasi LangFuse: %s. Mode no-op.", e)
            self._langfuse = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled and self._langfuse is not None


_observability_client: ObservabilityClient | None = None


def get_observability_client() -> ObservabilityClient:
    global _observability_client
    if _observability_client is None:
        _observability_client = ObservabilityClient()
    return _observability_client


def _start_trace_if_enabled(observability: ObservabilityClient, name: str, meta: dict):
    if observability.enabled:
        try:
            return observability._langfuse.trace(name=name, metadata=meta or None)
        except Exception as e:
            logger.warning("LangFuse trace start gagal: %s", e)
    return None


def _start_generation_if_enabled(observability: ObservabilityClient, trace, name: str, meta: dict):
    if observability.enabled and trace is not None:
        try:
            return trace.generation(name=name, metadata=meta or None)
        except Exception as e:
            logger.warning("LangFuse generation start gagal: %s", e)
    return None


def _end_generation_if_enabled(observability: ObservabilityClient, generation, meta: dict):
    if observability.enabled and generation is not None:
        try:
            generation.end(output=meta.get("output"), metadata=meta.get("metadata") or None)
        except Exception as e:
            logger.warning("LangFuse generation end gagal: %s", e)


def start_query_trace(meta: dict | None = None):
    """Mulai trace untuk satu query."""
    observability = get_observability_client()
    return _start_trace_if_enabled(observability, "query", meta)


def start_generation(trace, name: str, meta: dict | None = None):
    """Mulai generation span (LLM call)."""
    observability = get_observability_client()
    return _start_generation_if_enabled(observability, trace, name, meta or {})


def end_generation(generation, output: Any = None, meta: dict | None = None):
    """Akhiri generation span."""
    observability = get_observability_client()
    _end_generation_if_enabled(observability, generation, {"output": output, "metadata": meta})


def flush() -> None:
    """Flush semua event LangFuse. Never raises."""
    observability = get_observability_client()
    if observability.enabled and observability._langfuse is not None:
        try:
            observability._langfuse.flush()
        except Exception as e:
            logger.warning("LangFuse flush gagal: %s", e)


# ------------------------------------------------------------------ #
# Usage / Cost tracking
# ------------------------------------------------------------------ #


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimasi biaya query berdasarkan pricing config."""
    cost_input = input_tokens * settings.LLM_INPUT_COST_PER_MILLION_TOKENS / 1_000_000
    cost_output = output_tokens * settings.LLM_OUTPUT_COST_PER_MILLION_TOKENS / 1_000_000
    return round(cost_input + cost_output, 6)


def extract_usage_metadata(response: Any) -> dict:
    """
    Ekstrak token usage dari response LangChain AIMessage.

    Mengembalikan dict dengan input/output/total token bila tersedia,
    atau {} bila provider tidak memberikan info usage.
    """
    if response is None:
        return {}

    usage = {}
    try:
        resp_meta = getattr(response, "response_metadata", None) or {}
        usage_meta = resp_meta.get("token_usage") or resp_meta.get("usage") or {}
        if isinstance(usage_meta, dict):
            usage["input_tokens"] = int(usage_meta.get("prompt_tokens") or usage_meta.get("input_tokens") or 0)
            usage["output_tokens"] = int(usage_meta.get("completion_tokens") or usage_meta.get("output_tokens") or 0)
    except Exception:
        usage = {}

    if usage and (usage.get("input_tokens") or usage.get("output_tokens")):
        usage["total_tokens"] = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        usage["estimated_cost_usd"] = estimate_cost_usd(
            usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        )
        return usage
    return {}


def accumulate_usage(usage_meta: dict, response: Any) -> dict:
    """Tambahkan usage dari response ke aggregate per-request."""
    extracted = extract_usage_metadata(response)
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        usage_meta[key] = usage_meta.get(key, 0) + extracted.get(key, 0)
    if extracted.get("estimated_cost_usd"):
        usage_meta["estimated_cost_usd"] = round(
            usage_meta.get("estimated_cost_usd", 0.0) + extracted["estimated_cost_usd"], 6
        )
    if "generations" not in usage_meta:
        usage_meta["generations"] = []
    usage_meta["generations"].append(extracted)
    return usage_meta
