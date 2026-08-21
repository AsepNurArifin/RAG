-- EnterpriseMind AI — Migration 001
-- Additive migration untuk hardening & konsistensi storage.
-- Aman dijalankan ulang (idempotent). Jalankan:
--   psql -U postgres -d enterprisemind -f app/db/migrations/001_security_storage_consistency.sql

-- users.must_change_password
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false;

-- documents: status lifecycle baru + uploaded_by + delete metadata
ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES users(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS delete_error TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS delete_retry_count INTEGER NOT NULL DEFAULT 0;

-- Perluas CHECK constraint status dokumen (jika constraint lama masih ada).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'documents'::regclass AND conname = 'documents_status_check'
    ) THEN
        ALTER TABLE documents DROP CONSTRAINT documents_status_check;
        ALTER TABLE documents ADD CONSTRAINT documents_status_check
            CHECK (status IN ('pending', 'processing', 'indexed', 'failed', 'uploading', 'stored', 'deleting', 'delete_failed', 'deleted'));
    END IF;
END $$;

-- query_logs: token & cost detail
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS input_tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS output_tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS total_tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS usage_details JSONB NOT NULL DEFAULT '{}'::jsonb;

-- parent_chunks (jika belum ada di deployment lama)
CREATE TABLE IF NOT EXISTS parent_chunks (
    id VARCHAR(255) PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    chunk_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_storage_object ON documents(storage_object_name);
CREATE INDEX IF NOT EXISTS idx_chunk_hashes_document ON chunk_hashes(document_id);
CREATE INDEX IF NOT EXISTS idx_parent_chunks_document ON parent_chunks(document_id);
