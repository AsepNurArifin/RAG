"""
Configuration — EnterpriseMind AI.

Central config. All LLM model names defined HERE ONLY (single source of truth).
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    import warnings
    warnings.warn(".env tidak ditemukan atau GROQ_API_KEY belum di-set.")


def _safe_int(value: str, name: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable {name} harus berupa angka, menerima: '{value}'")


def _safe_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"Environment variable {name} harus bernilai boolean, menerima: '{value}'")


@dataclass(frozen=True)
class Settings:
    # LLM — Groq (fast inference)
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    GROQ_MODEL_FAST: str = field(default_factory=lambda: os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b"))
    GROQ_MODEL_REASONING: str = field(default_factory=lambda: os.getenv("GROQ_MODEL_REASONING", "openai/gpt-oss-120b"))

    # LLM token cost per 1M tokens (USD). Defaults ~ Groq pricing.
    LLM_INPUT_COST_PER_MILLION_TOKENS: float = field(
        default_factory=lambda: _safe_float(os.getenv("LLM_INPUT_COST_PER_MILLION_TOKENS", "0.25"), "LLM_INPUT_COST_PER_MILLION_TOKENS")
    )
    LLM_OUTPUT_COST_PER_MILLION_TOKENS: float = field(
        default_factory=lambda: _safe_float(os.getenv("LLM_OUTPUT_COST_PER_MILLION_TOKENS", "0.80"), "LLM_OUTPUT_COST_PER_MILLION_TOKENS")
    )

    # PostgreSQL
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost:5432/enterprisemind")
    )

    # Milvus
    MILVUS_URI: str = field(default_factory=lambda: os.getenv("MILVUS_URI", "http://localhost:19530"))
    MILVUS_COLLECTION: str = field(default_factory=lambda: os.getenv("MILVUS_COLLECTION", "enterprisemind_documents"))

    # Docling (Docker serve) — OPSIONAL. Default OFF agar VPS tetap ramping
    # (plan_optimasi.md Fase 2). Saat OFF, ekstraksi tabel memakai jalur native
    # PyMuPDF (find_tables().to_markdown()) + RapidOCR fallback.
    # Nyalakan hanya untuk backfill dokumen bertabel kompleks via Docling eksternal.
    DOCLING_ENABLED: bool = field(
        default_factory=lambda: _safe_bool(os.getenv("DOCLING_ENABLED", "false"), "DOCLING_ENABLED")
    )
    DOCLING_URL: str = field(default_factory=lambda: os.getenv("DOCLING_URL", "http://localhost:5001"))

    # Temporal
    TEMPORAL_HOST: str = field(default_factory=lambda: os.getenv("TEMPORAL_HOST", "localhost:7233"))

    # Embedding
    EMBEDDING_MODEL: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"))
    EMBEDDING_DIMENSIONS: int = 1024

    # Reranker — plan_optimasi.md Fase 3A: ONNX INT8 default (runtime ringan,
    # tanpa torch/sentence-transformers). Fallback "pytorch" hanya dipakai saat
    # berkas ONNX belum tersedia / RERANKER_BACKEND=pytorch (dev, ekspor model).
    RERANKER_BACKEND: str = field(
        default_factory=lambda: os.getenv("RERANKER_BACKEND", "onnx").strip().lower()
    )
    RERANKER_MODEL: str = field(default_factory=lambda: os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"))
    # Override direktori ONNX (jika kosong, diturunkan dari HF_HOME / model_cache)
    RERANKER_ONNX_DIR: str = field(default_factory=lambda: os.getenv("RERANKER_ONNX_DIR", ""))
    RERANKER_MAX_LENGTH: int = field(default_factory=lambda: _safe_int(os.getenv("RERANKER_MAX_LENGTH", "256"), "RERANKER_MAX_LENGTH"))
    # Threads inference bersama embedding+reranker (0 = biarkan onnxruntime memilih)
    ORT_THREADS: int = field(default_factory=lambda: _safe_int(os.getenv("ORT_THREADS", "0"), "ORT_THREADS"))

    # Agent Thresholds
    CONFIDENCE_THRESHOLD: float = 0.6
    MAX_REFLECTION_ITERATIONS: int = 1
    QUERY_TIMEOUT_SECONDS: int = 180

    # Jeda antar node LLM berat (Verifier → Summarizer) agar tidak melampaui
    # TPM provider (gpt-oss-120b tier free ~8000 TPM). Detik.
    LLM_NODE_COOLDOWN_SECONDS: int = field(
        default_factory=lambda: _safe_int(os.getenv("LLM_NODE_COOLDOWN_SECONDS", "5"), "LLM_NODE_COOLDOWN_SECONDS")
    )

    # Application
    APP_ENV: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    APP_HOST: str = field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    APP_PORT: int = field(default_factory=lambda: _safe_int(os.getenv("APP_PORT", "8000"), "APP_PORT"))
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = field(default_factory=lambda: _safe_int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"), "RATE_LIMIT_PER_MINUTE"))

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = field(default_factory=lambda: _safe_int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"), "MAX_UPLOAD_SIZE_MB"))
    EXTRACTION_TIMEOUT_SECONDS: int = field(default_factory=lambda: _safe_int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "600"), "EXTRACTION_TIMEOUT_SECONDS"))

    # MinIO Storage
    MINIO_ENDPOINT: str = field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    MINIO_ACCESS_KEY: str = field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    MINIO_SECRET_KEY: str = field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    MINIO_BUCKET_DOCS: str = field(default_factory=lambda: os.getenv("MINIO_BUCKET_DOCS", "enterprisemind-docs"))

    # JWT
    JWT_SECRET_KEY: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", ""))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = field(default_factory=lambda: _safe_int(os.getenv("JWT_EXPIRE_MINUTES", "480"), "JWT_EXPIRE_MINUTES"))
    JWT_SECRET_MIN_BYTES: int = 32

    # Bootstrap admin (only used at startup; never store in repo)
    BOOTSTRAP_ADMIN_EMAIL: str = field(default_factory=lambda: os.getenv("BOOTSTRAP_ADMIN_EMAIL", ""))
    BOOTSTRAP_ADMIN_PASSWORD: str = field(default_factory=lambda: os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""))

    # Conversation memory
    CONVERSATION_HISTORY_LIMIT: int = field(
        default_factory=lambda: _safe_int(os.getenv("CONVERSATION_HISTORY_LIMIT", "5"), "CONVERSATION_HISTORY_LIMIT")
    )
    CONVERSATION_HISTORY_MAX_CHARS: int = field(
        default_factory=lambda: _safe_int(os.getenv("CONVERSATION_HISTORY_MAX_CHARS", "200"), "CONVERSATION_HISTORY_MAX_CHARS")
    )

    # Observability (LangFuse) — optional, non-critical
    LANGFUSE_PUBLIC_KEY: str = field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""))
    LANGFUSE_SECRET_KEY: str = field(default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", ""))
    LANGFUSE_HOST: str = field(default_factory=lambda: os.getenv("LANGFUSE_HOST", ""))
    LANGFUSE_ENABLED: bool = field(
        default_factory=lambda: _safe_bool(os.getenv("LANGFUSE_ENABLED", "false"), "LANGFUSE_ENABLED")
    )

    # Tools
    ENABLE_CALCULATOR: bool = field(
        default_factory=lambda: _safe_bool(os.getenv("ENABLE_CALCULATOR", "true"), "ENABLE_CALCULATOR")
    )
    ENABLE_METADATA_TOOL: bool = field(
        default_factory=lambda: _safe_bool(os.getenv("ENABLE_METADATA_TOOL", "true"), "ENABLE_METADATA_TOOL")
    )

    def __post_init__(self):
        if not self.JWT_SECRET_KEY:
            raise ValueError(
                "JWT_SECRET_KEY wajib di-set di SEMUA environment (termasuk development). "
                "Generate dengan: openssl rand -hex 32"
            )
        if len(self.JWT_SECRET_KEY.encode("utf-8")) < self.JWT_SECRET_MIN_BYTES:
            raise ValueError(
                f"JWT_SECRET_KEY terlalu pendek (minimal {self.JWT_SECRET_MIN_BYTES} byte). "
                "Generate dengan: openssl rand -hex 32"
            )


def _safe_float(value: str, name: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable {name} harus berupa angka, menerima: '{value}'")


settings = Settings()
