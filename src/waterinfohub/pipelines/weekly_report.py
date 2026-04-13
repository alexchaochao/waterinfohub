from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import delete, select

from waterinfohub.core.settings import settings
from waterinfohub.db.models import EventSource, NormalizedEvent, WeeklyReport, WeeklyReportItem
from waterinfohub.db.session import get_session
from waterinfohub.services.report_renderer import (
    ReportItem,
    build_key_conclusions,
    render_weekly_report,
    to_report_json,
)
from waterinfohub.services.scoring import load_scoring_rules


@dataclass(slots=True)
class WeeklyReportStats:
    report_week: str
    selected: int
    body_items: int
    appendix_items: int
    file_path: str


def run_weekly_report(config_dir: Path, reference_date: date | None = None) -> WeeklyReportStats:
    current_date = reference_date or date.today()
    week_start, week_end, report_week = _resolve_week_window(current_date)
    rules = load_scoring_rules(config_dir)
    body_threshold = float(rules["thresholds"]["weekly_body_min_importance"])
    appendix_threshold = float(rules["thresholds"]["weekly_appendix_min_importance"])

    with get_session() as session:
        events = session.scalars(
            select(NormalizedEvent)
            .where(NormalizedEvent.first_seen_at >= week_start)
            .where(NormalizedEvent.first_seen_at < week_end)
            .where(NormalizedEvent.importance_score >= appendix_threshold)
            .order_by(NormalizedEvent.importance_score.desc(), NormalizedEvent.signal_strength.desc())
        ).all()

        items = [_to_report_item(session, event) for event in events]
        body_items = [item for item in items if item.importance_score >= body_threshold]
        selected_items = body_items or items[:10]
        conclusions = build_key_conclusions(selected_items)
        report_title = f"{report_week} | Global Smart Water Intelligence Weekly Report"
        markdown = render_weekly_report(report_title, conclusions, selected_items)
        report_json = to_report_json(report_title, conclusions, selected_items)

        report = session.scalar(select(WeeklyReport).where(WeeklyReport.report_week == report_week))
        if report is None:
            report = WeeklyReport(
                report_week=report_week,
                report_title=report_title,
                report_markdown=markdown,
                report_json=report_json,
                status="generated",
            )
            session.add(report)
            session.flush()
        else:
            report.report_title = report_title
            report.report_markdown = markdown
            report.report_json = report_json
            report.status = "generated"
            session.execute(
                delete(WeeklyReportItem).where(WeeklyReportItem.weekly_report_id == report.id)
            )
            session.flush()

        for position, item in enumerate(selected_items, start=1):
            session.add(
                WeeklyReportItem(
                    weekly_report_id=report.id,
                    event_id=item.event_id,
                    position=position,
                    section_name=item.section,
                )
            )

        session.commit()

    output_path = _write_report_file(report_week, markdown)
    return WeeklyReportStats(
        report_week=report_week,
        selected=len(selected_items),
        body_items=len(body_items),
        appendix_items=len(items),
        file_path=str(output_path),
    )


def _resolve_week_window(current_date: date) -> tuple[datetime, datetime, str]:
    iso_year, iso_week, iso_weekday = current_date.isocalendar()
    week_start_date = current_date - timedelta(days=iso_weekday - 1)
    week_end_date = week_start_date + timedelta(days=7)
    week_start = datetime.combine(week_start_date, time.min, tzinfo=UTC)
    week_end = datetime.combine(week_end_date, time.min, tzinfo=UTC)
    return week_start, week_end, f"{iso_year}-W{iso_week:02d}"


def _to_report_item(session, event: NormalizedEvent) -> ReportItem:
    source = session.scalar(
        select(EventSource)
        .where(EventSource.event_id == event.id)
        .order_by(EventSource.extraction_confidence.desc(), EventSource.id.asc())
    )
    section = _map_section(event.domain)
    return ReportItem(
        event_id=event.id,
        section=section,
        title=event.event_title or event.entity_name or f"Event {event.id}",
        summary=event.summary or "No summary available.",
        source_name=source.source_name if source else "Unknown",
        source_url=source.source_url if source else "",
        published_at=event.published_at.isoformat() if event.published_at else None,
        confidence=event.confidence,
        signal_strength=event.signal_strength,
        importance_score=event.importance_score,
    )


def _map_section(domain: str) -> str:
    if domain == "standard":
        return "standards"
    if domain == "competitor":
        return "competitors"
    return "tenders"


def _write_report_file(report_week: str, markdown: str) -> Path:
    output_dir = settings.report_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report_week}.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
