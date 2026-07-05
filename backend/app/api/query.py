"""
Query API — EnterpriseMind AI.

Endpoint utama untuk menerima pertanyaan pengguna dan memprosesnya
melalui multi-agent graph.

Ref: FR2.1 di SRS_PRD.md, A.3.3 (endpoint /query)

Endpoints:
    POST /api/query — Kirim pertanyaan ke sistem multi-agent
"""

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.auth import get_current_user
from app.db import log_query, save_message
from app.graph.build_graph import build_agent_graph
from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])
limiter = Limiter(key_func=get_remote_address)

# Build graph sekali saat module di-import
_agent_graph = None


def _get_graph():
    """Lazy initialization graph — build sekali, pakai berulang."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


# ------------------------------------------------------------------ #
# Request / Response Models
# ------------------------------------------------------------------ #


class QueryRequest(BaseModel):
    """Request body untuk /api/query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Pertanyaan pengguna dalam bahasa natural.",
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID sesi percakapan. Auto-generated jika tidak dikirim.",
    )


class CitationResponse(BaseModel):
    """Satu item sitasi."""

    source: str = ""
    date: str = ""
    excerpt: str = ""
    relevance_score: float = 0.0


class ActionItemResponse(BaseModel):
    """Satu item action."""

    action_type: str = ""
    draft_content: str = ""
    requires_human_review: bool = True


class QueryResponse(BaseModel):
    """Response body untuk /api/query."""

    answer: str
    citations: list[dict] = []
    action_items: list[dict] = []
    confidence_score: float = 0.0
    intent: str = ""
    reflection_count: int = 0
    latency_ms: int = 0
    session_id: str = ""


# ------------------------------------------------------------------ #
# Endpoint
# ------------------------------------------------------------------ #


@router.post("/query", response_model=QueryResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_query(
    request: Request,
    body: QueryRequest,
    user: dict = Depends(get_current_user),
) -> QueryResponse:
    """
    Terima pertanyaan user, proses lewat agent graph, kembalikan jawaban.

    Rate limited sesuai SECURITY.md #4 untuk melindungi kuota API Groq.

    Args:
        request: FastAPI Request (untuk rate limiter).
        body: QueryRequest dengan query dan session_id.

    Returns:
        QueryResponse dengan jawaban, sitasi, action items, dan metrik.

    Raises:
        HTTPException 500: Jika proses query gagal.
        HTTPException 429: Jika rate limit terlampaui.
    """
    start_time = time.time()

    logger.info(
        "[Query API] Diterima: query='%s...', session=%s",
        body.query[:80],
        body.session_id,
    )

    try:
        graph = _get_graph()

        # Initial state
        initial_state = {
            "query": body.query,
            "session_id": body.session_id,
            "intent": "",
            "agents_to_activate": [],
            "orchestrator_reasoning": "",
            "retrieved_documents": [],
            "reformulated_query": "",
            "verified_claims": [],
            "flagged_issues": [],
            "confidence_score": 0.0,
            "needs_reflection": False,
            "reflection_count": 0,
            "final_answer": "",
            "citations": [],
            "action_items": [],
            "conversation_history": [],
            "error": None,
        }

        # Run graph
        result = graph.invoke(initial_state)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Log query untuk metrik dashboard (FR7.1)
        try:
            await log_query(
                query=body.query,
                intent=result.get("intent", ""),
                agents_activated=result.get("agents_to_activate", []),
                latency_ms=elapsed_ms,
                confidence_score=result.get("confidence_score", 0),
                reflection_count=result.get("reflection_count", 0),
                model_used=settings.REASONING_MODEL,
            )
        except Exception as e:
            logger.warning("Gagal log query ke Supabase: %s", e)

        logger.info(
            "[Query API] Selesai: intent=%s, confidence=%.2f, "
            "latency=%dms, reflections=%d",
            result.get("intent", ""),
            result.get("confidence_score", 0),
            elapsed_ms,
            result.get("reflection_count", 0),
        )

        # Ensure conversation record exists and save messages
        try:
            client = get_supabase_client()

            # Check if conversation exists
            conv_result = (
                client.table("conversations")
                .select("id")
                .eq("session_id", body.session_id)
                .execute()
            )

            if conv_result.data:
                conversation_id = conv_result.data[0]["id"]
            else:
                # Create new conversation
                title = body.query[:60] + ("..." if len(body.query) > 60 else "")
                conv_insert = (
                    client.table("conversations")
                    .insert({
                        "session_id": body.session_id,
                        "user_id": user["id"],
                        "title": title,
                    })
                    .execute()
                )
                conversation_id = conv_insert.data[0]["id"]

            # Save user message
            await save_message(
                conversation_id=conversation_id,
                role="user",
                content=body.query,
            )

            # Save assistant message
            await save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.get("final_answer", ""),
                citations=result.get("citations", []),
                confidence_score=result.get("confidence_score", 0),
                action_items=result.get("action_items", []),
                latency_ms=elapsed_ms,
                model_used=settings.REASONING_MODEL,
            )
        except Exception as e:
            logger.warning("Gagal menyimpan pesan ke DB: %s", e)

        return QueryResponse(
            answer=result.get("final_answer", "Maaf, gagal memproses pertanyaan."),
            citations=result.get("citations", []),
            action_items=result.get("action_items", []),
            confidence_score=result.get("confidence_score", 0),
            intent=result.get("intent", ""),
            reflection_count=result.get("reflection_count", 0),
            latency_ms=elapsed_ms,
            session_id=body.session_id,
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.exception("[Query API] Error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses pertanyaan: {str(e)}",
        ) from e
