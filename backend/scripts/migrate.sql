-- EnterpriseMind AI — PostgreSQL Migration Script
-- Run: psql -U em_user -d enterprisemind -f scripts/migrate.sql

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    token_version INTEGER DEFAULT 1,
    department VARCHAR(100),
    clearance_level INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    category VARCHAR(100) DEFAULT 'uncategorized',
    status VARCHAR(50) DEFAULT 'pending',
    chunk_count INTEGER DEFAULT 0,
    storage_object_name TEXT,
    file_size_bytes BIGINT DEFAULT 0,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    confidence_score FLOAT,
    action_items JSONB DEFAULT '[]'::jsonb,
    follow_up_suggestions JSONB DEFAULT '[]'::jsonb,
    intent VARCHAR(100),
    intent_type VARCHAR(100),
    reflection_count INTEGER DEFAULT 0,
    request_id TEXT,
    trace_id TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    error_code TEXT,
    latency_ms INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Query logs table (for dashboard metrics)
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    intent VARCHAR(100),
    agents_activated JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    confidence_score FLOAT,
    reflection_count INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    estimated_cost_usd FLOAT DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    usage_details JSONB DEFAULT '{}'::jsonb,
    request_id TEXT,
    trace_id TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    session_id TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Parent chunks table (for production parent-child storage)
CREATE TABLE IF NOT EXISTS parent_chunks (
    id VARCHAR(255) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    chunk_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_intent ON query_logs(intent);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_parent_chunks_document ON parent_chunks(document_id);

-- chunk_hashes: stored SHA-256 hashes of chunks for Tier-1 deduplication
CREATE TABLE IF NOT EXISTS chunk_hashes (
    hash VARCHAR(64) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunk_hashes_hash ON chunk_hashes(hash);

-- Admin awal TIDAK lagi di-seed dengan password publik.
-- Buat admin pertama lewat environment (lihat README):
--   BOOTSTRAP_ADMIN_EMAIL=admin@company.com
--   BOOTSTRAP_ADMIN_PASSWORD=<password-kuat-minimal-12-karakter>
