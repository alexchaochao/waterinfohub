from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class ReportItem:
    section: str
    title: str
    summary: str
    source_name: str
    source_url: str
    confidence: float
    signal_strength: float


def render_weekly_report(report_title: str, items: Iterable[ReportItem]) -> str:
    lines = [f"# {report_title}", "", "## Event List", ""]

    for item in items:
        lines.append(f"### {item.title}")
        lines.append(f"- Section: {item.section}")
        lines.append(f"- Summary: {item.summary}")
        lines.append(f"- Source: {item.source_name} | {item.source_url}")
        lines.append(f"- Confidence: {item.confidence:.2f}")
        lines.append(f"- Signal Strength: {item.signal_strength:.2f}")
        lines.append("")

    return "\n".join(lines)
