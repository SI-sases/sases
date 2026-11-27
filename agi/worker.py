"""Minimal sub-agent worker: claim queued agents, plan read-only work, execute, report."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any

from . import agents, approvals, context_pack
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


def ensure_status(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agi_worker_status ("
        "owner TEXT PRIMARY KEY,last_seen INTEGER NOT NULL,last_result TEXT)"
    )
    conn.commit()


def status(conn: sqlite3.Connection) -> list[dict]:
    ensure_status(conn)
    rows = conn.execute("SELECT owner,last_seen,last_result FROM agi_worker_status ORDER BY last_seen DESC").fetchall()
    return [{"owner": r[0], "last_seen": r[1], "last_result": r[2]} for r in rows]


def _touch(conn: sqlite3.Connection, owner: str, result: dict[str, Any]) -> None:
    ensure_status(conn)
    conn.execute(
        "INSERT INTO agi_worker_status(owner,last_seen,last_result) VALUES(?,?,?) "
        "ON CONFLICT(owner) DO UPDATE SET last_seen=excluded.last_seen,last_result=excluded.last_result",
        (owner, int(__import__("time").time()), json.dumps(result, ensure_ascii=False)[:1000]),
    )
    conn.commit()


def _patch_step(conn: sqlite3.Connection, agent_id: str, index: int, total: int, step: dict) -> None:
    agents.set_progress(conn, agent_id, f"审批后第 {index + 1}/{total} 步完成")


def _run_approved(conn: sqlite3.Connection, registry, owner: str) -> dict[str, Any]:
    rows = approvals.list_by_status(conn, "allow", 20)
    for row in rows:
        if row.get("tool") != "agent.execute":
            continue
        try:
            payload = json.loads(row.get("args_json") or "{}")
        except json.JSONDecodeError:
            continue
        agent_id = str(payload.get("agent_id") or "")
        steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
        agent = agents.get_agent(conn, agent_id)
        if not agent or not steps:
            approvals.mark_executed(conn, int(row["id"]))
            continue
        agents.set_progress(conn, agent_id, "审批通过，执行中")
        for step in steps:
            args = step.get("args") if isinstance(step.get("args"), dict) else {}
            args.setdefault("approved", True)
            args.setdefault("_approved", True)
            step["args"] = args
        package = TaskPackage(goal=str(agent.get("goal") or "approved task"),
                              node_id=str(agent.get("node_id") or "local"),
                              acceptance=["approved execution"], steps=steps,
                              tools_allowed=[s.get("tool") for s in steps])
        result = execute(package, registry, conn, owner=owner, profile="main",
                         on_step=lambda i, s, r: _patch_step(conn, agent_id, i, len(steps), s))
        agents.finish(conn, agent_id, "done" if result.get("ok") else "failed", result)
        approvals.mark_executed(conn, int(row["id"]))
        return {"ok": bool(result.get("ok")), "claimed": True, "agent_id": agent_id,
                "status": "done" if result.get("ok") else "failed", "approved": True,
                "result": result}
    return {"ok": True, "claimed": False}


def run_once(conn: sqlite3.Connection, registry, owner: str = "worker",
             base_url: str = "") -> dict[str, Any]:
    base_url = base_url or os.environ.get("SASES_WORKER_BASE_URL", "http://127.0.0.1:8001")
    agent_id = agents.claim_next(conn, owner, 300)
    if not agent_id:
        result = _run_approved(conn, registry, owner)
        _touch(conn, owner, result)
        return result
    agent = agents.get_agent(conn, agent_id) or {}
    steer_notes = []
    for msg in agents.unread_messages(conn, agent_id):
        try:
            payload = json.loads(msg.get("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        text = str(payload.get("message") or "")
        agents.ack_message(conn, int(msg["id"]))
        if any(k in text.lower() for k in ("取消", "停止", "cancel", "stop")):
            agents.finish(conn, agent_id, "cancelled", {"ok": False, "reason": "cancelled by parent"})
            out = {"ok": True, "claimed": True, "agent_id": agent_id, "status": "cancelled"}
            _touch(conn, owner, out)
            return out
        if text:
            steer_notes.append(text)
    try:
        task = json.loads(agent.get("task_json") or "{}")
    except json.JSONDecodeError:
        task = {}
    goal = str(agent.get("goal") or task.get("goal") or agent.get("name") or "")
    ctx_id = ""
    try:
        ctx_meta = json.loads(agent.get("context_json") or "{}")
        ctx_id = str(ctx_meta.get("context_id") or "")
    except json.JSONDecodeError:
        ctx_meta = {}
    if ctx_id:
        pack = context_pack.get(conn, ctx_id)
        if pack:
            goal = pack.get("goal") or goal
            context_pack.patch(conn, ctx_id, {"state": {"status": "running"}}, agent_id=agent_id)
            agents.set_progress(conn, agent_id, "读取上下文")
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
        if ctx_id:
            context_pack.patch(conn, ctx_id, {"state": {"status": "needs_approval"}}, agent_id=agent_id)
        agents.finish(conn, agent_id, "needs_approval", {
            "ok": False, "approval_id": approval_id, "reason": reason, "steps": steps,
        })
        out = {"ok": True, "claimed": True, "agent_id": agent_id,
               "status": "needs_approval", "approval_id": approval_id, "reason": reason}
        _touch(conn, owner, out)
        return out
    package = TaskPackage(goal=goal or "worker task", node_id=str(agent.get("node_id") or "local"),
                          acceptance=["worker completed"], steps=steps,
                          tools_allowed=[s.get("tool") for s in steps])
    agents.set_progress(conn, agent_id, "执行中")
    def _on_step(index: int, step: dict, step_result: dict) -> None:
        agents.set_progress(conn, agent_id, f"第 {index + 1}/{len(steps)} 步完成")
        if ctx_id:
            context_pack.patch(conn, ctx_id, {
                "state": {"status": "running", "current_step": index + 1},
                "facts": [{"key": "last_tool", "value": str(step.get("tool") or "")}],
            }, agent_id=agent_id)

    result = execute(package, registry, conn, owner=owner, profile="main", on_step=_on_step)
    if ctx_id:
        facts = [{"key": "last_result", "value": "ok" if result.get("ok") else "failed"}]
        if not result.get("ok"):
            facts.append({"key": "last_error", "value": str(result.get("error") or "failed")[:300]})
        urls = __import__("re").findall(r"https?://[^\s\"']+", json.dumps(result, ensure_ascii=False))
        artifacts = [{"id": "art_url_" + str(i), "type": "url", "uri": u,
                      "name": u.rsplit("/", 1)[-1] or "url", "access": "public"}
                     for i, u in enumerate(dict.fromkeys(urls))]
        context_pack.patch(conn, ctx_id, {
            "state": {"status": "done" if result.get("ok") else "failed", "current_step": len(steps)},
            "facts": facts,
            "artifacts": artifacts,
        }, agent_id=agent_id)
        result["context_id"] = ctx_id
    if steer_notes:
        result["steer_notes"] = steer_notes
    agents.finish(conn, agent_id, "done" if result.get("ok") else "failed", result)
    out = {"ok": bool(result.get("ok")), "claimed": True, "agent_id": agent_id,
           "status": "done" if result.get("ok") else "failed", "result": result}
    _touch(conn, owner, out)
    return out


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/agi.db")
    parser.add_argument("--owner", default="worker")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    from .tools import build_default_registry
    registry = build_default_registry()
    while True:
        conn = sqlite3.connect(args.db)
        conn.row_factory = sqlite3.Row
        try:
            print(json.dumps(run_once(conn, registry, args.owner), ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001 - keep the worker alive
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
                  flush=True)
        finally:
            conn.close()
        if not args.loop:
            return 0
        __import__("time").sleep(max(0.5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
