from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class SourceDefinition:
    id: str
    name: str
    domain: str
    source_type: str
    method: str
    enabled: bool
    start_urls: list[str]


def load_sources(config_file: Path) -> list[SourceDefinition]:
    raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    records = raw.get("sources", [])
    items: list[SourceDefinition] = []
    for rec in records:
        items.append(
            SourceDefinition(
                id=rec["id"],
                name=rec["name"],
                domain=rec["domain"],
                source_type=rec["source_type"],
                method=rec.get("method", "requests"),
                enabled=bool(rec.get("enabled", True)),
                start_urls=list(rec.get("start_urls", [])),
            )
        )
    return items
