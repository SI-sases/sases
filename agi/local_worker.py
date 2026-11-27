"""Local SASES sub-agent worker.

Runs on the user's desktop, where Chrome/CDP and local files exist. It polls the
main AGI for queued local agents, claims one, executes its task package, and
posts progress/result back.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

from .executor import execute
from .package import TaskPackage
from .planner import plan
from .tools import build_default_registry
from .worker import _read_only


def _call(server: str, token: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}, ensure_ascii=False).encode() if method != "GET" else None
    req = urllib.request.Request(server.rstrip("/") + path, data=data, method=method,
                                 headers={"Accept": "application/json",
                                          "Content-Type": "application/json",
                                          "X-SASES-AGI-Token": token})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def _execute(server: str, token: str, registry, agent_id: str, steps: list[dict],
             goal: str) -> dict:
    _call(server, token, "POST", f"/agents/{agent_id}/progress", {"progress": "本地执行中"})
    package = TaskPackage(goal=goal, node_id="local", acceptance=["local result reported"],
                          steps=steps, tools_allowed=[s.get("tool") for s in steps])
    conn = sqlite3.connect(":memory:")
    result = execute(package, registry, conn, owner="local-worker", profile="main")
    status = "done" if result.get("ok") else "failed"
    _call(server, token, "POST", f"/agents/{agent_id}/finish", {"status": status, "result": result})
    return {"ok": bool(result.get("ok")), "claimed": True, "agent_id": agent_id, "status": status, "result": result}


def _run_approved(server: str, token: str, registry) -> dict:
    rows = _call(server, token, "GET", "/approvals/approved").get("approvals", [])
    for row in rows:
        if row.get("tool") != "agent.execute":
            continue
        try:
            payload = json.loads(row.get("args_json") or "{}")
        except json.JSONDecodeError:
            continue
        agent_id = str(payload.get("agent_id") or "")
        steps = payload.get("steps") or []
        if not agent_id or not steps:
            continue
        agent = _call(server, token, "GET", f"/agents/{agent_id}").get("agent", {})
        if str(agent.get("node_id") or "") not in ("local", "desktop"):
            continue
        result = _execute(server, token, registry, agent_id, steps,
                          str(agent.get("goal") or "local task"))
        _call(server, token, "POST", "/approvals/executed", {"id": int(row["id"])})
        return result
    return {"ok": True, "claimed": False}


def run_once(server: str, token: str, registry=None, base_url: str = "") -> dict:
    registry = registry or build_default_registry()
    approved = _run_approved(server, token, registry)
    if approved.get("agent_id"):
        return approved
    listing = _call(server, token, "GET", "/agents")
    queued = [a for a in listing.get("agents", [])
              if a.get("status") == "queued" and str(a.get("node_id") or "") in ("local", "desktop")]
    if not queued:
        return {"ok": True, "claimed": False}
    agent = queued[0]
    agent_id = str(agent.get("agent_id") or "")
    if not _call(server, token, "POST", f"/agents/{agent_id}/claim",
                 {"owner": "local-worker", "ttl": 300}).get("ok"):
        return {"ok": True, "claimed": False}
    try:
        task = json.loads(agent.get("task_json") or "{}")
    except json.JSONDecodeError:
        task = {}
    goal = str(agent.get("goal") or task.get("goal") or "local task")
    steps = task.get("steps") if isinstance(task.get("steps"), list) else []
    if not steps:
        steps = plan(goal, registry, base_url or "http://127.0.0.1:8001", 5).get("steps") or []
    safe, reason = _read_only(registry, steps)
    if not safe:
        approval = _call(server, token, "POST", "/approvals", {
            "tool": "agent.execute",
            "args": {"agent_id": agent_id, "steps": steps},
            "description": f"{goal}: {reason}",
            "risk": "high",
        })
        _call(server, token, "POST", f"/agents/{agent_id}/progress", {"progress": "等待审批"})
        _call(server, token, "POST", f"/agents/{agent_id}/finish",
              {"status": "needs_approval", "result": {"ok": False, "approval_id": approval.get("approval_id"),
                                                       "reason": reason}})
        return {"ok": True, "claimed": True, "agent_id": agent_id,
                "status": "needs_approval", "approval_id": approval.get("approval_id")}
    return _execute(server, token, registry, agent_id, steps, goal)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://10.0.0.3:8099")
    parser.add_argument("--token-file", default="data/agi.token")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    while True:
        try:
            outcome = run_once(args.server, token)
            _call(args.server, token, "POST", "/local-worker/status", {
                "owner": "local-worker", "current_agent": outcome.get("agent_id"),
                "claimed": outcome.get("claimed"),
            })
            print(json.dumps(outcome, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), flush=True)
        if not args.loop:
            return 0
        time.sleep(max(0.5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
