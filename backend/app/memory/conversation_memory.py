"""
Conversation Memory — EnterpriseMind AI.

Short-term conversation memory: menyimpan riwayat percakapan
dalam sesi aktif agar sistem bisa merujuk pada konteks sebelumnya.

Ref: FR4.1 (riwayat dalam sesi), FR4.2 (merujuk konteks sebelumnya)

Usage:
    from app.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.add_message("session-123", "user", "Berapa cuti tahunan?")
    memory.add_message("session-123", "assistant", "12 hari kerja...")
    history = memory.get_history("session-123")
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Max messages per session untuk mencegah context overflow
MAX_HISTORY_LENGTH = 20


class ConversationMemory:
    """
    In-memory conversation history manager.

    Menyimpan riwayat per session_id di memori (bukan persisten).
    Untuk MVP, ini cukup. Untuk production, bisa dipindah ke
    Supabase atau Redis.
    """

    def __init__(self, max_history: int = MAX_HISTORY_LENGTH):
        """
        Inisialisasi ConversationMemory.

        Args:
            max_history: Maksimal pesan yang disimpan per sesi.
        """
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._max_history = max_history

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Tambah pesan ke riwayat sesi.

        Args:
            session_id: ID sesi percakapan.
            role: Peran pengirim ("user", "assistant", "system").
            content: Isi pesan.

        Side effects:
            Menulis ke in-memory dict.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._history[session_id].append(message)

        # Trim jika melebihi batas
        if len(self._history[session_id]) > self._max_history:
            self._history[session_id] = self._history[session_id][
                -self._max_history :
            ]

        logger.debug(
            "Pesan ditambahkan: session=%s, role=%s, total=%d",
            session_id,
            role,
            len(self._history[session_id]),
        )

    def get_history(self, session_id: str) -> list[dict]:
        """
        Ambil riwayat percakapan untuk sesi tertentu.

        Args:
            session_id: ID sesi percakapan.

        Returns:
            List dict pesan, urut kronologis.
        """
        return self._history.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """
        Hapus riwayat untuk sesi tertentu.

        Args:
            session_id: ID sesi yang akan dihapus.

        Side effects:
            Menghapus data dari in-memory dict.
        """
        if session_id in self._history:
            del self._history[session_id]
            logger.info("Session dihapus: %s", session_id)

    def get_active_sessions(self) -> list[str]:
        """
        Ambil daftar session ID yang aktif.

        Returns:
            List session ID.
        """
        return list(self._history.keys())


# Singleton instance
conversation_memory = ConversationMemory()
