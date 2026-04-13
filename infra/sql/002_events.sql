CREATE TABLE IF NOT EXISTS normalized_events (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_name TEXT,
    event_title TEXT,
    summary TEXT,
    region TEXT,
    country TEXT,
    technologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    importance_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    signal_strength DOUBLE PRECISION NOT NULL DEFAULT 0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    published_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dedupe_key TEXT NOT NULL,
    embedding VECTOR(1536)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_normalized_events_dedupe_key
    ON normalized_events (dedupe_key);

CREATE INDEX IF NOT EXISTS idx_normalized_events_domain
    ON normalized_events (domain);

CREATE INDEX IF NOT EXISTS idx_normalized_events_published_at
    ON normalized_events (published_at DESC);

CREATE TABLE IF NOT EXISTS event_sources (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES normalized_events (id) ON DELETE CASCADE,
    raw_document_id BIGINT NOT NULL REFERENCES raw_documents (id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    quote_text TEXT,
    extraction_confidence DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_event_sources_event_id
    ON event_sources (event_id);

CREATE TABLE IF NOT EXISTS standard_events (
    event_id BIGINT PRIMARY KEY REFERENCES normalized_events (id) ON DELETE CASCADE,
    standard_no TEXT,
    standard_name TEXT,
    standard_scope TEXT,
    action_type TEXT,
    organization TEXT
);

CREATE TABLE IF NOT EXISTS competitor_events (
    event_id BIGINT PRIMARY KEY REFERENCES normalized_events (id) ON DELETE CASCADE,
    company_name TEXT,
    market TEXT,
    strategic_intent TEXT,
    impact_analysis TEXT
);
