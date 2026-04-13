CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS raw_documents (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    language TEXT,
    raw_text TEXT,
    raw_html_path TEXT,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_documents_content_hash
    ON raw_documents (content_hash);

CREATE INDEX IF NOT EXISTS idx_raw_documents_domain
    ON raw_documents (domain);

CREATE INDEX IF NOT EXISTS idx_raw_documents_published_at
    ON raw_documents (published_at DESC);
