"""
Query API — EnterpriseMind AI.

POST /api/query — Send question to multi-agent system. SSE streaming response.
RBAC: Injects user profile filter for document retrieval.
"""
import logging
import time
import uuid

import asyncio
import json
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.auth import get_current_user, get_user_rbac_filter
from app.core.postgres_client import fetch_one, fetch_all, execute_query
from app.db import log_query, save_message
from app.graph.build_graph import build_agent_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])
limiter = Limiter(key_func=get_remote_address)

_agent_graph = None


def _get_graph():
    """Lazy init — build once, reuse."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict] = []
    action_items: list[dict] = []
    confidence_score: float = 0.0
    intent: str = ""
    reflection_count: int = 0
    latency_ms: int = 0
    session_id: str = ""


@router.post("/query")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_query(
    request: Request,
    body: QueryRequest,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Process query through agent graph. Returns SSE stream. RBAC-aware."""
    async def event_generator():
        start_time = time.time()

        try:
            graph = _get_graph()

            # RBAC filter from user profile
            rbac_filter = get_user_rbac_filter(user)

            initial_state = {
                "query": body.query,
                "session_id": body.session_id,
                "user_id": str(user["id"]),
                "user_department": user.get("department", "") or "",
                "user_clearance_level": user.get("clearance_level", 1) or 1,
                "rbac_filter": rbac_filter,
                "intent": "",
                "intent_type": "",
                "intent_confidence": 0.0,
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
                "graph_context": "",
                "error": None,
                "query_deadline": time.time() + settings.QUERY_TIMEOUT_SECONDS,
            }

            current_state = initial_state.copy()
            logger.info("[Query] Starting graph.astream for query: '%s...'", body.query[:60])

            queue = asyncio.Queue()

            async def run_graph():
                try:
                    node_count = 0
                    async for output in graph.astream(initial_state):
                        node_count += 1
                        for node_name, state_update in output.items():
                            logger.info("[Query] graph.astream yielded node #%d: %s", node_count, node_name)
                            current_state.update(state_update)
                            await queue.put({"type": "agent", "agent": node_name})
                    logger.info("[Query] graph.astream completed. Total nodes: %d", node_count)
                    await queue.put({"type": "done"})
                except asyncio.CancelledError:
                    logger.info("[Query] Graph execution cancelled by client disconnect.")
                    await queue.put({"type": "cancelled"})
                except Exception as e:
                    logger.exception("[Query] Graph execution failed")
                    await queue.put({"type": "error", "message": str(e)})

            # Jalankan graph di background
            graph_task = asyncio.create_task(run_graph())

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("[Query] Client disconnected, cancelling graph task...")
                    graph_task.cancel()
                    try:
                        await graph_task
                    except asyncio.CancelledError:
                        logger.info("[Query] Graph task cancelled successfully.")
                    return

                try:
                    # Tunggu maksimal 10 detik untuk pesan dari graph
                    msg = await asyncio.wait_for(queue.get(), timeout=10.0)
                    
                    if msg["type"] == "done":
                        break
                    elif msg["type"] == "cancelled":
                        logger.info("[Query] Graph cancelled, stopping event generator.")
                        return
                    elif msg["type"] == "error":
                        raise RuntimeError(msg["message"])
                    elif msg["type"] == "agent":
                        yield f"data: {json.dumps(msg)}\n\n"
                        
                except asyncio.TimeoutError:
                    # Sudah 10 detik tidak ada aktivitas (misal Researcher butuh 100s)
                    # Kirim heartbeat agar koneksi Proxy Next.js tidak terputus (Timeout)
                    logger.info("[Query] Mengirim heartbeat ke frontend...")
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Skip DB operations if graph was cancelled (client disconnected)
            if graph_task.cancelled():
                logger.info("[Query] Skipping DB save — query was cancelled.")
                return

            # Log query
            try:
                await log_query(
                    query=body.query, intent=current_state.get("intent", ""),
                    agents_activated=current_state.get("agents_to_activate", []),
                    latency_ms=elapsed_ms, confidence_score=current_state.get("confidence_score", 0),
                    reflection_count=current_state.get("reflection_count", 0),
                    model_used=settings.GROQ_MODEL_REASONING,
                )
            except Exception as e:
                logger.warning("Gagal log query: %s", e)

            # Save conversation
            try:
                title = body.query[:60] + ("..." if len(body.query) > 60 else "")

                # Check if conversation exists
                conv = await fetch_one(
                    "SELECT id FROM conversations WHERE session_id = $1",
                    body.session_id,
                )

                if conv:
                    conversation_id = str(conv["id"])
                else:
                    conv = await fetch_one(
                        "INSERT INTO conversations (session_id, user_id, title) VALUES ($1, $2, $3) RETURNING id",
                        body.session_id, str(user["id"]), title,
                    )
                    conversation_id = str(conv["id"])

                await save_message(conversation_id=conversation_id, role="user", content=body.query)
                await save_message(
                    conversation_id=conversation_id, role="assistant",
                    content=current_state.get("final_answer", ""),
                    citations=current_state.get("citations", []),
                    confidence_score=current_state.get("confidence_score", 0),
                    action_items=current_state.get("action_items", []),
                    latency_ms=elapsed_ms, model_used=settings.GROQ_MODEL_REASONING,
                )
            except Exception as e:
                logger.warning("Gagal menyimpan pesan ke DB: %s", e)

            final_answer = current_state.get("final_answer") or "Maaf, gagal memproses pertanyaan."
            final_response = {
                "type": "result", "answer": final_answer,
                "citations": current_state.get("citations", []),
                "action_items": current_state.get("action_items", []),
                "confidence_score": current_state.get("confidence_score", 0),
                "intent": current_state.get("intent", ""),
                "reflection_count": current_state.get("reflection_count", 0),
                "latency_ms": elapsed_ms, "session_id": body.session_id,
            }
            yield f"data: {json.dumps(final_response)}\n\n"

        except Exception as e:
            logger.exception("[Query API] Error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
