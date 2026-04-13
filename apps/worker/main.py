from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from waterinfohub.core.settings import settings
from waterinfohub.pipelines.ingest import run_ingest
from waterinfohub.pipelines.normalize import run_normalization
from waterinfohub.pipelines.weekly_report import run_weekly_report


def main() -> None:
    parser = argparse.ArgumentParser(description="WaterInfoHub worker")
    parser.add_argument("--scheduler", action="store_true", help="Run as a long-lived scheduler")
    parser.add_argument("--weekly-report", action="store_true", help="Generate weekly report once")
    args = parser.parse_args()

    if args.scheduler:
        run_scheduler()
        return

    if args.weekly_report:
        run_weekly_report_once()
        return

    run_pipeline_once()


def run_pipeline_once() -> None:
    now = datetime.now(timezone.utc).isoformat()
    project_root = _project_root()
    ingest_stats = run_ingest(project_root / "configs")
    normalize_stats = run_normalization(project_root / "configs")
    print(
        f"worker run at {now} | fetched={ingest_stats.fetched} inserted={ingest_stats.inserted} "
        f"duplicated={ingest_stats.duplicated} failed={ingest_stats.failed} "
        f"| normalized_processed={normalize_stats.processed} normalized={normalize_stats.normalized} "
        f"skipped={normalize_stats.skipped} duplicate_events={normalize_stats.duplicated} "
        f"normalize_failed={normalize_stats.failed}"
    )


def run_weekly_report_once() -> None:
    now = datetime.now(timezone.utc).isoformat()
    project_root = _project_root()
    stats = run_weekly_report(project_root / "configs")
    print(
        f"weekly report run at {now} | report_week={stats.report_week} selected={stats.selected} "
        f"body_items={stats.body_items} appendix_items={stats.appendix_items} file_path={stats.file_path}"
    )


def run_scheduler() -> None:
    scheduler = BlockingScheduler(timezone=settings.worker_timezone)
    scheduler.add_job(
        run_pipeline_once,
        CronTrigger(
            hour=settings.worker_daily_hour,
            minute=settings.worker_daily_minute,
            timezone=settings.worker_timezone,
        ),
        id="daily_pipeline",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_report_once,
        CronTrigger(
            day_of_week=settings.worker_weekly_day_of_week,
            hour=settings.worker_weekly_hour,
            minute=settings.worker_weekly_minute,
            timezone=settings.worker_timezone,
        ),
        id="weekly_report",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    print(
        "worker scheduler started "
        f"(timezone={settings.worker_timezone}, "
        f"daily={settings.worker_daily_hour:02d}:{settings.worker_daily_minute:02d}, "
        f"weekly={settings.worker_weekly_day_of_week} "
        f"{settings.worker_weekly_hour:02d}:{settings.worker_weekly_minute:02d})"
    )
    scheduler.start()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    main()
