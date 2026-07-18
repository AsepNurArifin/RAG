"""
EnterpriseMind AI — FastAPI Application Entry Point.

Entry point utama backend. Mount semua router dari api/,
konfigurasi CORS, dan setup rate limiting.

Ref: A.3.3 di SRS_PRD.md (Kebutuhan Antarmuka API)
Endpoint yang diekspos: /query, /upload, /documents, /metrics
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

# ------------------------------------------------------------------ #
# Logging Setup
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO if settings.APP_ENV == "production" else logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Disable verbose logging from noisy libraries
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Rate Limiter (ref: SECURITY.md #4)
# ------------------------------------------------------------------ #
limiter = Limiter(key_func=get_remote_address)

# ------------------------------------------------------------------ #
# FastAPI App
# ------------------------------------------------------------------ #
app = FastAPI(
    title="EnterpriseMind AI",
    description=(
        "Intelligent Multi-Agent Knowledge Assistant — "
        "Agentic RAG dengan verifikasi fakta, sitasi sumber, "
        "dan action item generation."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------------------------------------------ #
# CORS Middleware (ref: ADR-009 — VPS backend + Vercel frontend)
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Health Check
# ------------------------------------------------------------------ #
@app.get("/health")
async def health_check():
    """Health check endpoint untuk monitoring."""
    return {
        "status": "healthy",
        "app": "EnterpriseMind AI",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }


# ------------------------------------------------------------------ #
# Startup Event
# ------------------------------------------------------------------ #
@app.on_event("startup")
async def startup_event():
    """Inisialisasi saat aplikasi dimulai. Pre-load models untuk eliminate cold start."""
    import time
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("EnterpriseMind AI Backend starting...")
    logger.info("Environment: %s", settings.APP_ENV)
    logger.info("CORS Origins: %s", settings.CORS_ORIGINS)
    logger.info("LLM Fast Model: %s", settings.GROQ_MODEL_FAST)
    logger.info("LLM Reasoning Model: %s", settings.GROQ_MODEL_REASONING)
    logger.info("Rate Limit: %d requests/minute", settings.RATE_LIMIT_PER_MINUTE)

    # Pre-load embedding model (eliminates ~20s cold start)
    try:
        from app.ingestion.embedder import get_embedding_model
        logger.info("Pre-loading embedding model: %s...", settings.EMBEDDING_MODEL)
        get_embedding_model()
        logger.info("Embedding model ready.")
    except Exception as e:
        logger.warning("Failed to pre-load embedding model: %s", e)

    # Pre-load reranker model (eliminates ~5s cold start)
    try:
        from app.retrieval.reranker import get_reranker
        logger.info("Pre-loading reranker model...")
        get_reranker()
        logger.info("Reranker model ready.")
    except Exception as e:
        logger.warning("Failed to pre-load reranker model: %s", e)

    # Pre-initialize Sastrawi stemmer (eliminates ~1s first-call init)
    try:
        from app.retrieval.hybrid_search import _get_stemmer
        logger.info("Pre-loading Sastrawi stemmer...")
        _get_stemmer()
        logger.info("Sastrawi stemmer ready.")
    except Exception as e:
        logger.warning("Failed to pre-load Sastrawi stemmer: %s", e)

    elapsed = time.time() - t0
    logger.info("Startup pre-loading completed in %.1fs", elapsed)
    logger.info("=" * 60)


# ------------------------------------------------------------------ #
# Global Exception Handler
# ------------------------------------------------------------------ #
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global untuk exception yang tidak tertangani.

    Mengembalikan pesan error yang user-friendly (bukan raw stack trace)
    sesuai DEFINITION_OF_DONE.md checklist UI.
    """
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Terjadi kesalahan internal. Silakan coba lagi.",
            "detail": str(exc) if settings.APP_ENV == "development" else None,
        },
    )


# ------------------------------------------------------------------ #
# Router Registration
from app.api.upload import router as upload_router
from app.api.query import router as query_router
from app.api.documents import router as documents_router
from app.api.metrics import router as metrics_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.sessions import router as sessions_router

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(metrics_router)
app.include_router(users_router)
app.include_router(sessions_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
    )

# Trigger reload

# Trigger reload 2
