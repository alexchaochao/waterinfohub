from dataclasses import dataclass


@dataclass(slots=True)
class SourceConfig:
    id: str
    name: str
    domain: str
    source_type: str
    method: str
    enabled: bool = True
