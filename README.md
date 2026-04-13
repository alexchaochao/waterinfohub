# WaterInfoHub

WaterInfoHub is a lightweight intelligence pipeline for smart water market monitoring.

Current scope:

- Monitor standards and regulation updates
- Track competitor announcements and analyze signals
- Reserve tender tracking for phase two
- Generate a weekly report with source attribution on every item

## Project layout

- apps/api: FastAPI entrypoint
- apps/worker: scheduled pipeline entrypoint
- configs/sources: source registry
- configs/prompts: LLM prompt templates
- configs/scoring: event scoring rules
- infra/sql: database schema and reserved phase-two tables
- src: collectors, parsers, pipelines, models, and services
- data/reports: generated markdown output

## First milestone

The MVP should do four things reliably:

1. fetch source pages and store raw documents
2. normalize raw documents into structured events
3. score and deduplicate events
4. generate a weekly markdown report with source links

## Suggested run order

1. Install dependencies
2. Configure environment variables
3. Run Alembic migrations
4. Fill source lists in configs/sources
5. Run the ingest worker daily
6. Run the weekly report pipeline every week and publish the generated markdown

## Local commands

```bash
python -m pip install -e .
alembic upgrade head
python -m apps.worker.main
python -m apps.worker.main --scheduler
python -m apps.worker.main --weekly-report
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## Current pipeline status

- ingest: fetch configured source pages into raw_documents
- normalize: convert new raw_documents into normalized_events, standard_events, competitor_events, and event_sources
  - LLM integration: For standard and competitor events, summary and impact_analysis fields are extracted via LLM (OpenAI-compatible API, prompt in configs/prompts), with local fallback if LLM unavailable.
- weekly-report: generate markdown from normalized_events, persist weekly_reports, and write report files to data/reports
- worker: supports one-off pipeline runs and long-lived scheduled mode
- api endpoints:
	- POST /jobs/ingest/run
	- POST /jobs/normalize/run
	- POST /jobs/pipeline/run
	- POST /jobs/weekly-report/run

## Environment variables

Recommended variables:

- DATABASE_URL
- LLM_BASE_URL
- LLM_API_KEY
- LLM_MODEL
- REPORT_OUTPUT_DIR

## Notes

- The project keeps raw documents and normalized events separate to preserve traceability.
- Tender tracking is reserved in schema and directory structure but is not wired into the MVP yet.
- Alembic revision 20260413_0002 adds query-oriented fields and indexes for source tracing, weekly ranking, full-text search, and vector search.

## Linux deployment

- Read cloud readiness checklist: docs/linux-cloud-readiness.md
- Docker production template: infra/docker/docker-compose.prod.yml
- Systemd templates: infra/systemd/
- Linux bootstrap script: scripts/linux-bootstrap.sh
