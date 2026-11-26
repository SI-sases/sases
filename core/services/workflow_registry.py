"""File-based workflow registry (tool pipelines)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = ROOT / "workflows"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _read(path: Path) -> dict | None:
    try:
        data = json.loads((path / "workflow.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    wid = str(data.get("id") or path.name)
    if not ID_RE.match(wid) or wid != path.name:
        return None
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > 20:
        return None
    for step in steps:
        if not isinstance(step, dict) or not str(step.get("tool") or "").strip():
            return None
    data["id"] = wid
    data.setdefault("name", wid)
    data.setdefault("description", "")
    return data


def list_workflows() -> list[dict]:
    out = []
    if not WORKFLOWS.is_dir():
        return out
    for path in sorted(WORKFLOWS.iterdir()):
        if path.is_dir() and ID_RE.match(path.name):
            data = _read(path)
            if data:
                out.append({
                    "id": data["id"], "name": data.get("name", data["id"]),
                    "description": data.get("description", ""),
                    "steps": len(data.get("steps", [])),
                })
    return out


def get_workflow(workflow_id: str) -> dict:
    if not ID_RE.match(workflow_id or ""):
        raise KeyError("invalid workflow id")
    path = WORKFLOWS / workflow_id
    data = _read(path) if path.is_dir() else None
    if not data:
        raise KeyError("workflow not found")
    return data
