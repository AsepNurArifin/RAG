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
from app.core import observability
from app.db import log_query, save_message
from app.db.messages import get_or_create_user_conversation, get_messages_for_session
from app.graph.build_graph import build_agent_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])
limiter = Limiter(key_func=get_remote_address)

_agent_graph = None

# Pesan error aman untuk user — detail teknis hanya ke log/Langfuse.
_SAFE_ERROR_MESSAGES = {
    "QUERY_TIMEOUT": ("Pemrosesan memakan waktu terlalu lama. Silakan coba lagi.", False),
    "LLM_FAILURE": ("Sistem sedang mengalami kendala saat memproses jawaban. Silakan coba lagi.", True),
    "SESSION_OWNERSHIP": ("Session ini milik user lain. Buat session baru.", False),
    "SERVER_ERROR": ("Terjadi kesalahan sistem. Silakan coba lagi.", True),
}


def _safe_error(code: str, detail: str) -> dict:
    message, retryable = _SAFE_ERROR_MESSAGES.get(code, _SAFE_ERROR_MESSAGES["SERVER_ERROR"])
    return {"type": "error", "code": code, "message": message, "retryable": retryable, "detail": detail[:200]}


def _get_graph():
    """Lazy init — build once, reuse."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


# Nama node graph yang dilaporkan ke frontend sebagai tracking agent.
# "tools" dan "reflection" dipetakan ulang di frontend (AGENT_ALIASES).
GRAPH_NODE_NAMES = frozenset(
    {"orchestrator", "tools", "researcher", "verifier", "summarizer", "executor", "reflection"}
)


def _lifecycle_node_name(event: dict) -> str | None:
    """Ambil nama node graph dari satu event ``astream_events`` bila event ini
    adalah start/end LEVEL NODE — bukan sub-chain/LLM di dalam node.

    Event level node memiliki tepat satu parent (root graph run) pada
    langchain-core >= 0.3 (attr ``parent_ids`` tersedia). Fallback untuk core
    lama: cocokkan ``metadata.langgraph_node`` dengan nama event.
    """
    name = event.get("name")
    if name not in GRAPH_NODE_NAMES:
        return None
    parents = event.get("parent_ids")
    if parents is not None:
        return name if len(parents) <= 1 else None
    metadata = event.get("metadata") or {}
    return name if metadata.get("langgraph_node") == name else None


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
        request_id = str(uuid.uuid4())
        current_state: dict = {"status": "failed", "confidence_score": 0.0, "reflection_count": 0}

        # Langfuse: satu root trace per query. Optional — no-op jika disabled.
        trace = observability.start_query_trace({
            "request_id": request_id,
            "session_id": body.session_id,
            "environment": settings.APP_ENV,
            "query_length": len(body.query),
        })
        trace_token = observability.set_active_trace(trace)

        try:
            graph = _get_graph()

            # RBAC filter from user profile
            rbac_filter = get_user_rbac_filter(user)

            user_id = str(user["id"])

            # Resolusi conversation + history. Harus dilakukan SEBELUM graph
            # agar konteks percakapan sebelumnya tersedia untuk LLM.
            # Ownership divalidasi: session milik user lain → tidak dipakai.
            conversation_id = None
            conversation_history = []
            try:
                conv = await get_or_create_user_conversation(
                    body.session_id, user_id, title=body.query[:60] + ("..." if len(body.query) > 60 else ""),
                )
                if conv is None:
                    raise HTTPException(
                        status_code=403,
                        detail="Session ini milik user lain. Buat session baru.",
                    )
                conversation_id = str(conv["id"])
                conversation_history = await get_messages_for_session(
                    body.session_id,
                    user_id,
                    limit=settings.CONVERSATION_HISTORY_LIMIT,
                    max_chars=settings.CONVERSATION_HISTORY_MAX_CHARS,
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Gagal memuat history conversation: %s", e)
                conversation_history = []

            initial_state = {
                "query": body.query,
                "session_id": body.session_id,
                "user_id": user_id,
                "user_department": user.get("department", "") or "",
                "user_clearance_level": user.get("clearance_level", 1) or 1,
                "rbac_filter": rbac_filter,
                "request_id": request_id,
                "trace_id": trace.id if trace is not None else None,
                "langfuse_trace": trace,
                "status": "completed",
                "error_code": None,
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
                "follow_up_suggestions": [],
                "action_items": [],
                "conversation_history": conversation_history,
                "llm_usage": {},
                "tool_results": [],
                "error": None,
                "query_deadline": time.time() + settings.QUERY_TIMEOUT_SECONDS,
            }

            current_state = initial_state.copy()
            logger.info("[Query] Starting graph.astream for query: '%s...'", body.query[:60])

            queue = asyncio.Queue()

            async def run_graph():
                try:
                    node_count = 0
                    # astream_events (v2): event lifecycle per node. Event
                    # "on_chain_start" level node dikirim SAAT node MULAI
                    # berjalan, sehingga indikator pipeline di frontend
                    # berpindah real-time (astream() biasa baru mengirim
                    # setelah node selesai).
                    async for event in graph.astream_events(initial_state, version="v2"):
                        etype = event.get("event")
                        if etype == "on_chain_start":
                            node_name = _lifecycle_node_name(event)
                            if node_name:
                                node_count += 1
                                logger.info("[Query] Node mulai #%d: %s", node_count, node_name)
                                await queue.put({"type": "agent", "agent": node_name, "status": "started"})
                        elif etype == "on_chain_end":
                            node_name = _lifecycle_node_name(event)
                            if node_name:
                                output = (event.get("data") or {}).get("output")
                                if isinstance(output, dict):
                                    current_state.update(output)
                    logger.info("[Query] graph.astream_events completed. Total nodes: %d", node_count)
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

            # Tentukan status akhir: degraded jika ada error/fallback, selain itu completed.
            status = "completed"
            error_code = current_state.get("error_code")
            if current_state.get("error"):
                status = "degraded" if current_state.get("final_answer") else "failed"
                error_code = error_code or "LLM_FAILURE"

            # Log query
            try:
                usage = current_state.get("llm_usage", {}) or {}
                await log_query(
                    query=body.query, intent=current_state.get("intent", ""),
                    agents_activated=current_state.get("agents_to_activate", []),
                    latency_ms=elapsed_ms, confidence_score=current_state.get("confidence_score", 0),
                    reflection_count=current_state.get("reflection_count", 0),
                    model_used=settings.GROQ_MODEL_REASONING,
                    estimated_cost_usd=usage.get("estimated_cost_usd", 0.0),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    usage_details=usage,
                    request_id=request_id,
                    trace_id=current_state.get("trace_id"),
                    status=status,
                    session_id=body.session_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning("Gagal log query: %s", e)

            # Save conversation
            try:
                # Reuse conversation_id yang sudah di-resolve sebelum graph.
                # Jika belum ada (mis. gagal load history), fallback ownership-aware.
                if not conversation_id:
                    conv = await get_or_create_user_conversation(
                        body.session_id,
                        str(user["id"]),
                        title=body.query[:60] + ("..." if len(body.query) > 60 else ""),
                    )
                    if conv is None:
                        logger.warning("Session milik user lain, pesan tidak disimpan.")
                        conversation_id = None
                    else:
                        conversation_id = str(conv["id"])

                if conversation_id:
                    await save_message(
                        conversation_id=conversation_id, role="user", content=body.query,
                        request_id=request_id,
                    )
                    await save_message(
                        conversation_id=conversation_id, role="assistant",
                        content=current_state.get("final_answer", ""),
                        citations=current_state.get("citations", []),
                        confidence_score=current_state.get("confidence_score", 0),
                        action_items=current_state.get("action_items", []),
                        follow_up_suggestions=current_state.get("follow_up_suggestions", []),
                        intent=current_state.get("intent", ""),
                        intent_type=current_state.get("intent_type", ""),
                        reflection_count=current_state.get("reflection_count", 0),
                        request_id=request_id,
                        trace_id=current_state.get("trace_id"),
                        status=status,
                        error_code=error_code,
                        latency_ms=elapsed_ms, model_used=settings.GROQ_MODEL_REASONING,
                    )
            except Exception as e:
                logger.warning("Gagal menyimpan pesan ke DB: %s", e)

            final_answer = current_state.get("final_answer") or "Maaf, gagal memproses pertanyaan."
            final_response = {
                "type": "result", "answer": final_answer,
                "status": status,
                "citations": current_state.get("citations", []),
                "action_items": current_state.get("action_items", []),
                "confidence_score": current_state.get("confidence_score", 0),
                "intent": current_state.get("intent", ""),
                "intent_type": current_state.get("intent_type", ""),
                "reflection_count": current_state.get("reflection_count", 0),
                "latency_ms": elapsed_ms, "session_id": body.session_id,
                "follow_up_suggestions": current_state.get("follow_up_suggestions", []),
                "request_id": request_id,
                "trace_id": current_state.get("trace_id"),
            }
            yield f"data: {json.dumps(final_response)}\n\n"

        except asyncio.CancelledError:
            logger.info("[Query] Generator dibatalkan (disconnect).")
            raise
        except HTTPException as e:
            # Ownership/validasi — pesan aman, kode stabil.
            code = "SESSION_OWNERSHIP" if e.status_code == 403 else "SERVER_ERROR"
            yield f"data: {json.dumps(_safe_error(code, str(e.detail)))}\n\n"
        except Exception as e:
            logger.exception("[Query API] Error: %s", e)
            payload = _safe_error("SERVER_ERROR", str(e))
            yield f"data: {json.dumps(payload)}\n\n"
        finally:
            # Langfuse: tutup trace + flush. Kegagalan observability tidak boleh
            # memengaruhi respons user.
            observability.end_query_trace(
                trace,
                output={"request_id": request_id, "status": current_state.get("status", "completed") if "current_state" in dir() else "failed"},
                meta={
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "confidence_score": current_state.get("confidence_score", 0) if "current_state" in dir() else 0,
                    "reflection_count": current_state.get("reflection_count", 0) if "current_state" in dir() else 0,
                },
            )
            observability.flush()
            observability.reset_active_trace(trace_token)

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
