# core/services/run_service.py
# -*- coding: utf-8 -*-
"""统一运行入口：一个 run → 一个 agent_loop。"""
import os

from ..db import db_cursor


def create_run(user_id, conversation_id, source, goal, supervisor_id="sases_assistant", max_rounds=10):
    from . import supervisor_service
    run_id = supervisor_service.create_run(
        int(user_id), int(conversation_id), supervisor_id or "sases_assistant",
        str(goal), task_type=str(source or "chat"), max_rounds=int(max_rounds))
    return run_id


def recover_stale_runs():
    """断网/重启恢复：running 但 heartbeat 过期的 run 标记 interrupted。"""
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE supervisor_runs SET status='interrupted', finished_at=datetime('now') "
                "WHERE status='running' AND ("
                "(heartbeat_at IS NOT NULL AND heartbeat_at < datetime('now','-90 seconds')) "
                "OR (heartbeat_at IS NULL AND created_at < datetime('now','-10 minutes')))")
            n = cur.rowcount
        if n:
            print("[run] recovered stale runs: " + str(n))
        return n
    except Exception as e:
        print("[run] recover stale failed: " + str(e))
        return 0


async def run_once(user_id, conversation_id, goal, source="chat",
                   supervisor_id="sases_assistant", max_steps=8, skill_ids=None,
                   run_id=None, finish=True, allowed_tool_ids=None,
                   resume=False, on_event=None, permissions=None, agent_id=None):
    from .agent_loop import run
    from . import execution_gateway
    rid = run_id or create_run(user_id, conversation_id, source, goal, supervisor_id)
    try:
        r = await run(int(user_id), int(conversation_id), str(goal),
                      allowed_tool_ids=allowed_tool_ids,
                      max_steps=int(max_steps), run_id=int(rid), mode="strict",
                      supervisor_id=supervisor_id, skill_ids=skill_ids,
                      resume=resume, on_event=on_event, permissions=permissions, agent_id=agent_id)
        status = str(r.get("status") or "")
        mapped = "completed" if status == "ok" else (
            "failed" if status in ("max_steps", "verification_failed", "plan_incomplete",
                                   "plan_required", "error") else status)
        if mapped in ("completed", "failed") and finish:
            try:
                execution_gateway._finish(int(rid), int(conversation_id), supervisor_id,
                                          mapped, r.get("content") or "", source)
            except Exception as e:
                print("[run] finish 失败: " + str(e))
        return {"run_id": rid, "status": mapped, "loop": r}
    except Exception as e:
        try:
            supervisor_service.finish_run(int(rid), "failed")
        except Exception:
            pass
        return {"run_id": rid, "status": "failed", "error": str(e)}
