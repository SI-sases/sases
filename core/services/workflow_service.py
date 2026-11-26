"""Workflow runner: sequential tool steps with approval checks."""
from __future__ import annotations

import json
import time
from typing import Any

from core.db import db_cursor
from core.services import tool_policy, workflow_registry


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                input_json TEXT NOT NULL DEFAULT '{}',
                result_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _sub(value: Any, params: dict) -> Any:
    if isinstance(value, str):
        for k, v in params.items():
            value = value.replace("{{" + str(k) + "}}", str(v))
        return value
    if isinstance(value, list):
        return [_sub(v, params) for v in value]
    if isinstance(value, dict):
        return {k: _sub(v, params) for k, v in value.items()}
    return value


def run(user_id: int, workflow_id: str, params: dict | None = None, approve: bool = False) -> dict:
    wf = workflow_registry.get_workflow(workflow_id)
    ensure_schema()
    params = params or {}
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO workflow_runs(user_id,workflow_id,status,input_json,created_at) VALUES (?,?,?,?,?)",
            (user_id, workflow_id, "running", json.dumps(params, ensure_ascii=False), _now()),
        )
        run_id = cur.lastrowid

    results = []
    status = "completed"
    try:
        from core import tool_gateway
        for index, step in enumerate(wf.get("steps", []), 1):
            tool = str(step.get("tool") or "")
            args = _sub(step.get("params") or {}, params)
            if tool_policy.requires_approval(tool, args) and not approve:
                results.append({"step": index, "tool": tool,
                                "ok": False, "error": "approval required"})
                status = "approval_required"
                break
            res = tool_gateway.invoke_tool(tool, args)
            ok = bool(getattr(res, "success", False))
            results.append({
                "step": index, "tool": tool, "ok": ok,
                "result": str(getattr(res, "result", None))[:1000] if ok else None,
                "error": None if ok else str(getattr(res, "error", "failed"))[:300],
            })
            if not ok:
                status = "failed"
                break
    except Exception as exc:
        status = "failed"
        results.append({"step": len(results) + 1, "tool": "", "ok": False, "error": str(exc)[:300]})
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE workflow_runs SET status=?,result_json=?,finished_at=? WHERE id=?",
            (status, json.dumps(results, ensure_ascii=False), _now(), run_id),
        )
    return {"run_id": run_id, "workflow_id": workflow_id, "status": status, "results": results}
