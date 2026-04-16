from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Phase(StrEnum):
    RECON = "recon"
    WEB = "web"
    VULN = "vuln"
    REPORT = "report"


@dataclass(slots=True)
class Artifact:
    key: str
    path: Path
    kind: str = "file"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    tool: str
    phase: Phase
    success: bool
    artifacts: list[Artifact] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class RunContext:
    target: str
    workspace: Path
    config: dict[str, Any]
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def publish(self, artifact: Artifact) -> None:
        self.artifacts[artifact.key] = artifact

    def require(self, key: str) -> Artifact:
        if key not in self.artifacts:
            raise KeyError(f"Missing required artifact: {key}")
        return self.artifacts[key]

    def get_path(self, key: str) -> Path:
        return self.require(key).path


class ToolPlugin(ABC):
    name: str
    phase: Phase
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    parallel_safe: bool = True

    @abstractmethod
    def run(self, ctx: RunContext) -> ToolResult:
        raise NotImplementedError