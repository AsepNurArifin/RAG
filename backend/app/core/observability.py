"""
Observability — EnterpriseMind AI.

Setup LangFuse callback handler untuk tracing setiap agent call
dan tool call. Ref: ADR-006, CODING_STANDARDS.md (setiap agent/tool
call WAJIB ter-trace di LangFuse).

Usage:
    from app.core.observability import get_langfuse_handler

    # Dalam agent function
    handler = get_langfuse_handler(trace_name="researcher_agent")
    llm.invoke(prompt, config={"callbacks": [handler]})
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse_handler = None


def get_langfuse_handler(
    trace_name: str = "enterprisemind",
    user_id: str | None = None,
    session_id: str | None = None,
):
    """
    Buat LangFuse callback handler untuk LangChain.

    Args:
        trace_name: Nama trace untuk identifikasi di LangFuse dashboard.
        user_id: Opsional — ID pengguna untuk menghubungkan trace ke user.
        session_id: Opsional — ID sesi untuk mengelompokkan trace.

    Returns:
        CallbackHandler LangFuse, atau None jika LangFuse tidak dikonfigurasi.

    Side effects:
        Membuat koneksi ke LangFuse server pada pemanggilan pertama.
    """
    global _langfuse_handler
    if _langfuse_handler is not None:
        return _langfuse_handler

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning(
            "LangFuse credentials belum di-set. "
            "Tracing dinonaktifkan. Set LANGFUSE_PUBLIC_KEY dan "
            "LANGFUSE_SECRET_KEY di .env untuk mengaktifkan."
        )
        return None

    try:
        from langfuse.callback import CallbackHandler

        _langfuse_handler = CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            trace_name=trace_name,
            user_id=user_id,
            session_id=session_id,
        )
        logger.debug(
            "LangFuse handler dibuat: trace_name=%s, host=%s",
            trace_name,
            settings.LANGFUSE_HOST,
        )
        return _langfuse_handler

    except Exception:
        logger.exception("Gagal membuat LangFuse handler")
        return None


def get_callbacks(
    trace_name: str = "enterprisemind",
    user_id: str | None = None,
    session_id: str | None = None,
) -> list:
    """
    Dapatkan list callback handlers untuk digunakan dalam LangChain calls.

    Convenience function yang mengembalikan list (bukan single handler)
    agar bisa langsung dipakai di config={"callbacks": get_callbacks(...)}.

    Returns:
        List berisi LangFuse handler jika tersedia, atau list kosong.
    """
    handler = get_langfuse_handler(trace_name, user_id, session_id)
    return [handler] if handler is not None else []
