CREATE TABLE IF NOT EXISTS tender_events (
    event_id BIGINT PRIMARY KEY REFERENCES normalized_events (id) ON DELETE CASCADE,
    project_name TEXT,
    country TEXT,
    procurement_org TEXT,
    award_company TEXT,
    amount TEXT,
    currency TEXT
);
