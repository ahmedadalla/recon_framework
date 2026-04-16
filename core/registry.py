from __future__ import annotations

import importlib.util
import sys
from hashlib import sha1
from collections.abc import Iterable
from pathlib import Path
from typing import Type

from core.contracts import ToolPlugin

TOOL_REGISTRY: dict[str, Type[ToolPlugin]] = {}
_LOADED_PLUGIN_PATHS: set[str] = set()


def register_tool(cls: Type[ToolPlugin]) -> Type[ToolPlugin]:
    TOOL_REGISTRY[cls.name] = cls
    return cls


def iter_plugins(enabled: Iterable[str] | None = None) -> list[ToolPlugin]:
    enabled_set = set(enabled) if enabled is not None else None
    plugins: list[ToolPlugin] = []
    for name, plugin_cls in TOOL_REGISTRY.items():
        if enabled_set is not None and name not in enabled_set:
            continue
        plugins.append(plugin_cls())
    return plugins


def load_builtin_plugins() -> None:
    from plugins.recon import crtsh, dnsx_final, oneforall, puredns, subenum, subfinder  # noqa: F401
    from plugins.web import httpx, spidering, wayback, url_merge, pattern_matching  # noqa: F401
    from plugins.vuln import crlfuzz, dalfox, fuzzing, gf_router, nuclei, nse_scans, port_scan, s3scanner, screenshots, sqlmap  # noqa: F401
    from plugins.report import reporting  # noqa: F401


def load_external_plugins(plugin_paths: Iterable[str | Path], base_path: Path | None = None) -> None:
    for raw_path in plugin_paths:
        plugin_path = Path(raw_path)
        if not plugin_path.is_absolute() and base_path is not None:
            plugin_path = base_path / plugin_path
        if plugin_path.is_dir():
            candidates = sorted(plugin_path.glob("*.py"))
        elif plugin_path.is_file() and plugin_path.suffix == ".py":
            candidates = [plugin_path]
        else:
            continue

        for file_path in candidates:
            resolved = str(file_path.resolve())
            if resolved in _LOADED_PLUGIN_PATHS:
                continue

            module_name = f"external_plugin_{sha1(resolved.encode('utf-8')).hexdigest()}"
            spec = importlib.util.spec_from_file_location(module_name, resolved)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            _LOADED_PLUGIN_PATHS.add(resolved)