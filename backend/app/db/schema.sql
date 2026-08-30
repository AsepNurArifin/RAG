-- EnterpriseMind AI Database Schema
-- Urutan CREATE TABLE mengikuti dependency (referenced table dibuat lebih dulu).
-- Ini adalah baseline fresh install. Perubahan incremental ada di app/db/migrations/*.sql.

-- users: application users
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    token_version INTEGER DEFAULT 1,
    department TEXT,
    clearance_level INTEGER DEFAULT 1,
    must_change_password BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- documents: uploaded document metadata
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'indexed', 'failed', 'uploading', 'stored', 'deleting', 'delete_failed', 'deleted')),
    chunk_count INTEGER DEFAULT 0,
    storage_object_name TEXT,
    file_size_bytes BIGINT DEFAULT 0,
    uploaded_by UUID REFERENCES users(id),
    delete_error TEXT,
    delete_retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- conversations: conversation sessions
CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- messages: messages in conversations
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    confidence_score FLOAT,
    action_items JSONB DEFAULT '[]'::jsonb,
    follow_up_suggestions JSONB DEFAULT '[]'::jsonb,
    intent TEXT,
    intent_type TEXT,
    reflection_count INTEGER DEFAULT 0,
    request_id TEXT,
    trace_id TEXT,
    status TEXT DEFAULT 'completed',
    error_code TEXT,
    latency_ms INTEGER,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- query_logs: interaction logs for dashboard metrics
CREATE TABLE query_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    intent TEXT,
    agents_activated JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    confidence_score FLOAT,
    reflection_count INTEGER DEFAULT 0,
    model_used TEXT,
    estimated_cost_usd FLOAT DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    usage_details JSONB DEFAULT '{}'::jsonb,
    request_id TEXT,
    trace_id TEXT,
    status TEXT DEFAULT 'completed',
    session_id TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- evaluation_results: RAGAS evaluation results
CREATE TABLE evaluation_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    query TEXT NOT NULL,
    expected_answer TEXT,
    actual_answer TEXT,
    faithfulness FLOAT,
    answer_relevance FLOAT,
    context_precision FLOAT,
    model_type TEXT CHECK (model_type IN ('naive_rag', 'agentic_rag')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- parent_chunks: production parent-child storage
CREATE TABLE IF NOT EXISTS parent_chunks (
    id VARCHAR(255) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    chunk_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- chunk_hashes: stored SHA-256 hashes of chunks for Tier-1 deduplication
CREATE TABLE IF NOT EXISTS chunk_hashes (
    hash VARCHAR(64) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_storage_object ON documents(storage_object_name);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_intent ON query_logs(intent);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_request_id ON messages(request_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_request_id ON query_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_parent_chunks_document ON parent_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_hashes_document ON chunk_hashes(document_id);
