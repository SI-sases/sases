"""Execute a TaskPackage through the shared tool registry."""
from __future__ import annotations

import sqlite3
from typing import Any, Callable

from .package import TaskPackage


def execute(package: TaskPackage, registry, conn: sqlite3.Connection,
            owner: str = "main", profile: str = "sub",
            on_step: Callable[[int, dict, dict], None] | None = None) -> dict[str, Any]:
    package.validate()
    if not package.steps:
        return {"ok": False, "error": "package has no steps", "trace_id": package.trace_id}
    results: list[dict[str, Any]] = []
    allowed = set(package.tools_allowed or [])
    for index, step in enumerate(package.steps):
        tool_id = str(step.get("tool") or "")
        if not tool_id:
            return {"ok": False, "error": "step missing tool", "step": index,
                    "trace_id": package.trace_id, "results": results}
        if allowed and tool_id not in allowed:
            return {"ok": False, "error": f"tool not allowed: {tool_id}", "step": index,
                    "trace_id": package.trace_id, "results": results}
        args = dict(step.get("args") or {})
        try:
            result = registry.invoke(profile, tool_id, args)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "step": index,
                    "trace_id": package.trace_id, "results": results}
        results.append({"tool": tool_id, "result": result})
        if on_step and result.get("ok") is not False:
            try:
                on_step(index, step, result)
            except Exception:
                pass
        if result.get("ok") is False and result.get("error") == "approval_required":
            return {"ok": False, "error": "approval_required", "step": index,
                    "trace_id": package.trace_id, "results": results}
        if result.get("ok") is False:
            return {"ok": False, "error": result.get("error", "tool failed"), "step": index,
                    "trace_id": package.trace_id, "results": results}
    return {"ok": True, "trace_id": package.trace_id, "run_id": package.run_id, "results": results}
