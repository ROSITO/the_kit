from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SubjectInfo:
    id: str = "anonymous"
    group: str | None = None


@dataclass
class Node:
    index: int
    type: str
    engine: str = "qt"
    timing_mode: str = "standard"
    id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def node_id(self) -> str:
        return self.id or f"node_{self.index:03d}"


@dataclass
class Protocol:
    protocol_version: str
    name: str
    loop: int
    nodes: list[Node]
    path: Path
    root: Path
    subject: SubjectInfo = field(default_factory=SubjectInfo)
    randomize_blocks: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
