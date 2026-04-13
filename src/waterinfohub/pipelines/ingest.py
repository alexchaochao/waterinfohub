from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlalchemy.exc import IntegrityError

from waterinfohub.collectors.source_loader import SourceDefinition, load_sources
from waterinfohub.core.settings import settings
from waterinfohub.db.models import RawDocument
from waterinfohub.db.session import get_session
from waterinfohub.services.structured_logger import get_structured_logger

logger = get_structured_logger("ingest")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


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
                except Exception as exc:
                    import traceback

                    session.rollback()
                    stats.failed += 1
                    logger.error(
                        f"Ingest failed for source {getattr(source, 'name', None)} url {url}",
                        extra={
                            "extra": {
                                "source": getattr(source, "name", None),
                                "url": url,
                                "exception": str(exc),
                                "traceback": traceback.format_exc(),
                            }
                        },
                    )
    return stats


def _fetch_source_page(source: SourceDefinition, url: str) -> RawDocument:
    try:
        html = _fetch_via_http(url)
    except httpx.HTTPStatusError as exc:
        if settings.playwright_fallback_enabled and _should_fallback_to_playwright(
            exc.response.status_code
        ):
            html = _fallback_to_playwright(url, exc)
        else:
            raise
    except httpx.HTTPError as exc:
        if settings.playwright_fallback_enabled:
            html = _fallback_to_playwright(url, exc)
        else:
            raise

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


def _fetch_via_http(url: str) -> str:
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _fetch_via_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
            return page.content()
        finally:
            browser.close()


def _should_fallback_to_playwright(status_code: int) -> bool:
    return status_code in {401, 403, 429} or 500 <= status_code < 600


def _fallback_to_playwright(url: str, original_error: Exception) -> str:
    logger.warning(f"httpx failed for {url}, fallback to Playwright: {original_error}")
    try:
        return _fetch_via_playwright(url)
    except Exception as fallback_error:
        raise RuntimeError(
            f"Playwright fallback failed for {url}: {fallback_error}"
        ) from original_error


def _safe_text(text: str) -> str:
    return " ".join(text.split())
