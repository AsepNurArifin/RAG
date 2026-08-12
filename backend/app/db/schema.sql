-- EnterpriseMind AI Database Schema
-- Urutan CREATE TABLE mengikuti dependency (referenced table dibuat lebih dulu).

-- users: application users
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
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

-- documents: uploaded document metadata
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'indexed', 'failed')),
    chunk_count INTEGER DEFAULT 0,
    storage_object_name TEXT,
    file_size_bytes BIGINT DEFAULT 0,
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

-- chunk_hashes: stored SHA-256 hashes of chunks for Tier-1 deduplication
CREATE TABLE IF NOT EXISTS chunk_hashes (
    hash VARCHAR(64) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

