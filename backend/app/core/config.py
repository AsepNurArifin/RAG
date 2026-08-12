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


@dataclass(frozen=True)
class Settings:
    # LLM — Groq (fast inference)
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    GROQ_MODEL_FAST: str = field(default_factory=lambda: os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant"))
    GROQ_MODEL_REASONING: str = field(default_factory=lambda: os.getenv("GROQ_MODEL_REASONING", "llama-3.3-70b-versatile"))

    # PostgreSQL
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost:5432/enterprisemind")
    )

    # Milvus
    MILVUS_URI: str = field(default_factory=lambda: os.getenv("MILVUS_URI", "http://localhost:19530"))
    MILVUS_COLLECTION: str = field(default_factory=lambda: os.getenv("MILVUS_COLLECTION", "enterprisemind_documents"))

    # Docling (Docker serve)
    DOCLING_URL: str = field(default_factory=lambda: os.getenv("DOCLING_URL", "http://localhost:5001"))

    # Temporal
    TEMPORAL_HOST: str = field(default_factory=lambda: os.getenv("TEMPORAL_HOST", "localhost:7233"))

    # Embedding
    EMBEDDING_MODEL: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"))
    EMBEDDING_DIMENSIONS: int = 1024

    # Agent Thresholds
    CONFIDENCE_THRESHOLD: float = 0.6
    MAX_REFLECTION_ITERATIONS: int = 1
    QUERY_TIMEOUT_SECONDS: int = 180

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

    # Chunking
    CHUNK_SIZE: int = field(default_factory=lambda: _safe_int(os.getenv("CHUNK_SIZE", "1000"), "CHUNK_SIZE"))
    CHUNK_OVERLAP: int = field(default_factory=lambda: _safe_int(os.getenv("CHUNK_OVERLAP", "200"), "CHUNK_OVERLAP"))

    # JWT
    JWT_SECRET_KEY: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", ""))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = field(default_factory=lambda: _safe_int(os.getenv("JWT_EXPIRE_MINUTES", "480"), "JWT_EXPIRE_MINUTES"))

    def __post_init__(self):
        if self.APP_ENV != "development" and not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY wajib di-set di environment production!")


settings = Settings()
