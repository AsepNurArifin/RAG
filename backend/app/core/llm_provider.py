"""
LLM Provider — EnterpriseMind AI.

Groq provider — fast LPU inference.
Dua model berdasarkan task:
- task_type="fast" → GROQ_MODEL_FAST (routing, intent, query expansion)
- task_type="reasoning" → GROQ_MODEL_REASONING (summarizer, verifier)

Semua invoke LLM sebaiknya lewat invoke_with_retry() / invoke_llm_instrumented()
agar usage token & cost tercatat serta bisa di-trace (LangFuse optional).
"""
import logging
import time

from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.observability import (
    accumulate_usage,
    end_generation,
    start_generation,
)

logger = logging.getLogger(__name__)


def get_llm(
    task_type: str = "fast",
    temperature: float = 0.1,
    max_tokens: int | None = None,
    request_timeout: int = 60,
) -> ChatGroq:
    """
    Get Groq LLM instance.

    Args:
        task_type: "fast" (routing) atau "reasoning" (summarizer/verifier)
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
        request_timeout: HTTP request timeout in seconds (default 60s)
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak boleh kosong. Set di .env file.")

    # Pilih model berdasarkan task type
    if task_type == "reasoning":
        model = settings.GROQ_MODEL_REASONING
        temp = max(temperature, 0.4)
        if max_tokens is None:
            max_tokens = 4096
    else:
        model = settings.GROQ_MODEL_FAST
        temp = temperature
        if max_tokens is None:
            # gpt-oss-20b adalah model reasoning — sebagian token dipakai untuk
            # reasoning internal, jadi beri ruang cukup untuk jawaban aktual.
            max_tokens = 2048

    logger.info(
        "Membuat LLM instance: model=%s, task_type=%s, temperature=%s, timeout=%ds",
        model, task_type, temp, request_timeout,
    )

    kwargs = {
        "model": model,
        "api_key": settings.GROQ_API_KEY,
        "temperature": temp,
        "timeout": request_timeout,
        # Retry dimiliki oleh invoke_with_retry()/invoke_llm_instrumented()
        # (single owner), bukan client. Client internal me-retry 429/413 yang
        # justru membuang waktu & kuota untuk error permanen.
        "max_retries": 0,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatGroq(**kwargs)


def _is_retryable_error(error: Exception) -> tuple[bool, float]:
    """
    Klasifikasi error LLM: apakah layak retry, dan delay yang disarankan.

    Retryable:
        - 429 (rate limit) — hormati Retry-After jika tersedia
        - 5xx (server error) — transient
        - network/timeout/connection error — transient

    Non-retryable (jangan buang waktu & kuota):
        - 400, 401, 403, 404, 409, 413 (payload too large), 422
        - parsing/invalid request, context overflow
    """
    error_str = str(error)
    lower = error_str.lower()

    # Provider status errors (groq.APIStatusError, httpx.HTTPStatusError)
    status_code = getattr(error, "status_code", None)
    if status_code is None:
        response = getattr(error, "response", None)
        if response is not None:
            status_code = getattr(response, "status_code", None)
    if status_code is None:
        import re
        m = re.search(r"(\d{3})", error_str)
        if m:
            status_code = int(m.group(1))

    if status_code == 429:
        delay = _retry_after_delay(error)
        return True, delay
    if status_code is not None and 500 <= status_code < 600:
        return True, 1.0
    if status_code is not None:
        # 4xx selain 429 → permanen
        return False, 0.0

    # Tanpa status code: network/timeout → retryable
    import httpx
    if isinstance(error, (httpx.TransportError, httpx.TimeoutException, TimeoutError, ConnectionError)):
        return True, 1.0

    # Fallback berbasis string
    if "429" in error_str or "rate_limit" in lower or "quota" in lower:
        return True, _retry_after_delay(error)
    if any(tok in lower for tok in ("timeout", "connection", "network", "temporarily", "server error", "internal server")):
        return True, 1.0

    return False, 0.0


def _retry_after_delay(error: Exception) -> float:
    """Baca header Retry-After dari response bila tersedia."""
    response = getattr(error, "response", None)
    if response is not None:
        retry_after = response.headers.get("Retry-After") if getattr(response, "headers", None) else None
        if retry_after:
            try:
                return float(retry_after) + 0.5
            except ValueError:
                pass
    return 1.0


def invoke_with_retry(chain, input_data: dict, max_retries: int = 3, base_delay: float = 1.0, deadline: float | None = None):
    """
    Invoke LLM chain dengan retry cerdas untuk error transient.

    - Retry hanya untuk 429/5xx/network error.
    - 4xx permanen (400/401/403/404/413/422) langsung gagal, tidak di-retry.
    - Backoff exponential + jitter, menghormati Retry-After.
    - Jika deadline diberikan, hentikan retry ketika sisa waktu < delay.

    Args:
        chain: LangChain chain to invoke
        input_data: Input data for the chain
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds (doubles each retry)
        deadline: Timestamp (epoch) batas waktu query; None = tanpa batas.

    Returns:
        LLM response

    Raises:
        Last exception if all retries fail
    """
    import random

    last_exception = None

    for attempt in range(max_retries):
        t0 = time.time()
        try:
            logger.info("[LLM] invoke attempt %d/%d starting...", attempt + 1, max_retries)
            result = chain.invoke(input_data)
            elapsed = time.time() - t0
            logger.info("[LLM] invoke attempt %d/%d completed in %.1fs", attempt + 1, max_retries, elapsed)
            return result
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            elapsed = time.time() - t0
            logger.warning("[LLM] invoke attempt %d/%d failed after %.1fs: %s", attempt + 1, max_retries, elapsed, error_msg[:200])

            retryable, delay = _is_retryable_error(e)
            if not retryable:
                logger.warning("[LLM] Error non-retryable (status/permanent), tidak di-retry: %s", error_msg[:200])
                raise

            # Jitter: +-25% untuk mencegah thundering herd
            delay = delay * (0.75 + 0.5 * random.random())

            # Deadline-aware: jangan retry jika sisa waktu lebih kecil dari delay
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining < delay:
                    logger.warning("[LLM] Sisa deadline %.1fs < delay %.1fs, berhenti retry.", remaining, delay)
                    raise

            # Exponential backoff (attempt sudah termasuk retry pertama)
            effective_delay = max(delay, base_delay * (2 ** attempt)) if attempt > 0 else delay
            logger.warning(
                "[LLM] Rate limit/transient (attempt %d/%d), waiting %.1fs before retry...",
                attempt + 1, max_retries, effective_delay,
            )
            time.sleep(effective_delay)

    logger.error("[LLM] All %d retries exhausted. Last error: %s", max_retries, last_exception)
    raise last_exception


def invoke_llm_instrumented(
    chain,
    input_data: dict,
    agent_name: str = "llm",
    task_type: str = "reasoning",
    max_retries: int = 3,
    base_delay: float = 1.0,
    usage_meta: dict | None = None,
    trace=None,
    deadline: float | None = None,
) -> tuple[object, dict]:
    """
    Invoke LLM chain dengan retry + usage/cost tracking + optional tracing.

    Retry cerdas: hanya 429/5xx/network, tidak me-retry error permanen (413/400).
    Deadline-aware: berhenti retry ketika sisa waktu tidak cukup.

    Returns:
        (response, usage_meta) — usage_meta di-update in-place (aggregate).
    """
    import random

    if usage_meta is None:
        usage_meta = {}
    generation = start_generation(trace, name=f"llm_{agent_name}", meta={"task_type": task_type})

    last_exception = None
    result = None

    for attempt in range(max_retries):
        t0 = time.time()
        try:
            result = chain.invoke(input_data)
            elapsed = time.time() - t0
            logger.info("[LLM][%s] attempt %d/%d selesai dalam %.1fs", agent_name, attempt + 1, max_retries, elapsed)
            accumulate_usage(usage_meta, result)
            end_generation(generation, output=result.content if hasattr(result, "content") else result, meta={"status": "ok"})
            return result, usage_meta
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            logger.warning("[LLM][%s] attempt %d/%d gagal: %s", agent_name, attempt + 1, max_retries, error_msg[:200])

            retryable, delay = _is_retryable_error(e)
            if not retryable:
                logger.warning("[LLM][%s] Error non-retryable, berhenti: %s", agent_name, error_msg[:200])
                break

            delay = delay * (0.75 + 0.5 * random.random())
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining < delay:
                    logger.warning("[LLM][%s] Sisa deadline %.1fs < delay %.1fs, berhenti retry.", agent_name, remaining, delay)
                    break

            effective_delay = max(delay, base_delay * (2 ** attempt)) if attempt > 0 else delay
            logger.warning("[LLM][%s] Retry dalam %.1fs (attempt %d/%d)...", agent_name, effective_delay, attempt + 1, max_retries)
            time.sleep(effective_delay)

    end_generation(generation, output=None, meta={"status": "error", "error": str(last_exception)[:200]})
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("LLM invoke gagal tanpa exception.")
