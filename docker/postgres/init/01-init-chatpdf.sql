CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER GENERATED ALWAYS AS (char_length(content)) STORED,
    embedding VECTOR(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_document_chunk UNIQUE (document_id, page_number, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_documents_file_name
    ON documents (file_name);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_page_number
    ON document_chunks (page_number);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_l2
    ON document_chunks
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);

ANALYZE documents;
ANALYZE document_chunks;
