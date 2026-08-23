"""
Utility functions untuk formatting — EnterpriseMind AI.

Fungsi-fungsi yang digunakan bersama oleh multiple agent
untuk formatting dokumen, history, dan data lainnya.
"""


def format_documents_for_prompt(
    documents: list[dict],
    max_chars: int = 2500,
    include_date: bool = True,
) -> str:
    """
    Format dokumen menjadi string untuk LLM prompt context.

    Args:
        documents: List dokumen hasil retrieval (dict dengan content, source, date).
        max_chars: Maksimum karakter konten per dokumen.
        include_date: Sertakan tanggal dokumen dalam output.

    Returns:
        String terformat siap dimasukkan ke prompt.
    """
    parts = []
    for i, doc in enumerate(documents, 1):
        source = _get_field(doc, "source") or _get_field(doc, "filename") or "unknown"
        content = _get_field(doc, "content") or ""
        content = content[:max_chars]

        if include_date:
            date = _get_field(doc, "date") or _get_field(doc, "upload_date") or "N/A"
            parts.append(
                f"[Dokumen {i}] (Sumber: {source}, Tanggal: {date})\n"
                f"{content}\n"
            )
        else:
            parts.append(f"[Dokumen {i}] (Sumber: {source})\n{content}\n")

    return "\n".join(parts)


def estimate_tokens(text: str) -> int:
    """
    Estimasi token dari teks (heuristik: 4 karakter ≈ 1 token).
    Cukup akurat untuk budgeting prompt agar tidak melebihi TPM provider.
    """
    if not text:
        return 0
    # Bahasa campuran: angka aman ~4 char/token. Jangan terlalu presisi.
    return max(1, int(len(text) / 4))


def truncate_documents_for_budget(
    documents: list[dict],
    max_total_chars: int,
    per_doc_max_chars: int = 2500,
) -> list[dict]:
    """
    Potong daftar dokumen agar total context muat dalam budget karakter.

    Strategi:
    1. Sort berdasarkan relevance_score (dokumen paling relevan dipertahankan).
    2. Potong content per dokumen ke per_doc_max_chars.
    3. Drop dokumen paling tidak relevan hingga total muat dalam max_total_chars.

    Returns:
        List dokumen baru (copy) yang sudah dibatasi.
    """
    if not documents:
        return []

    ordered = sorted(
        documents,
        key=lambda d: d.get("reranker_score", d.get("relevance_score", 0)),
        reverse=True,
    )

    result = []
    used = 0
    for doc in ordered:
        content = _get_field(doc, "content") or ""
        content = content[:per_doc_max_chars]
        doc_meta = doc.get("metadata", {}) if isinstance(doc.get("metadata"), dict) else {}

        if used + len(content) > max_total_chars:
            break

        # Copy doc + truncate content + simpan metadata
        new_doc = dict(doc)
        new_doc["content"] = content
        new_doc["metadata"] = dict(doc_meta)
        result.append(new_doc)
        used += len(content)

    logger = _get_logger()
    logger.info(
        "[Budget] Dokumen dibatasi: %d/%d dipakai, ~%d chars (~%d token)",
        len(result), len(documents), used, estimate_tokens(str(result[:1])) if result else 0,
    )
    return result


def _get_logger():
    import logging
    return logging.getLogger(__name__)


def _get_field(doc: dict, field: str) -> str | None:
    """Get field from doc dict, checking both top-level and nested metadata."""
    value = doc.get(field)
    if value:
        return str(value)
    metadata = doc.get("metadata", {})
    if isinstance(metadata, dict):
        value = metadata.get(field)
        if value:
            return str(value)
    return None


def format_conversation_history(history: list[dict], max_messages: int = 5) -> str:
    """
    Format riwayat percakapan untuk LLM prompt context.

    Args:
        history: List pesan dengan key 'role' dan 'content'.
        max_messages: Maksimum pesan yang disertakan (paling baru).

    Returns:
        String riwayat percakapan terformat.
    """
    if not history:
        return ""

    recent = history[-max_messages:]
    parts = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:200]
        label = {"user": "Pengguna", "assistant": "Asisten", "system": "Sistem"}.get(role, role)
        parts.append(f"{label}: {content}")

    return "\n".join(parts)
