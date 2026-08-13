"""
Core — EnterpriseMind AI.

Re-export auth utilities and config.
"""
from app.core.config import settings
from app.core.llm_provider import get_llm

__all__ = [
    "settings",
    "get_llm",
]
