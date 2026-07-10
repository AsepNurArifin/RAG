"""
Conversation Memory — EnterpriseMind AI.

Short-term conversation memory: menyimpan riwayat percakapan
dalam sesi aktif agar sistem bisa merujuk pada konteks sebelumnya.

Ref: FR4.1 (riwayat dalam sesi), FR4.2 (merujuk konteks sebelumnya)

Usage:
    from app.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory(backend="memory")
    memory.add_message("session-123", "user", "Berapa cuti tahunan?")
    memory.add_message("session-123", "assistant", "12 hari kerja...")
    history = memory.get_history("session-123")
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 20


class ConversationMemory:
    """
    Conversation history manager — backend opsional (memory / supabase / redis).

    Default: in-memory (cocok untuk development / single-instance).
    Production: gunakan backend supabase atau redis untuk persistensi.
    """

    def __init__(
        self,
        max_history: int = MAX_HISTORY_LENGTH,
        backend: str = "memory",
    ):
        self._max_history = max_history
        self._backend = backend
        self._history: dict[str, list[dict]] = defaultdict(list)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._backend == "memory":
            self._add_to_memory(session_id, message)
        elif self._backend == "supabase":
            self._add_to_supabase(session_id, message)
        else:
            logger.warning("Backend '%s' tidak dikenal, fallback ke memory", self._backend)
            self._add_to_memory(session_id, message)

    def _add_to_memory(self, session_id: str, message: dict) -> None:
        self._history[session_id].append(message)

        if len(self._history[session_id]) > self._max_history:
            self._history[session_id] = self._history[session_id][
                -self._max_history :
            ]

        logger.debug(
            "Pesan ditambahkan (memory): session=%s, role=%s, total=%d",
            session_id,
            message["role"],
            len(self._history[session_id]),
        )

    def _add_to_supabase(self, session_id: str, message: dict) -> None:
        try:
            from app.core.supabase_client import get_supabase_client

            client = get_supabase_client()

            conv_result = (
                client.table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .execute()
            )

            if not conv_result.data:
                conv_insert = (
                    client.table("conversations")
                    .insert({"session_id": session_id})
                    .execute()
                )
                conv_id = conv_insert.data[0]["id"]
            else:
                conv_id = conv_result.data[0]["id"]

            client.table("messages").insert({
                "conversation_id": conv_id,
                "role": message["role"],
                "content": message["content"],
            }).execute()

            logger.debug(
                "Pesan ditambahkan (supabase): session=%s, role=%s",
                session_id,
                message["role"],
            )

        except Exception as e:
            logger.warning("Gagal simpan ke Supabase, fallback memory: %s", e)
            self._add_to_memory(session_id, message)

    def get_history(self, session_id: str) -> list[dict]:
        if self._backend == "supabase":
            return self._get_history_from_supabase(session_id)
        return self._history.get(session_id, [])

    def _get_history_from_supabase(self, session_id: str) -> list[dict]:
        try:
            from app.core.supabase_client import get_supabase_client

            client = get_supabase_client()
            conv_result = (
                client.table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .execute()
            )

            if not conv_result.data:
                return []

            conv_id = conv_result.data[0]["id"]
            msg_result = (
                client.table("messages")
                .select("*")
                .eq("conversation_id", conv_id)
                .order("created_at")
                .limit(self._max_history)
                .execute()
            )

            return [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("created_at", ""),
                }
                for msg in msg_result.data
            ]

        except Exception as e:
            logger.warning("Gagal baca dari Supabase: %s", e)
            return self._history.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        if session_id in self._history:
            del self._history[session_id]
            logger.info("Session dihapus: %s", session_id)

    def get_active_sessions(self) -> list[str]:
        return list(self._history.keys())


conversation_memory = ConversationMemory()
