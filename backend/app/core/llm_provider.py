"""
LLM Provider — EnterpriseMind AI.

Groq provider — fast LPU inference.
Dua model berdasarkan task:
- task_type="fast" → GROQ_MODEL_FAST (routing, intent, query expansion)
- task_type="reasoning" → GROQ_MODEL_REASONING (summarizer, verifier)
"""
import logging
import time

from langchain_groq import ChatGroq

from app.core.config import settings

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
            max_tokens = 1024

    logger.info(
        "Membuat LLM instance: model=%s, task_type=%s, temperature=%s, timeout=%ds",
        model, task_type, temp, request_timeout,
    )

    kwargs = {
        "model": model,
        "api_key": settings.GROQ_API_KEY,
        "temperature": temp,
        "timeout": request_timeout,
        "max_retries": 2,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatGroq(**kwargs)


def invoke_with_retry(chain, input_data: dict, max_retries: int = 3, base_delay: float = 1.0):
    """
    Invoke LLM chain dengan retry untuk handle quota/rate limit errors.

    Args:
        chain: LangChain chain to invoke
        input_data: Input data for the chain
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        LLM response

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            logger.info("[LLM] invoke attempt %d/%d starting...", attempt + 1, max_retries)
            t0 = time.time()
            result = chain.invoke(input_data)
            elapsed = time.time() - t0
            logger.info("[LLM] invoke attempt %d/%d completed in %.1fs", attempt + 1, max_retries, elapsed)
            return result
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            elapsed = time.time() - t0
            logger.warning("[LLM] invoke attempt %d/%d failed after %.1fs: %s", attempt + 1, max_retries, elapsed, error_msg[:200])

            # Check if it's a quota/rate limit error
            if "429" in error_msg or "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    "[LLM] Rate limit hit (attempt %d/%d), waiting %.1fs before retry...",
                    attempt + 1, max_retries, delay,
                )
                time.sleep(delay)
            else:
                # Not a rate limit error, don't retry
                raise

    # All retries exhausted
    logger.error("[LLM] All %d retries exhausted. Last error: %s", max_retries, last_exception)
    raise last_exception
