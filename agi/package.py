"""Task packages are the only thing the main AGI sends to a sub AGI."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaskPackage:
    goal: str
    node_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: "trace_" + uuid.uuid4().hex[:16])
    run_id: str = field(default_factory=lambda: "run_" + uuid.uuid4().hex[:16])
    parent_run_id: str = ""
    constraints: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    acceptance: list[str] = field(default_factory=list)
    tools_allowed: list[str] = field(default_factory=list)
    approval_required: bool = False

    def validate(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal is required")
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if not self.acceptance:
            raise ValueError("acceptance criteria are required")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
