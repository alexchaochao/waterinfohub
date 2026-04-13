from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from waterinfohub.collectors.source_loader import SourceDefinition, load_sources
from waterinfohub.db.models import RawDocument
from waterinfohub.db.session import get_session


@dataclass(slots=True)
class IngestStats:
    fetched: int = 0
    inserted: int = 0
    duplicated: int = 0
    failed: int = 0


def run_ingest(config_dir: Path) -> IngestStats:
    stats = IngestStats()
    source_files = [
        config_dir / "sources" / "standards.yaml",
        config_dir / "sources" / "competitors.yaml",
    ]
    all_sources: list[SourceDefinition] = []
    for path in source_files:
        if path.exists():
            all_sources.extend(load_sources(path))

    with get_session() as session:
        for source in all_sources:
            if not source.enabled:
                continue
            for url in source.start_urls:
                try:
                    doc = _fetch_source_page(source, url)
                    stats.fetched += 1
                    session.add(doc)
                    session.commit()
                    stats.inserted += 1
                except IntegrityError:
                    session.rollback()
                    stats.duplicated += 1
                except Exception:
                    session.rollback()
                    stats.failed += 1
    return stats


def _fetch_source_page(source: SourceDefinition, url: str) -> RawDocument:
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
    soup = BeautifulSoup(html, "html.parser")
    title = _safe_text(soup.title.string) if soup.title and soup.title.string else None
    text = _safe_text(soup.get_text(" ", strip=True))[:8000]
    content_hash = hashlib.sha256(f"{source.id}|{url}|{text}".encode("utf-8")).hexdigest()
    return RawDocument(
        source_id=source.id,
        source_name=source.name,
        domain=source.domain,
        source_type=source.source_type,
        source_host=urlparse(url).netloc or None,
        source_url=url,
        title=title,
        raw_text=text,
        content_hash=content_hash,
        status="new",
    )


def _safe_text(text: str) -> str:
    return " ".join(text.split())
