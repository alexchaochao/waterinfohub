from __future__ import annotations

from pathlib import Path

import yaml


def load_scoring_rules(config_dir: Path) -> dict:
    rules_path = config_dir / "scoring" / "rules.yaml"
    return yaml.safe_load(rules_path.read_text(encoding="utf-8"))


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))
