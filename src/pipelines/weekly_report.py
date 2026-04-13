from datetime import date

from services.report_renderer import ReportItem, render_weekly_report


def build_placeholder_weekly_report() -> str:
    report_title = f"{date.today().isoformat()} Weekly Smart Water Intelligence Report"
    items = [
        ReportItem(
            section="standards",
            title="Reserved sample item",
            summary="Replace this placeholder with normalized events from the database.",
            source_name="Reserved",
            source_url="https://example.com",
            confidence=0.0,
            signal_strength=0.0,
        )
    ]
    return render_weekly_report(report_title, items)
