"""
Utility functions untuk formatting — EnterpriseMind AI.

Fungsi-fungsi yang digunakan bersama oleh multiple agent
untuk formatting dokumen, history, dan data lainnya.
"""


def format_documents_for_prompt(
    documents: list[dict],
    max_chars: int = 800,
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
        source = doc.get("source", doc.get("filename", "unknown"))
        content = doc.get("content", "")[:max_chars]

        if include_date:
            date = doc.get("date", doc.get("upload_date", "N/A")) or "N/A"
            parts.append(
                f"--- Dokumen {i} ---\n"
                f"Sumber: {source} (tanggal: {date})\n"
                f"Konten: {content}\n"
            )
        else:
            parts.append(f"[Sumber: {source}]\n{content}\n")

    return "\n".join(parts)


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
