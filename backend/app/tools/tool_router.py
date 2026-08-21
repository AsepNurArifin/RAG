"""
Tool Router — EnterpriseMind AI.

Node deterministic yang memutuskan apakah query butuh tool:
- calculator: ekspresi matematika
- metadata: pertanyaan daftar/status dokumen

WEB SEARCH TIDAK ADA — kebijakan PT internal melarang sistem melakukan
pencarian ke internet. Batas ini diberlakukan di level kode.
"""

import logging
import re
import time

from app.core.config import settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# Pola deteksi ekspresi matematika: hanya angka + operator yang diizinkan
_CALC_RE = re.compile(r"^[\d\s+\-*/().%^]+$")

# Kata kunci untuk pertanyaan metadata dokumen
_METADATA_KEYWORDS = (
    "dokumen apa saja", "daftar dokumen", "list dokumen", "dokumen yang ada",
    "berapa banyak dokumen", "jumlah dokumen", "dokumen kategori",
    "what documents", "list of documents", "how many documents",
    "apakah ada dokumen", "cek dokumen", "status dokumen",
)


def _looks_like_calculation(query: str) -> bool:
    stripped = query.strip().lower()
    if len(stripped) < 2 or len(stripped) > 500:
        return False
    # Harus angka/operator, minimal ada 1 angka
    if not _CALC_RE.match(stripped):
        return False
    return any(ch.isdigit() for ch in stripped)


def _looks_like_metadata_query(query: str) -> bool:
    lowered = query.lower().strip()
    return any(kw in lowered for kw in _METADATA_KEYWORDS)


def run_tool_node(state: GraphState) -> GraphState:
    """Jalankan tool yang relevan berdasarkan query dan simpan hasilnya."""
    query = state.get("query", "")
    tool_results = list(state.get("tool_results", []) or [])

    try:
        if _looks_like_calculation(query):
            if not settings.ENABLE_CALCULATOR:
                tool_results.append({"name": "calculator", "status": "disabled", "output": ""})
            else:
                from app.tools.calculator_tool import calculate
                t0 = time.time()
                output = calculate(query)
                tool_results.append({
                    "name": "calculator",
                    "input": query,
                    "output": output,
                    "status": "success" if not output.startswith("Error") else "error",
                    "latency_ms": int((time.time() - t0) * 1000),
                })
        elif _looks_like_metadata_query(query):
            if not settings.ENABLE_METADATA_TOOL:
                tool_results.append({"name": "metadata", "status": "disabled", "output": []})
            else:
                from app.tools.metadata_query_tool import query_document_metadata
                t0 = time.time()
                # run_tool_node dieksekusi di thread (via asyncio.to_thread),
                # sehingga aman memakai asyncio.run di sini.
                import asyncio
                output = asyncio.run(query_document_metadata())
                status = "error" if (isinstance(output, list) and output and "error" in output[0]) else "success"
                tool_results.append({
                    "name": "metadata",
                    "input": query,
                    "output": output,
                    "status": status,
                    "latency_ms": int((time.time() - t0) * 1000),
                })
    except Exception as e:
        logger.warning("[ToolRouter] Error saat menjalankan tool: %s", e)
        tool_results.append({"name": "unknown", "status": "error", "output": str(e)[:200]})

    if tool_results:
        logger.info("[ToolRouter] %d tool result(s) untuk query '%s...'", len(tool_results), query[:40])

    return {**state, "tool_results": tool_results}

