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


async def run_once(user_id, conversation_id, goal, source="chat",
                   supervisor_id="sases_assistant", max_steps=8, skill_ids=None,
                   run_id=None):
    from .agent_loop import run
    from . import supervisor_service
    rid = run_id or create_run(user_id, conversation_id, source, goal, supervisor_id)
    try:
        r = await run(int(user_id), int(conversation_id), str(goal),
                      max_steps=int(max_steps), run_id=int(rid), mode="strict",
                      supervisor_id=supervisor_id, skill_ids=skill_ids)
        status = str(r.get("status") or "")
        mapped = "completed" if status == "ok" else (
            "failed" if status in ("max_steps", "verification_failed", "plan_incomplete",
                                   "plan_required", "error") else status)
        if mapped in ("completed", "failed"):
            try:
                supervisor_service.finish_run(int(rid), mapped)
            except Exception as e:
                print("[run] finish_run 失败: " + str(e))
        return {"run_id": rid, "status": mapped, "loop": r}
    except Exception as e:
        try:
            supervisor_service.finish_run(int(rid), "failed")
        except Exception:
            pass
        return {"run_id": rid, "status": "failed", "error": str(e)}
