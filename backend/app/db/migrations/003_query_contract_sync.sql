-- Migration 003: Query contract sync (BE-FE integration)
-- Menyelaraskan persistensi dengan kontrak live response:
-- - messages: follow_up_suggestions, intent, intent_type, reflection_count,
--             request_id, trace_id, status, error_code
-- - query_logs: request_id, trace_id, status, session_id (audit trail)
-- Additive only — aman untuk database existing.

-- ------------------------------------------------------------------ #
-- messages: simpan respons lengkap agar history identik dengan live
-- ------------------------------------------------------------------ #
ALTER TABLE messages ADD COLUMN IF NOT EXISTS follow_up_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS intent TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS intent_type TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS reflection_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS request_id TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS trace_id TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS error_code TEXT;

-- ------------------------------------------------------------------ #
-- query_logs: korelasi audit (user/session/request/trace)
-- ------------------------------------------------------------------ #
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS request_id TEXT;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS trace_id TEXT;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_messages_request_id ON messages(request_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_request_id ON query_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id);
