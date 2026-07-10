-- ============================================
-- EnterpriseMind AI — Supabase Migration
-- ============================================
-- Jalankan script ini di Supabase SQL Editor
-- untuk membuat tabel yang dibutuhkan.
-- ============================================

-- Tabel users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    token_version INT NOT NULL DEFAULT 1
);

-- Tabel conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Analysis',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel metadata dokumen
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'indexed', 'failed')
    ),
    file_path TEXT,
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
    agents_activated JSONB,
    latency_ms INT,
    confidence_score FLOAT,
    reflection_count INT DEFAULT 0,
    model_used TEXT,
    estimated_cost_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB,
    confidence_score FLOAT,
    action_items JSONB,
    latency_ms INT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel hasil evaluasi (opsional jika dipakai Ragas)
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    context JSONB,
    ground_truth TEXT,
    faithfulness FLOAT,
    answer_relevancy FLOAT,
    context_precision FLOAT,
    context_recall FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- Row Level Security (aktifkan untuk production)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_results ENABLE ROW LEVEL SECURITY;

-- Policy: service_role bisa full access (Bypass RLS for backend service)
DROP POLICY IF EXISTS "Service role full access on users" ON users;
CREATE POLICY "Service role full access on users" ON users TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on conversations" ON conversations;
CREATE POLICY "Service role full access on conversations" ON conversations TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on documents" ON documents;
CREATE POLICY "Service role full access on documents" ON documents TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on query_logs" ON query_logs;
CREATE POLICY "Service role full access on query_logs" ON query_logs TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on messages" ON messages;
CREATE POLICY "Service role full access on messages" ON messages TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on evaluation_results" ON evaluation_results;
CREATE POLICY "Service role full access on evaluation_results" ON evaluation_results TO service_role USING (true) WITH CHECK (true);

-- Alter table to add token_version if running incremental update
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 1;
