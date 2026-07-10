"""
Database Models & Helpers — EnterpriseMind AI.

Definisi tabel Supabase dan helper functions untuk CRUD operasi.
Menggunakan Supabase Python client (bukan SQLAlchemy) sesuai ADR-008.

Tabel yang dibutuhkan (buat via Supabase Dashboard / SQL Editor):

-- documents: metadata dokumen yang diupload
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'indexed', 'failed')),
    chunk_count INTEGER DEFAULT 0,
    file_path TEXT,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- conversations: sesi percakapan
CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- messages: pesan dalam percakapan
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    confidence_score FLOAT,
    action_items JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- evaluation_results: hasil evaluasi RAGAS
CREATE TABLE evaluation_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    expected_answer TEXT,
    actual_answer TEXT,
    faithfulness FLOAT,
    answer_relevance FLOAT,
    context_precision FLOAT,
    model_type TEXT CHECK (model_type IN ('naive_rag', 'agentic_rag')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- query_logs: log interaksi untuk metrik dashboard
CREATE TABLE query_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    intent TEXT,
    agents_activated JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    confidence_score FLOAT,
    reflection_count INTEGER DEFAULT 0,
    model_used TEXT,
    estimated_cost_usd FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Document Operations
# ------------------------------------------------------------------ #


async def create_document(
    filename: str,
    file_type: str,
    category: str = "uncategorized",
    file_path: str | None = None,
    file_size_bytes: int = 0,
) -> dict[str, Any]:
    """
    Buat record dokumen baru di Supabase.

    Args:
        filename: Nama file dokumen.
        file_type: Tipe file (pdf, docx, txt).
        category: Kategori dokumen (default: uncategorized).
        file_path: Path ke file di Supabase Storage.
        file_size_bytes: Ukuran file dalam bytes.

    Returns:
        Dict data dokumen yang baru dibuat.

    Side effects:
        INSERT ke tabel 'documents' di Supabase.
    """
    client = get_supabase_client()
    data = {
        "filename": filename,
        "file_type": file_type,
        "category": category,
        "status": "pending",
        "file_path": file_path,
        "file_size_bytes": file_size_bytes,
    }
    result = client.table("documents").insert(data).execute()
    logger.info("Dokumen dibuat: filename=%s, id=%s", filename, result.data[0]["id"])
    return result.data[0]


async def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
) -> dict[str, Any]:
    """
    Update status dokumen (pending → processing → indexed / failed).

    Args:
        document_id: UUID dokumen.
        status: Status baru (pending, processing, indexed, failed).
        chunk_count: Jumlah chunk yang dihasilkan (opsional).

    Returns:
        Dict data dokumen yang diupdate.

    Side effects:
        UPDATE tabel 'documents' di Supabase.
    """
    client = get_supabase_client()
    data: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if chunk_count is not None:
        data["chunk_count"] = chunk_count

    result = (
        client.table("documents")
        .update(data)
        .eq("id", document_id)
        .execute()
    )
    logger.info("Status dokumen diupdate: id=%s, status=%s", document_id, status)
    return result.data[0]


async def get_all_documents() -> list[dict[str, Any]]:
    """
    Ambil semua dokumen.

    Returns:
        List dict data dokumen, diurutkan terbaru dulu.

    Side effects:
        SELECT dari tabel 'documents' di Supabase.
    """
    client = get_supabase_client()
    result = (
        client.table("documents")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return result.data


async def delete_document(document_id: str) -> bool:
    """
    Hapus dokumen berdasarkan ID.

    Args:
        document_id: UUID dokumen yang akan dihapus.

    Returns:
        True jika berhasil dihapus.

    Side effects:
        DELETE dari tabel 'documents' di Supabase.
    """
    client = get_supabase_client()
    client.table("documents").delete().eq("id", document_id).execute()
    logger.info("Dokumen dihapus: id=%s", document_id)
    return True


# ------------------------------------------------------------------ #
# Query Log Operations
# ------------------------------------------------------------------ #


async def log_query(
    query: str,
    intent: str | None = None,
    agents_activated: list[str] | None = None,
    latency_ms: int | None = None,
    confidence_score: float | None = None,
    reflection_count: int = 0,
    model_used: str | None = None,
    estimated_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """
    Catat log query untuk metrik dashboard (FR7.1).

    Args:
        query: Pertanyaan pengguna.
        intent: Hasil klasifikasi intent dari Orchestrator.
        agents_activated: Daftar agent yang diaktifkan.
        latency_ms: Waktu respons dalam milidetik.
        confidence_score: Skor kepercayaan Verifier.
        reflection_count: Jumlah iterasi reflection loop.
        model_used: Model yang digunakan.
        estimated_cost_usd: Estimasi biaya API call.

    Returns:
        Dict data log yang dibuat.

    Side effects:
        INSERT ke tabel 'query_logs' di Supabase.
    """
    client = get_supabase_client()
    data = {
        "query": query,
        "intent": intent,
        "agents_activated": agents_activated or [],
        "latency_ms": latency_ms,
        "confidence_score": confidence_score,
        "reflection_count": reflection_count,
        "model_used": model_used,
        "estimated_cost_usd": estimated_cost_usd,
    }
    result = client.table("query_logs").insert(data).execute()
    return result.data[0]


# ------------------------------------------------------------------ #
# Message Operations
# ------------------------------------------------------------------ #


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    confidence_score: float | None = None,
    action_items: list[dict] | None = None,
    latency_ms: int | None = None,
    model_used: str | None = None,
) -> dict[str, Any]:
    """
    Simpan pesan ke riwayat percakapan.

    Args:
        conversation_id: UUID percakapan.
        role: Peran pengirim (user, assistant, system).
        content: Isi pesan.
        citations: Daftar sitasi (opsional).
        confidence_score: Skor kepercayaan (opsional).
        action_items: Daftar action items (opsional).
        latency_ms: Waktu respons dalam ms (opsional).
        model_used: Model yang digunakan (opsional).

    Returns:
        Dict data pesan yang disimpan.

    Side effects:
        INSERT ke tabel 'messages' di Supabase.
    """
    client = get_supabase_client()
    data = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "citations": citations or [],
        "confidence_score": confidence_score,
        "action_items": action_items or [],
        "latency_ms": latency_ms,
        "model_used": model_used,
    }
    result = client.table("messages").insert(data).execute()
    return result.data[0]
