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
    """Inisialisasi saat aplikasi dimulai."""
    logger.info("=" * 60)
    logger.info("EnterpriseMind AI Backend starting...")
    logger.info("Environment: %s", settings.APP_ENV)
    logger.info("CORS Origins: %s", settings.CORS_ORIGINS)
    logger.info(
        "LLM Models: fast=%s, reasoning=%s",
        settings.FAST_MODEL,
        settings.REASONING_MODEL,
    )
    logger.info(
        "Rate Limit: %d requests/minute", settings.RATE_LIMIT_PER_MINUTE
    )
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
        reload=settings.APP_ENV == "development",
    )

# Trigger reload

# Trigger reload 2
