from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from waterinfohub.core.settings import BASE_DIR
from waterinfohub.db.models import (
    CompetitorEvent,
    EventSource,
    NormalizedEvent,
    RawDocument,
    StandardEvent,
)
from waterinfohub.db.session import get_session
from waterinfohub.services.llm_client import LLMClient, load_prompt
from waterinfohub.services.scoring import clamp_score, load_scoring_rules
from waterinfohub.services.structured_logger import get_structured_logger
from waterinfohub.services.wework_notify import send_wework_message

logger = get_structured_logger("normalize")


TECH_KEYWORDS = {
    "nb-iot": "NB-IoT",
    "lorawan": "LoRaWAN",
    "lora": "LoRa",
    "wmbus": "wM-Bus",
    "wm-bus": "wM-Bus",
    "m-bus": "M-Bus",
    "ami": "AMI",
    "smart water": "smart_water",
    "water meter": "water_meter",
    "metering": "metering",
    "measurement": "measurement",
}

STANDARD_NO_PATTERNS = [
    re.compile(r"\b(OIML\s+[A-Z]?\d+[A-Z0-9\-]*)\b", re.IGNORECASE),
    re.compile(r"\b(IEC\s+\d+(?:-\d+)*(?::\d{4})?)\b", re.IGNORECASE),
    re.compile(r"\b(GB/T\s+\d+(?:\.\d+)?(?:-\d{4})?)\b", re.IGNORECASE),
]


@dataclass(slots=True)
class NormalizationStats:
    processed: int = 0
    normalized: int = 0
    skipped: int = 0
    duplicated: int = 0
    failed: int = 0


def run_normalization(config_dir: Path) -> NormalizationStats:
    rules = load_scoring_rules(config_dir)
    stats = NormalizationStats()

    with get_session() as session:
        documents = session.scalars(
            select(RawDocument).where(RawDocument.status == "new").order_by(RawDocument.id.asc())
        ).all()

        for raw_document in documents:
            stats.processed += 1
            try:
                event_payload = _build_event_payload(raw_document, rules)
                if event_payload is None:
                    raw_document.status = "filtered"
                    session.commit()
                    stats.skipped += 1
                    continue

                event = session.scalar(
                    select(NormalizedEvent).where(
                        NormalizedEvent.dedupe_key == event_payload["dedupe_key"]
                    )
                )
                if event is None:
                    event = NormalizedEvent(**_normalized_event_fields(event_payload))
                    session.add(event)
                    session.flush()
                    _insert_domain_record(session, raw_document, event.id, event_payload)
                    stats.normalized += 1
                else:
                    event.last_seen_at = datetime.now(UTC)
                    stats.duplicated += 1

                _ensure_event_source(session, event.id, raw_document)
                raw_document.status = "normalized"
                session.commit()
            except Exception as exc:
                import traceback

                session.rollback()
                raw_document.status = "error"
                session.add(raw_document)
                session.commit()
                stats.failed += 1
                logger.error(
                    f"Normalize failed for raw_document {getattr(raw_document, 'id', None)}",
                    extra={
                        "extra": {
                            "raw_document_id": getattr(raw_document, "id", None),
                            "source_name": getattr(raw_document, "source_name", None),
                            "source_url": getattr(raw_document, "source_url", None),
                            "exception": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    },
                )

    # 企业微信通知
    from waterinfohub.core.settings import settings
    if getattr(settings, "worker_daily_notify_enabled", True):
        msg = (
            f"【WaterInfoHub 日任务-归一化】\n"
            f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"处理：{stats.processed}，归一化：{stats.normalized}，跳过：{stats.skipped}，重复：{stats.duplicated}，失败：{stats.failed}"
        )
        send_wework_message(msg, getattr(settings, "wework_webhook_url", None))
    return stats


def _normalized_event_fields(payload: dict) -> dict:
    allowed_fields = {
        "domain",
        "event_type",
        "entity_name",
        "event_title",
        "summary",
        "search_text",
        "region",
        "country",
        "technologies",
        "tags",
        "importance_score",
        "signal_strength",
        "confidence",
        "published_at",
        "dedupe_key",
    }
    return {key: value for key, value in payload.items() if key in allowed_fields}


def _build_event_payload(raw_document: RawDocument, rules: dict) -> dict | None:
    raw_text = (raw_document.raw_text or "").strip()
    title = (raw_document.title or raw_document.source_name or "").strip()
    if not raw_text and not title:
        return None

    technologies = _extract_technologies(f"{title} {raw_text}")
    if raw_document.domain == "standard":
        return _build_standard_payload(raw_document, title, raw_text, technologies, rules)
    if raw_document.domain == "competitor":
        return _build_competitor_payload(raw_document, title, raw_text, technologies, rules)
    return None


def _build_standard_payload(
    raw_document: RawDocument,
    title: str,
    raw_text: str,
    technologies: list[str],
    rules: dict,
) -> dict | None:
    searchable = f"{title} {raw_text}".lower()
    if not _is_standard_relevant(searchable):
        return None

    standard_no = _match_standard_no(searchable)
    action_type = _detect_standard_action(searchable)
    tags = sorted(set(technologies + ["standard", action_type]))
    importance = _score_standard_event(searchable, raw_document.source_type, rules)
    confidence = clamp_score(0.65 + (0.1 if standard_no else 0.0) + (0.05 if technologies else 0.0))

    summary = None
    try:
        llm = LLMClient()
        prompt_path = BASE_DIR / "configs" / "prompts" / "standard_extract.md"
        prompt_template = load_prompt(prompt_path)
        prompt = f"{prompt_template}\n\nInput:\nTitle: {title}\nText: {raw_text}"
        llm_result = llm.run_completion(prompt)
        if llm_result:
            parsed = json.loads(llm_result)
            summary = parsed.get("relevance_reason") or parsed.get("standard_name") or None
    except Exception:
        summary = None
    if not summary:
        summary = _summarize_text(title, raw_text)

    dedupe_key = _make_dedupe_key(raw_document.domain, title, standard_no or raw_document.source_url)
    search_text = " ".join(filter(None, [title, summary, standard_no, raw_document.source_name]))

    return {
        "domain": raw_document.domain,
        "event_type": action_type,
        "entity_name": raw_document.source_name,
        "event_title": title,
        "summary": summary,
        "search_text": search_text,
        "region": _guess_region(raw_document.source_name, raw_document.source_host),
        "country": None,
        "technologies": technologies,
        "tags": tags,
        "importance_score": importance,
        "signal_strength": clamp_score((importance + confidence) / 2),
        "confidence": confidence,
        "published_at": raw_document.published_at,
        "dedupe_key": dedupe_key,
        "standard_no": standard_no,
        "standard_name": title,
        "standard_scope": _derive_standard_scope(searchable),
        "action_type": action_type,
        "organization": raw_document.source_name,
    }


def _build_competitor_payload(
    raw_document: RawDocument,
    title: str,
    raw_text: str,
    technologies: list[str],
    rules: dict,
) -> dict | None:
    searchable = f"{title} {raw_text}".lower()
    company_name = _detect_company_name(raw_document.source_name, searchable)
    event_type = _detect_competitor_event_type(searchable)
    tags = sorted(set(technologies + ["competitor", event_type]))
    importance = _score_competitor_event(event_type, raw_document.source_type, rules)
    confidence = clamp_score(0.65 + (0.05 if technologies else 0.0) + (0.05 if company_name else 0.0))

    impact_analysis = None
    try:
        llm = LLMClient()
        prompt_path = BASE_DIR / "configs" / "prompts" / "competitor_analysis.md"
        prompt_template = load_prompt(prompt_path)
        prompt = f"{prompt_template}\n\nInput:\nTitle: {title}\nText: {raw_text}"
        llm_result = llm.run_completion(prompt)
        if llm_result:
            parsed = json.loads(llm_result)
            impact_analysis = parsed.get("impact_analysis")
    except Exception:
        impact_analysis = None
    if not impact_analysis:
        impact_analysis = _infer_impact(event_type, technologies)

    summary = _summarize_text(title, raw_text)
    dedupe_key = _make_dedupe_key(raw_document.domain, company_name or raw_document.source_name, title)
    search_text = " ".join(filter(None, [title, summary, company_name]))

    return {
        "domain": raw_document.domain,
        "event_type": event_type,
        "entity_name": company_name,
        "event_title": title,
        "summary": summary,
        "search_text": search_text,
        "region": None,
        "country": None,
        "technologies": technologies,
        "tags": tags,
        "importance_score": importance,
        "signal_strength": clamp_score((importance + confidence) / 2),
        "confidence": confidence,
        "published_at": raw_document.published_at,
        "dedupe_key": dedupe_key,
        "company_name": company_name,
        "market": _detect_market(searchable),
        "strategic_intent": _infer_strategic_intent(event_type, technologies),
        "impact_analysis": impact_analysis,
    }


def _insert_domain_record(session, raw_document: RawDocument, event_id: int, payload: dict) -> None:
    if raw_document.domain == "standard":
        session.add(
            StandardEvent(
                event_id=event_id,
                standard_no=payload.get("standard_no"),
                standard_name=payload.get("standard_name"),
                standard_scope=payload.get("standard_scope"),
                action_type=payload.get("action_type"),
                organization=payload.get("organization"),
            )
        )
        return

    if raw_document.domain == "competitor":
        session.add(
            CompetitorEvent(
                event_id=event_id,
                company_name=payload.get("company_name"),
                market=payload.get("market"),
                strategic_intent=payload.get("strategic_intent"),
                impact_analysis=payload.get("impact_analysis"),
            )
        )


def _ensure_event_source(session, event_id: int, raw_document: RawDocument) -> None:
    existing = session.scalar(
        select(EventSource).where(
            EventSource.event_id == event_id,
            EventSource.raw_document_id == raw_document.id,
        )
    )
    if existing is not None:
        return

    quote_text = (raw_document.raw_text or "")[:280] or None
    session.add(
        EventSource(
            event_id=event_id,
            raw_document_id=raw_document.id,
            source_url=raw_document.source_url,
            source_name=raw_document.source_name,
            source_type=raw_document.source_type,
            quote_text=quote_text,
            extraction_confidence=0.75,
        )
    )


def _extract_technologies(text: str) -> list[str]:
    lowered = text.lower()
    found = [label for keyword, label in TECH_KEYWORDS.items() if keyword in lowered]
    return sorted(set(found))


def _is_standard_relevant(searchable: str) -> bool:
    include_hits = any(
        keyword in searchable
        for keyword in [
            "water meter",
            "smart water",
            "metering",
            "measurement",
            "nb-iot",
            "lorawan",
            "m-bus",
            "wm-bus",
            "communication protocol",
        ]
    )
    exclude_hits = any(keyword in searchable for keyword in ["food", "medical", "building material"])
    return include_hits and not exclude_hits


def _match_standard_no(text: str) -> str | None:
    for pattern in STANDARD_NO_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).upper()
    return None


def _detect_standard_action(text: str) -> str:
    if any(token in text for token in ["withdrawn", "abolish"]):
        return "withdrawn"
    if any(token in text for token in ["update", "revision", "amendment"]):
        return "update"
    if any(token in text for token in ["consultation", "draft"]):
        return "consultation"
    return "new"


def _derive_standard_scope(text: str) -> str | None:
    if "water" in text:
        return "water_meter"
    if "communication" in text or "protocol" in text:
        return "communication_protocol"
    if "measurement" in text or "metrology" in text:
        return "metrology"
    return None


def _detect_company_name(source_name: str, text: str) -> str | None:
    company_map = {
        "itron": "Itron",
        "landis+gyr": "Landis+Gyr",
        "diehl": "Diehl Metering",
    }
    searchable = f"{source_name} {text}".lower()
    for keyword, label in company_map.items():
        if keyword in searchable:
            return label
    return source_name


def _detect_competitor_event_type(text: str) -> str:
    mapping = [
        ("new_product", ["launch", "introduces", "new product", "release"]),
        ("market_expansion", ["expand", "expansion", "enters", "new market"]),
        ("certification", ["certification", "certified", "approved"]),
        ("award", ["awarded", "wins", "contract", "selected"]),
        ("technology_upgrade", ["upgrade", "enhancement", "advanced", "improved"]),
        ("strategic_partnership", ["partnership", "collaboration", "alliance"]),
        ("investment", ["investment", "acquire", "acquisition"]),
    ]
    for event_type, keywords in mapping:
        if any(keyword in text for keyword in keywords):
            return event_type
    return "technology_upgrade"


def _detect_market(text: str) -> str | None:
    for market in ["france", "germany", "italy", "spain", "uk", "europe", "asia"]:
        if market in text:
            return market.upper() if len(market) == 2 else market.title()
    return None


def _infer_strategic_intent(event_type: str, technologies: list[str]) -> str:
    if event_type == "new_product":
        return "Expand product coverage in smart metering."
    if event_type == "market_expansion":
        return "Strengthen geographic coverage in target utility markets."
    if technologies:
        return f"Reinforce positioning around {', '.join(technologies)}."
    return "Strengthen competitive visibility in utility digitization."


def _infer_impact(event_type: str, technologies: list[str]) -> str:
    if event_type == "award":
        return "This may indicate near-term commercial traction and stronger account penetration."
    if technologies:
        return f"This signals continued market attention on {', '.join(technologies)}."
    return "This is a moderate market signal and should be tracked with follow-on announcements."


def _guess_region(source_name: str, source_host: str | None) -> str | None:
    searchable = f"{source_name} {source_host or ''}".lower()
    if any(token in searchable for token in ["oiml", ".eu", "iec"]):
        return "global"
    if any(token in searchable for token in ["sac", ".cn"]):
        return "cn"
    return None


def _score_standard_event(text: str, source_type: str, rules: dict) -> float:
    source_weight = float(rules["source_weights"].get(source_type, 0.6))
    base = float(rules["importance_rules"]["standard"]["base"])
    bonus = 0.0
    if any(token in text for token in ["oiml", "iec", "sac"]):
        bonus += float(rules["importance_rules"]["standard"]["authority_bonus"])
    if any(token in text for token in ["nb-iot", "lorawan", "m-bus", "protocol"]):
        bonus += float(rules["importance_rules"]["standard"]["communication_protocol_bonus"])
    if any(token in text for token in ["metrology", "measurement", "metering"]):
        bonus += float(rules["importance_rules"]["standard"]["metrology_bonus"])
    return clamp_score(base * source_weight + bonus)


def _score_competitor_event(event_type: str, source_type: str, rules: dict) -> float:
    source_weight = float(rules["source_weights"].get(source_type, 0.6))
    base = float(rules["importance_rules"]["competitor"]["base"])
    bonus = 0.0
    if event_type == "new_product":
        bonus += float(rules["importance_rules"]["competitor"]["new_product_bonus"])
    if event_type == "award":
        bonus += float(rules["importance_rules"]["competitor"]["award_bonus"])
    if event_type == "strategic_partnership":
        bonus += float(rules["importance_rules"]["competitor"]["strategic_partnership_bonus"])
    return clamp_score(base * source_weight + bonus)


def _make_dedupe_key(*parts: str) -> str:
    normalized = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _summarize_text(title: str, raw_text: str) -> str:
    if not raw_text:
        return title[:280]
    summary = raw_text[:320].strip()
    if title and title.lower() not in summary.lower():
        return f"{title}. {summary}"[:320]
    return summary
