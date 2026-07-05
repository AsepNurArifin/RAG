-- ============================================
-- EnterpriseMind AI — Supabase Migration
-- ============================================
-- Jalankan script ini di Supabase SQL Editor
-- untuk membuat tabel yang dibutuhkan.
-- ============================================

-- Tabel metadata dokumen
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'indexed', 'failed')
    ),
    chunk_count INT DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel log query untuk metrik dashboard
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    intent TEXT,
    agents_activated TEXT[],
    latency_ms INT,
    confidence_score FLOAT,
    reflection_count INT DEFAULT 0,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category
    ON documents(category);
CREATE INDEX IF NOT EXISTS idx_query_logs_created
    ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id);

-- Row Level Security (aktifkan untuk production)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policy: service_role bisa full access
CREATE POLICY "Service role full access"
    ON documents FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access"
    ON query_logs FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access"
    ON messages FOR ALL
    USING (true)
    WITH CHECK (true);
