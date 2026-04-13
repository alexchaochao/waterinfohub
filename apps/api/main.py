from pathlib import Path

from fastapi import FastAPI

from waterinfohub.pipelines.ingest import run_ingest
from waterinfohub.pipelines.normalize import run_normalization
from waterinfohub.pipelines.weekly_report import run_weekly_report


app = FastAPI(title="WaterInfoHub API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/ingest/run")
def trigger_ingest() -> dict[str, int]:
    project_root = Path(__file__).resolve().parents[2]
    stats = run_ingest(project_root / "configs")
    return {
        "fetched": stats.fetched,
        "inserted": stats.inserted,
        "duplicated": stats.duplicated,
        "failed": stats.failed,
    }


@app.post("/jobs/normalize/run")
def trigger_normalize() -> dict[str, int]:
    project_root = Path(__file__).resolve().parents[2]
    stats = run_normalization(project_root / "configs")
    return {
        "processed": stats.processed,
        "normalized": stats.normalized,
        "skipped": stats.skipped,
        "duplicated": stats.duplicated,
        "failed": stats.failed,
    }


@app.post("/jobs/pipeline/run")
def trigger_pipeline() -> dict[str, int]:
    project_root = Path(__file__).resolve().parents[2]
    ingest_stats = run_ingest(project_root / "configs")
    normalize_stats = run_normalization(project_root / "configs")
    return {
        "fetched": ingest_stats.fetched,
        "inserted": ingest_stats.inserted,
        "ingest_duplicated": ingest_stats.duplicated,
        "ingest_failed": ingest_stats.failed,
        "processed": normalize_stats.processed,
        "normalized": normalize_stats.normalized,
        "skipped": normalize_stats.skipped,
        "normalize_duplicated": normalize_stats.duplicated,
        "normalize_failed": normalize_stats.failed,
    }


@app.post("/jobs/weekly-report/run")
def trigger_weekly_report() -> dict[str, int | str]:
    project_root = Path(__file__).resolve().parents[2]
    stats = run_weekly_report(project_root / "configs")
    return {
        "report_week": stats.report_week,
        "selected": stats.selected,
        "body_items": stats.body_items,
        "appendix_items": stats.appendix_items,
        "file_path": stats.file_path,
    }
