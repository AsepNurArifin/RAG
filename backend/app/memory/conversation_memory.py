"""
Conversation Memory — EnterpriseMind AI.

Short-term conversation memory: menyimpan riwayat percakapan
dalam sesi aktif agar sistem bisa merujuk pada konteks sebelumnya.

Backends:
- "memory": In-memory (development, single-instance)
- "postgresql": PostgreSQL (production, persistent)

Usage:
    from app.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory(backend="memory")
    memory.add_message("session-123", "user", "Berapa cuti tahunan?")
    history = memory.get_history("session-123")
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 20


class ConversationMemory:
    """Conversation history manager. Backend: memory or postgresql."""

    def __init__(self, max_history: int = MAX_HISTORY_LENGTH, backend: str = "memory"):
        self._max_history = max_history
        self._backend = backend
        self._history: dict[str, list[dict]] = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._backend == "memory":
            self._add_to_memory(session_id, message)
        elif self._backend == "postgresql":
            self._add_to_postgresql(session_id, message)
        else:
            logger.warning("Backend '%s' tidak dikenal, fallback ke memory", self._backend)
            self._add_to_memory(session_id, message)

    def _add_to_memory(self, session_id: str, message: dict) -> None:
        self._history[session_id].append(message)
        if len(self._history[session_id]) > self._max_history:
            self._history[session_id] = self._history[session_id][-self._max_history:]
        logger.debug("Pesan ditambahkan (memory): session=%s, role=%s", session_id, message["role"])

    def _add_to_postgresql(self, session_id: str, message: dict) -> None:
        try:
            import asyncio
            from app.core.postgres_client import fetch_one

            async def _save():
                conv = await fetch_one("SELECT id FROM conversations WHERE session_id = $1", session_id)
                if not conv:
                    conv = await fetch_one(
                        "INSERT INTO conversations (session_id) VALUES ($1) RETURNING id", session_id
                    )
                await fetch_one(
                    "INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3) RETURNING id",
                    conv["id"], message["role"], message["content"],
                )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_save())
            else:
                loop.run_until_complete(_save())

            logger.debug("Pesan ditambahkan (postgresql): session=%s, role=%s", session_id, message["role"])
        except Exception as e:
            logger.warning("Gagal simpan ke PostgreSQL, fallback memory: %s", e)
            self._add_to_memory(session_id, message)

    def get_history(self, session_id: str) -> list[dict]:
        if self._backend == "postgresql":
            return self._get_history_from_postgresql(session_id)
        return self._history.get(session_id, [])

    def _get_history_from_postgresql(self, session_id: str) -> list[dict]:
        try:
            import asyncio
            from app.core.postgres_client import fetch_one, fetch_all

            async def _fetch():
                conv = await fetch_one("SELECT id FROM conversations WHERE session_id = $1", session_id)
                if not conv:
                    return []
                messages = await fetch_all(
                    "SELECT role, content, created_at FROM messages WHERE conversation_id = $1 ORDER BY created_at LIMIT $2",
                    conv["id"], self._max_history,
                )
                return [{"role": m["role"], "content": m["content"], "timestamp": str(m.get("created_at", ""))} for m in messages]

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return []
            return loop.run_until_complete(_fetch())
        except Exception as e:
            logger.warning("Gagal baca dari PostgreSQL: %s", e)
            return self._history.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        if session_id in self._history:
            del self._history[session_id]
            logger.info("Session dihapus: %s", session_id)

    def get_active_sessions(self) -> list[str]:
        return list(self._history.keys())


conversation_memory = ConversationMemory()
