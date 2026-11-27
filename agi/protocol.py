"""Structured messages between the main AGI and sub AGIs.

Chat is for humans.  Machines use these envelopes so a message can be
validated, replayed, audited and made idempotent.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

MESSAGE_TYPES = {
    "agi.heartbeat",
    "agi.event",
    "agi.task",
    "agi.proposal",
    "agi.apply",
    "agi.result",
    "agi.rollback",
}

SEVERITIES = {"info", "warning", "error", "critical"}


@dataclass
class Message:
    type: str
    node_id: str
    scope: str = "local"
    kind: str = "cloud"
    severity: str = "info"
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    idempotency_key: str | None = None
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str = ""
    run_id: str = ""
    parent_run_id: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))

    def validate(self) -> None:
        if self.type not in MESSAGE_TYPES:
            raise ValueError(f"unknown message type: {self.type}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity: {self.severity}")
        if not self.node_id:
            raise ValueError("node_id is required")
        if self.scope not in {"local", "fleet"}:
            raise ValueError("scope must be local or fleet")
        if self.kind not in {"client", "cloud"}:
            raise ValueError("kind must be client or cloud")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


def make_message(type: str, node_id: str, **kwargs: Any) -> Message:
    message = Message(type=type, node_id=node_id, **kwargs)
    message.validate()
    return message
