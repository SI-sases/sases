"""Failure handling plans for the main AGI."""
from __future__ import annotations


def plan_failure(node_id: str, task_id: int, attempts: int, reason: str = "") -> dict:
    attempts = max(0, int(attempts))
    if attempts < 3:
        return {
            "action": "retry",
            "node_id": node_id,
            "task_id": task_id,
            "attempt": attempts + 1,
            "delay_seconds": min(300, 15 * (attempts + 1)),
            "reason": reason,
            "requires_approval": False,
        }
    return {
        "action": "reroute",
        "node_id": node_id,
        "task_id": task_id,
        "reason": reason or "retry limit reached",
        "candidates": ["node-C", "node-B"],
        "requires_approval": False,
    }
