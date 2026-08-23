"""
Unit Tests — LLM Provider retry classification.

Memastikan error 4xx permanen (413/400) tidak di-retry, sedangkan
429/5xx/network transient di-retry. Ini mencegah buang waktu & kuota
ketika payload terlalu besar (TPM) atau request invalid.
"""

import httpx
import pytest

from app.core.llm_provider import _is_retryable_error, _retry_after_delay


def _status_error(code: int, retry_after: str | None = None):
    headers = {}
    if retry_after:
        headers["Retry-After"] = retry_after
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(code, request=req, headers=headers)
    return httpx.HTTPStatusError(str(code), request=req, response=resp)


def test_413_payload_too_large_not_retryable():
    """413 (payload > TPM limit) adalah error permanen — tidak boleh retry."""
    err = _status_error(413)
    retryable, _ = _is_retryable_error(err)
    assert retryable is False


def test_400_not_retryable():
    err = _status_error(400)
    retryable, _ = _is_retryable_error(err)
    assert retryable is False


def test_429_rate_limit_retryable_with_delay():
    """429 di-retry, dan delay mengikuti Retry-After bila tersedia."""
    err = _status_error(429, retry_after="36")
    retryable, delay = _is_retryable_error(err)
    assert retryable is True
    assert delay >= 36.0


def test_500_server_error_retryable():
    err = _status_error(500)
    retryable, _ = _is_retryable_error(err)
    assert retryable is True


def test_network_timeout_retryable():
    err = httpx.ConnectTimeout("connect timeout", request=httpx.Request("GET", "https://x"))
    retryable, _ = _is_retryable_error(err)
    assert retryable is True
