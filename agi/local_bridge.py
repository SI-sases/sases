"""Synchronous local-runtime bridge for read-only main-AGI tools."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path


def _server() -> str:
    return os.environ.get("SASES_AGI_SERVER", "http://127.0.0.1:8099").rstrip("/")


def _token() -> str:
    token = os.environ.get("SASES_AGI_TOKEN", "").strip()
    if token:
        return token
    path = Path(os.environ.get("SASES_AGI_TOKEN_FILE", "data/agi.token"))
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}, ensure_ascii=False).encode() if method != "GET" else None
    req = urllib.request.Request(
        _server() + path, data=data, method=method,
        headers={"Content-Type": "application/json", "X-SASES-AGI-Token": _token()},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def run_readonly(tool: str, args: dict, timeout: int = 30) -> dict:
    try:
        spawned = _call("POST", "/agents/spawn", {
            "node_id": "local",
            "name": "local bridge: " + tool,
            "goal": "local read-only bridge",
            "status": "queued",
            "ttl": max(60, timeout + 30),
            "task": {"steps": [{"tool": tool, "args": args}]},
            "context": {"source": "main_bridge"},
        })
        agent_id = str(spawned.get("agent_id") or "")
        if not agent_id:
            return {"ok": False, "error": "local bridge spawn failed"}
        deadline = time.monotonic() + max(5, timeout)
        while time.monotonic() < deadline:
            time.sleep(0.5)
            agent = _call("GET", f"/agents/{agent_id}").get("agent") or {}
            status = str(agent.get("status") or "")
            if status in ("done", "failed", "cancelled", "quota_blocked"):
                raw = agent.get("result_json") or "{}"
                try:
                    result = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    result = {"ok": False, "error": "invalid agent result"}
                result["local_agent_id"] = agent_id
                result["status"] = status
                return result
        return {"ok": False, "error": "local bridge timeout", "local_agent_id": agent_id}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
