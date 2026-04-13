from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ReportItem:
    event_id: int
    section: str
    title: str
    summary: str
    source_name: str
    source_url: str
    published_at: str | None
    confidence: float
    signal_strength: float
    importance_score: float


def render_weekly_report(report_title: str, conclusions: list[str], items: Iterable[ReportItem]) -> str:
    grouped: dict[str, list[ReportItem]] = {
        "standards": [],
        "competitors": [],
        "tenders": [],
    }
    appendix: list[ReportItem] = []

    for item in items:
        appendix.append(item)
        grouped.setdefault(item.section, []).append(item)

    lines = [f"# {report_title}", "", "## Key Conclusions", ""]
    if conclusions:
        lines.extend([f"- {conclusion}" for conclusion in conclusions])
    else:
        lines.append("- No high-signal events met the reporting threshold this week.")

    lines.extend(_render_section("Standards and Regulation Updates", grouped.get("standards", [])))
    lines.extend(_render_section("Competitor Developments", grouped.get("competitors", [])))
    lines.extend(_render_section("Tender Tracking", grouped.get("tenders", []), reserved=True))
    lines.extend(_render_appendix(appendix))
    return "\n".join(lines).strip() + "\n"


def build_key_conclusions(items: list[ReportItem]) -> list[str]:
    if not items:
        return []

    conclusions: list[str] = []
    section_counts = Counter(item.section for item in items)
    tech_counter = Counter()
    for item in items:
        text = f"{item.title} {item.summary}".lower()
        if "nb-iot" in text:
            tech_counter["NB-IoT"] += 1
        if "lora" in text or "lorawan" in text:
            tech_counter["LoRaWAN"] += 1
        if "m-bus" in text:
            tech_counter["M-Bus"] += 1

    if section_counts.get("standards"):
        conclusions.append(
            f"This week included {section_counts['standards']} standards or regulation signals worth tracking."
        )
    if section_counts.get("competitors"):
        conclusions.append(
            f"Competitor activity remained active with {section_counts['competitors']} notable company events."
        )
    if tech_counter:
        tech_name, tech_count = tech_counter.most_common(1)[0]
        conclusions.append(
            f"{tech_name} appeared most frequently in this week's tracked signals with {tech_count} mentions."
        )
    top_item = sorted(items, key=lambda item: (item.importance_score, item.signal_strength), reverse=True)[0]
    conclusions.append(
        f"The highest-priority signal this week was {top_item.title} from {top_item.source_name}."
    )
    return conclusions[:4]


def to_report_json(report_title: str, conclusions: list[str], items: list[ReportItem]) -> dict:
    return {
        "report_title": report_title,
        "conclusions": conclusions,
        "items": [asdict(item) for item in items],
    }


def _render_section(title: str, items: list[ReportItem], reserved: bool = False) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not items:
        if reserved:
            lines.append("- Reserved for phase two. No tender events are published yet.")
        else:
            lines.append("- No events met the reporting threshold in this section.")
        return lines

    for item in items:
        lines.append(f"### {item.title}")
        lines.append(f"- Summary: {item.summary}")
        lines.append(f"- Source: {item.source_name} | {item.source_url}")
        if item.published_at:
            lines.append(f"- Published At: {item.published_at}")
        lines.append(f"- Confidence: {item.confidence:.2f}")
        lines.append(f"- Signal Strength: {item.signal_strength:.2f}")
        lines.append(f"- Importance: {item.importance_score:.2f}")
        lines.append("")
    return lines


def _render_appendix(items: list[ReportItem]) -> list[str]:
    lines = ["", "## Appendix", "", "### Event List", ""]
    if not items:
        lines.append("- No events were included in this report.")
        return lines

    for item in items:
        lines.append(
            f"- [{item.section}] {item.title} | {item.source_name} | {item.source_url} | confidence={item.confidence:.2f} | signal={item.signal_strength:.2f}"
        )
    return lines
