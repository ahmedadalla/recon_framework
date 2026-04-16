from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DEFAULT_PIPELINE_CONFIG

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML configs.")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data if isinstance(data, dict) else {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    defaults = _load_file(DEFAULT_PIPELINE_CONFIG)
    if config_path is None:
        return defaults

    runtime_path = Path(config_path)
    if not runtime_path.is_absolute():
        runtime_path = Path.cwd() / runtime_path

    runtime = _load_file(runtime_path)
    return _deep_merge(defaults, runtime)