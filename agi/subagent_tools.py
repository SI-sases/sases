"""Direct supervision tools for the main AGI.

These wrap the existing /agents HTTP control plane so the main AGI can spawn,
wait for, steer, cancel and inspect child agents without going through the
task queue UI.
"""
from __future__ import annotations

from .local_bridge import _call


def spawn(args: dict) -> dict:
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps:
        return {"ok": False, "error": "steps is required"}
    body = {
        "node_id": str(args.get("node_id") or "local"),
        "name": str(args.get("name") or "main subagent"),
        "goal": str(args.get("goal") or "subagent task"),
        "status": "queued",
        "ttl": max(60, min(int(args.get("ttl") or 300), 3600)),
        "task": {"steps": steps},
        "context": {"source": "main_subagent_tool"},
    }
    return _call("POST", "/agents/spawn", body)


def wait(args: dict) -> dict:
    agent_id = str(args.get("agent_id") or "")
    if not agent_id:
        return {"ok": False, "error": "agent_id is required"}
    timeout = max(1, min(int(args.get("timeout") or 20), 60))
    return _call("GET", f"/agents/{agent_id}/wait?timeout={timeout}")


def message(args: dict) -> dict:
    agent_id = str(args.get("agent_id") or "")
    text = str(args.get("message") or "").strip()
    if not agent_id or not text:
        return {"ok": False, "error": "agent_id and message are required"}
    return _call("POST", f"/agents/{agent_id}/message", {"message": text})


def cancel(args: dict) -> dict:
    agent_id = str(args.get("agent_id") or "")
    if not agent_id:
        return {"ok": False, "error": "agent_id is required"}
    return _call("POST", f"/agents/{agent_id}/cancel", {})


def trace(args: dict) -> dict:
    agent_id = str(args.get("agent_id") or "")
    if not agent_id:
        return {"ok": False, "error": "agent_id is required"}
    return _call("GET", f"/agents/{agent_id}/trace")
