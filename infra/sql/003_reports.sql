CREATE TABLE IF NOT EXISTS weekly_reports (
    id BIGSERIAL PRIMARY KEY,
    report_week TEXT NOT NULL,
    report_title TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    report_markdown TEXT NOT NULL,
    report_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'generated'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_reports_report_week
    ON weekly_reports (report_week);

CREATE TABLE IF NOT EXISTS weekly_report_items (
    id BIGSERIAL PRIMARY KEY,
    weekly_report_id BIGINT NOT NULL REFERENCES weekly_reports (id) ON DELETE CASCADE,
    event_id BIGINT NOT NULL REFERENCES normalized_events (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    section_name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weekly_report_items_report_id
    ON weekly_report_items (weekly_report_id);
