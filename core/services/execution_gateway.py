# core/services/execution_gateway.py
# -*- coding: utf-8 -*-
"""Step 2: 统一执行入口（A2A / 定时）→ agent_loop。"""
from datetime import datetime

from ..db import db_cursor
from . import agent_loop


def _get_run(run_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM supervisor_runs WHERE id=?", (run_id,))
        return cur.fetchone()


def _finish(run_id, conversation_id, supervisor_id, status, content, source):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status=?, finished_at=? WHERE id=?",
                    (status, datetime.now().isoformat(), run_id))
    try:
        from . import trace_service
        trace_service.emit(run_id, conversation_id, 1, "run_end",
                           content="任务结束：" + str(status), status=str(status))
    except Exception:
        pass
    text = str(content or "").strip()
    if not text:
        text = "✅ 已完成" if status == "completed" else "⚠️ 任务未完成：" + str(status)
    try:
        from .swarm.helpers import _insert_message
        _insert_message(int(conversation_id), "[SUMMARY]:" + text, sender_agent_id=supervisor_id)
    except Exception as e:
        print("[gateway] 本地结果落库失败: " + str(e))
    if source == "a2a":
        try:
            from .cross_account_delivery import deliver_to_linked_accounts
            r = _get_run(run_id)
            import asyncio
            asyncio.create_task(deliver_to_linked_accounts(
                user_id=r["user_id"], conversation_id=conversation_id,
                content=text, sender_agent_id=supervisor_id))
        except Exception as e:
            print("[gateway] A2A 回传失败: " + str(e))


async def run_a2a(run_id):
    run = _get_run(run_id)
    if not run:
        return {"ok": False, "error": "run not found"}
    try:
        res = await agent_loop.run(
            run["user_id"], run["conversation_id"], run["goal"],
            max_steps=10, run_id=run_id, mode="strict",
        )
    except Exception as e:
        _finish(run_id, run["conversation_id"], run["supervisor_id"], "failed", "执行失败：" + str(e), "a2a")
        return {"ok": False, "error": str(e)}
    status = "completed" if res.get("status") == "ok" else (
        "waiting_user" if res.get("status") == "awaiting_approval" else "failed")
    _finish(run_id, run["conversation_id"], run["supervisor_id"], status,
            res.get("content") or "", "a2a")
    return {"ok": status == "completed", "status": status, "content": res.get("content")}


async def run_schedule(run_id, user_id, conversation_id, goal, supervisor_id, options=None):
    try:
        res = await agent_loop.run(
            user_id, conversation_id, goal,
            allowed_tool_ids=(options or {}).get("tools") or None,
            max_steps=10, run_id=run_id, mode="strict",
        )
    except Exception as e:
        _finish(run_id, conversation_id, supervisor_id, "failed", "执行失败：" + str(e), "schedule")
        return {"ok": False, "error": str(e)}
    status = "completed" if res.get("status") == "ok" else (
        "waiting_user" if res.get("status") == "awaiting_approval" else "failed")
    _finish(run_id, conversation_id, supervisor_id, status,
            res.get("content") or "", "schedule")
    return {"ok": status == "completed", "status": status, "content": res.get("content")}
