-- ============================================
-- EnterpriseMind AI — Supabase Migration
-- ============================================
-- SUMBER KEBENARAN: app/db/schema.sql
-- Idempotent: aman dijalankan berulang kali (CREATE TABLE IF NOT EXISTS,
-- ALTER TABLE ... ADD COLUMN IF NOT EXISTS).
-- Jalankan di Supabase SQL Editor.
-- ============================================

-- Tabel users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    token_version INTEGER DEFAULT 1,
    department TEXT,
    clearance_level INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel metadata dokumen
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'indexed', 'failed')
    ),
    chunk_count INTEGER DEFAULT 0,
    storage_object_name TEXT,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel log query untuk metrik dashboard
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Tabel conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Tabel hasil evaluasi RAGAS
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    expected_answer TEXT,
    actual_answer TEXT,
    faithfulness FLOAT,
    answer_relevance FLOAT,
    context_precision FLOAT,
    model_type TEXT CHECK (model_type IN ('naive_rag', 'agentic_rag')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel hash deduplication Tier-1
CREATE TABLE IF NOT EXISTS chunk_hashes (
    hash VARCHAR(64) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel draft extraksi graph (menunggu review sebelum commit ke Neo4j)
CREATE TABLE IF NOT EXISTS graph_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    draft_data JSONB NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (
        status IN ('pending', 'approved', 'rejected', 'committed')
    ),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Upgrade idempotent untuk database lama
-- (jika tabel sudah dibuat dengan struktur versi sebelumnya)
-- ============================================

-- users: pindahkan kolom hashed_password -> password_hash jika DB lama
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS clearance_level INTEGER DEFAULT 1;

-- Perbaiki constraint role lama ('user','admin') menjadi ('admin','analyst','viewer')
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'analyst', 'viewer'));

-- conversations: tambah session_id jika DB lama
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS session_id TEXT;

-- evaluation_results: migrasi struktur lama -> baru (opsional, jika DB lama punya kolom answer/ground_truth)
ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS expected_answer TEXT;
ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS actual_answer TEXT;
ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS model_type TEXT CHECK (model_type IN ('naive_rag', 'agentic_rag'));

-- Dokumentasi migrasi data (hanya jika migrasi dari DB yang memakai hashed_password):
--   UPDATE users SET password_hash = hashed_password WHERE password_hash IS NULL;
--   ALTER TABLE users DROP COLUMN IF EXISTS hashed_password;

-- ============================================
-- Index untuk performa query
-- ============================================
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_chunk_hashes_document ON chunk_hashes(document_id);
CREATE INDEX IF NOT EXISTS idx_graph_drafts_status ON graph_drafts(status);

-- ============================================
-- Row Level Security (aktifkan untuk production)
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunk_hashes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_drafts ENABLE ROW LEVEL SECURITY;

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

DROP POLICY IF EXISTS "Service role full access on chunk_hashes" ON chunk_hashes;
CREATE POLICY "Service role full access on chunk_hashes" ON chunk_hashes TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on graph_drafts" ON graph_drafts;
CREATE POLICY "Service role full access on graph_drafts" ON graph_drafts TO service_role USING (true) WITH CHECK (true);
