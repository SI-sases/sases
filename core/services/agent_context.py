# core/services/agent_context.py
# -*- coding: utf-8 -*-
"""M3: 运行时上下文 provider（只放请求尾部，不写入 agent_messages）。"""
import os

from . import memory_service, project_service


def _is_task(goal, mode):
    if (mode or "").lower() == "strict":
        return True
    try:
        from . import intent_service
        return intent_service.route_intent(goal).get("intent") in ("task", "schedule")
    except Exception:
        return False


def build_runtime_context(user_id, conversation_id, goal, mode="fast"):
    if os.getenv("SASES_RUNTIME_CONTEXT", "0") != "1":
        return ""
    if not _is_task(goal, mode):
        return ""
    parts = []
    _recall = os.getenv("SASES_RUNTIME_RECALL", "0") == "1"
    if _recall:
        try:
            mems = memory_service.recall(user_id=user_id, query=goal, top_k=3)
            if mems:
                lines = []
                for m in mems[:3]:
                    text = str(m.get("content") or "").strip()
                    if text:
                        lines.append("- " + text[:300])
                if lines:
                    parts.append("【相关记忆】\n" + "\n".join(lines))
        except Exception as e:
            print("[context] memory recall 失败: " + str(e))
        try:
            chunks = project_service.retrieve_project_chunks(goal, top_k=3, user_id=user_id)
            if chunks:
                lines = []
                for c in chunks[:3]:
                    text = str(c.get("content") or c.get("text") or "").strip()
                    if text:
                        lines.append("- " + text[:300])
                if lines:
                    parts.append("【项目片段】\n" + "\n".join(lines))
        except Exception as e:
            print("[context] project retrieve 失败: " + str(e))
    try:
        from . import task_state_service
        snap = task_state_service.get_snapshot_fresh(conversation_id) if conversation_id else {}
        if snap and snap.get("status") in ("running", "paused", "failed") and snap.get("goal"):
            prog = snap.get("progress") or {}
            parts.append("【当前任务】\n目标：" + str(snap.get("goal"))[:200] +
                         "\n状态：" + str(snap.get("status")) +
                         "  进度：" + str(prog.get("completed", 0)) + "/" + str(prog.get("total", 0)))
    except Exception:
        pass
    if not parts:
        return ""
    text = "【运行时上下文】\n" + "\n\n".join(parts)
    return text[:2400]
