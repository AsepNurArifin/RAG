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


@dataclass(frozen=True)
class Settings:
    """Konfigurasi aplikasi — immutable setelah inisialisasi."""

    # ------------------------------------------------------------------ #
    # LLM Models (SINGLE SOURCE OF TRUTH)
    # Ref: ADR-001 di DECISION_LOG.md
    # ------------------------------------------------------------------ #
    REASONING_MODEL: str = "openai/gpt-oss-120b"
    """Model untuk task berat: verifikasi fakta, sintesis akhir."""

    FAST_MODEL: str = "openai/gpt-oss-20b"
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

    CHROMA_PORT: str = field(
        default_factory=lambda: os.getenv("CHROMA_PORT", "8000")
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

    QUERY_TIMEOUT_SECONDS: int = 12
    """Timeout keras untuk query kompleks (ref: NFR-P2)."""

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
        default_factory=lambda: int(os.getenv("APP_PORT", "8000"))
    )
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000"
        ).split(",")
    )

    # ------------------------------------------------------------------ #
    # Rate Limiting (ref: SECURITY.md #4)
    # ------------------------------------------------------------------ #
    RATE_LIMIT_PER_MINUTE: int = field(
        default_factory=lambda: int(
            os.getenv("RATE_LIMIT_PER_MINUTE", "30")
        )
    )

    # ------------------------------------------------------------------ #
    # JWT Authentication
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", "enterprisemind-dev-secret-change-in-production"
        )
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = field(
        default_factory=lambda: int(
            os.getenv("JWT_EXPIRE_MINUTES", "480")
        )
    )
    """Token berlaku 8 jam (480 menit) — sesuai jam kerja kantor."""


# Singleton instance — impor ini di seluruh kode backend
settings = Settings()
