from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


def load_settings(settings_path: Path) -> Dict[str, Any]:
    """Load YAML settings (dict).

    Keep this permissive: non-developers will edit YAML.
    Validation is performed later with clear error messages.
    """
    settings_path = settings_path.resolve()
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")

    with settings_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Settings YAML must be a mapping (dict). Got: {type(data)}")

    return data
