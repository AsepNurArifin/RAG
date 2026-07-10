"""
Konfigurasi terpusat EnterpriseMind AI.

PENTING (ref: AI_RULES.md #1, ARCHITECTURE.md prinsip #1):
- Semua nama model LLM HANYA didefinisikan di file ini.
- Tidak ada agent atau modul lain yang boleh hardcode nama model.
- Sebelum implementasi, cek console.groq.com/docs/models untuk memastikan
  model masih aktif — Groq mendeprecate model dengan frekuensi tinggi.

Konfigurasi ini diimpor oleh seluruh modul backend melalui:
    from app.core.config import settings
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    import warnings
    warnings.warn(".env tidak ditemukan atau kosong. Pastikan semua variabel environment sudah di-set.")


def _safe_int(value: str, name: str) -> int:
    """Konversi string ke int dengan error message yang jelas."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Environment variable {name} harus berupa angka, "
            f"menerima: '{value}'"
        )


@dataclass(frozen=True)
class Settings:
    """Konfigurasi aplikasi — immutable setelah inisialisasi."""

    # ------------------------------------------------------------------ #
    # LLM Models (SINGLE SOURCE OF TRUTH)
    # Ref: ADR-001 di DECISION_LOG.md
    # ------------------------------------------------------------------ #
    REASONING_MODEL: str = "llama-3.3-70b-versatile"
    """Model untuk task berat: verifikasi fakta, sintesis akhir."""

    FAST_MODEL: str = "llama-3.1-8b-instant"
    """Model untuk task ringan: routing, ekstraksi, intent classification."""

    # ------------------------------------------------------------------ #
    # Groq API
    # ------------------------------------------------------------------ #
    GROQ_API_KEY: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )

    # ------------------------------------------------------------------ #
    # Supabase (ref: ADR-008)
    # ------------------------------------------------------------------ #
    SUPABASE_URL: str = field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "")
    )
    SUPABASE_ANON_KEY: str = field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", "")
    )
    SUPABASE_SERVICE_ROLE_KEY: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )

    # ------------------------------------------------------------------ #
    # Chroma Vector DB
    # ------------------------------------------------------------------ #
    CHROMA_HOST: str = field(
        default_factory=lambda: os.getenv("CHROMA_HOST", "")
    )
    """Host Chroma server untuk Docker deployment.
    Jika kosong, gunakan persistent local Chroma."""

    CHROMA_PORT: int = field(
        default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000"))
    )

    CHROMA_PERSIST_DIRECTORY: str = field(
        default_factory=lambda: os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "./chroma_db"
        )
    )

    # ------------------------------------------------------------------ #
    # Embedding Model
    # ------------------------------------------------------------------ #
    EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
    )

    # ------------------------------------------------------------------ #
    # LangFuse Observability (ref: ADR-006)
    # ------------------------------------------------------------------ #
    LANGFUSE_PUBLIC_KEY: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", "")
    )
    LANGFUSE_SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", "")
    )
    LANGFUSE_HOST: str = field(
        default_factory=lambda: os.getenv(
            "LANGFUSE_HOST", "http://localhost:3001"
        )
    )

    # ------------------------------------------------------------------ #
    # Agent Thresholds
    # ------------------------------------------------------------------ #
    CONFIDENCE_THRESHOLD: float = 0.6
    """Skor minimum confidence Verifier sebelum trigger reflection loop."""

    MAX_REFLECTION_ITERATIONS: int = 2
    """Jumlah maksimum iterasi reflection loop (ref: NFR-P2, B.6 Risiko)."""

    QUERY_TIMEOUT_SECONDS: int = 60
    """Timeout keras untuk query kompleks (ref: NFR-P2).
    Dinaikkan dari 12s ke 60s karena pipeline multi-agent
    membutuhkan 4-5 LLM calls berturut-turut."""

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_ENV: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development")
    )
    APP_HOST: str = field(
        default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0")
    )
    APP_PORT: int = field(
        default_factory=lambda: _safe_int(os.getenv("APP_PORT", "8000"), "APP_PORT")
    )
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: [
            origin.strip() for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:3000"
            ).split(",")
        ]
    )

    # ------------------------------------------------------------------ #
    # Rate Limiting (ref: SECURITY.md #4)
    # ------------------------------------------------------------------ #
    RATE_LIMIT_PER_MINUTE: int = field(
        default_factory=lambda: _safe_int(
            os.getenv("RATE_LIMIT_PER_MINUTE", "30"), "RATE_LIMIT_PER_MINUTE"
        )
    )

    # ------------------------------------------------------------------ #
    # File Upload & Ingestion
    # ------------------------------------------------------------------ #
    MAX_UPLOAD_SIZE_MB: int = field(
        default_factory=lambda: _safe_int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"), "MAX_UPLOAD_SIZE_MB")
    )
    EXTRACTION_TIMEOUT_SECONDS: int = field(
        default_factory=lambda: _safe_int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "120"), "EXTRACTION_TIMEOUT_SECONDS")
    )

    # ------------------------------------------------------------------ #
    # Document Chunking
    # ------------------------------------------------------------------ #
    CHUNK_SIZE: int = field(
        default_factory=lambda: _safe_int(os.getenv("CHUNK_SIZE", "1000"), "CHUNK_SIZE")
    )
    CHUNK_OVERLAP: int = field(
        default_factory=lambda: _safe_int(os.getenv("CHUNK_OVERLAP", "200"), "CHUNK_OVERLAP")
    )

    # ------------------------------------------------------------------ #
    # JWT Authentication
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "")
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = field(
        default_factory=lambda: _safe_int(
            os.getenv("JWT_EXPIRE_MINUTES", "480"), "JWT_EXPIRE_MINUTES"
        )
    )
    """Token berlaku 8 jam (480 menit) — sesuai jam kerja kantor."""

    def __post_init__(self):
        if self.APP_ENV != "development" and not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY wajib di-set di environment production!")


# Singleton instance — impor ini di seluruh kode backend
settings = Settings()
