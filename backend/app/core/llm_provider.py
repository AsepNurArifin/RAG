"""
LLM Provider Factory — EnterpriseMind AI.

Factory function untuk membuat instance LLM berdasarkan tipe task.
Mengabstraksi provider (Groq) agar mudah diganti jika terjadi
deprecation model (ref: ADR-001, ARCHITECTURE.md prinsip #1).

Usage:
    from app.core.llm_provider import get_llm

    llm_fast = get_llm("fast")        # untuk routing, ekstraksi
    llm_reasoning = get_llm("reasoning")  # untuk verifikasi, sintesis
"""

import logging

from langchain_groq import ChatGroq

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm(
    task_type: str = "fast",
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> ChatGroq:
    """
    Buat instance ChatGroq berdasarkan tipe task.

    Args:
        task_type: Tipe task — "fast" (routing, ekstraksi) atau
                   "reasoning" (verifikasi, sintesis). Default "fast"
                   untuk efisiensi biaya (ref: ARCHITECTURE.md Constraints).
        temperature: Temperature untuk generasi. Default 0.1 untuk
                     jawaban yang konsisten.
        max_tokens: Maksimal token output. None = gunakan default model.

    Returns:
        Instance ChatGroq yang sudah dikonfigurasi.

    Raises:
        ValueError: Jika task_type tidak dikenali.

    Side effects:
        Tidak ada. Instance belum melakukan API call sampai dipanggil.
    """
    model_map = {
        "fast": settings.FAST_MODEL,
        "reasoning": settings.REASONING_MODEL,
    }

    model_name = model_map.get(task_type)
    if model_name is None:
        raise ValueError(
            f"task_type '{task_type}' tidak dikenali. "
            f"Gunakan salah satu: {list(model_map.keys())}"
        )

    logger.info(
        "Membuat LLM instance: model=%s, task_type=%s, temperature=%s",
        model_name,
        task_type,
        temperature,
    )

    kwargs: dict = {
        "model": model_name,
        "api_key": settings.GROQ_API_KEY,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatGroq(**kwargs)
