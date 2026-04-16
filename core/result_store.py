from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.contracts import Artifact


@dataclass
class ResultStore:
    root: Path
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def publish(self, artifact: Artifact) -> Artifact:
        self.artifacts[artifact.key] = artifact
        return artifact

    def get(self, key: str) -> Artifact:
        return self.artifacts[key]

    def record(self, event: dict[str, Any]) -> None:
        self.events.append(event)