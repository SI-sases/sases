"""Minimal sub-agent worker: claim queued agents, plan read-only work, execute, report."""
from __future__ import annotations

import json
import sqlite3
import sys
from typing import Any

from . import agents, approvals
from .executor import execute
from .package import TaskPackage
from .planner import plan


def _read_only(registry, steps: list[dict]) -> tuple[bool, str]:
    for step in steps:
        try:
            spec = registry.get(str(step.get("tool") or ""))
        except KeyError:
            return False, f"unknown tool: {step.get('tool')}"
        if spec.risk != "read":
            return False, f"tool requires approval: {spec.id} ({spec.risk})"
    return True, ""


def run_once(conn: sqlite3.Connection, registry, owner: str = "worker",
             base_url: str = "http://127.0.0.1:8001") -> dict[str, Any]:
    agent_id = agents.claim_next(conn, owner, 300)
    if not agent_id:
        return {"ok": True, "claimed": False}
    agent = agents.get_agent(conn, agent_id) or {}
    try:
        task = json.loads(agent.get("task_json") or "{}")
    except json.JSONDecodeError:
        task = {}
    goal = str(agent.get("goal") or task.get("goal") or agent.get("name") or "")
    steps = task.get("steps") if isinstance(task.get("steps"), list) else []
    agents.set_progress(conn, agent_id, "规划中")
    if not steps:
        planned = plan(goal, registry, base_url, 5)
        steps = planned.get("steps") or []
    safe, reason = _read_only(registry, steps)
    if not safe:
        approval_id = approvals.create(conn, "agent.execute", {"agent_id": agent_id, "steps": steps},
                                       f"{agent.get('name') or goal}: {reason}", "high")
        agents.set_progress(conn, agent_id, "等待审批")
        agents.finish(conn, agent_id, "needs_approval", {
            "ok": False, "approval_id": approval_id, "reason": reason, "steps": steps,
        })
        return {"ok": True, "claimed": True, "agent_id": agent_id,
                "status": "needs_approval", "approval_id": approval_id, "reason": reason}
    package = TaskPackage(goal=goal or "worker task", node_id=str(agent.get("node_id") or "local"),
                          acceptance=["worker completed"], steps=steps,
                          tools_allowed=[s.get("tool") for s in steps])
    agents.set_progress(conn, agent_id, "执行中")
    result = execute(package, registry, conn, owner=owner, profile="main")
    agents.finish(conn, agent_id, "done" if result.get("ok") else "failed", result)
    return {"ok": bool(result.get("ok")), "claimed": True, "agent_id": agent_id,
            "status": "done" if result.get("ok") else "failed", "result": result}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/agi.db")
    parser.add_argument("--owner", default="worker")
    args = parser.parse_args()
    from .tools import build_default_registry
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    print(json.dumps(run_once(conn, build_default_registry(), args.owner), ensure_ascii=False))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
