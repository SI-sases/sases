# core/services/execution_gateway.py
# -*- coding: utf-8 -*-
"""Step 2: 统一执行入口（A2A / 定时）→ agent_loop。"""
import asyncio
import os
from datetime import datetime

from ..db import db_cursor
from . import agent_loop


async def _a2a_heartbeat(target_user_id, stop_event):
    while not stop_event.is_set():
        try:
            await asyncio.sleep(10)
            if stop_event.is_set():
                break
            from ..api_routes.ws_routes import broadcast_to_user
            await broadcast_to_user(target_user_id, {
                "type": "sases_a2a_progress",
                "content": "对方智能体正在执行…",
            })
        except Exception:
            pass


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
    if os.getenv("SASES_MEMORY_WRITE", "1") == "1" and status == "completed":
        _min_chars = int(os.getenv("SASES_MEMORY_MIN_CHARS", "20"))
        if len(text) < _min_chars:
            return
        try:
            from . import memory_service, project_service
            with db_cursor() as _mc:
                _mc.execute("SELECT user_id, goal FROM supervisor_runs WHERE id=?", (run_id,))
                _mr = _mc.fetchone()
            if _mr:
                _uid = int(_mr["user_id"])
                _goal = str(_mr["goal"] or "")
                try:
                    memory_service.remember(_uid, "task_result", text[:2000],
                                            task_id=str(run_id), importance=0.6)
                except Exception as _e_mem:
                    print("[memory] 写入失败: " + str(_e_mem))
                try:
                    project_service.import_execution_note(str(run_id), _uid, _goal, text[:2000], "", "success")
                except Exception as _e_pj:
                    print("[project] 写入失败: " + str(_e_pj))
        except Exception as _e_m4:
            print("[memory] M4 写入失败: " + str(_e_m4))
    if source == "group":
        try:
            from . import group_service
            gid = -int(conversation_id)
            with db_cursor() as _uc:
                _uc.execute("SELECT user_id FROM supervisor_runs WHERE id=?", (run_id,))
                _urow = _uc.fetchone()
            _uid = int(_urow["user_id"]) if _urow else 0
            group_service.insert_agent_message(gid, supervisor_id or "sases_assistant", text, trigger_user_id=_uid)
            try:
                import asyncio
                from ..db import db_cursor as _dc
                with _dc() as _c:
                    _c.execute("SELECT global_group_id FROM groups WHERE id=?", (gid,))
                    _g = _c.fetchone()
                if _g and _g["global_group_id"]:
                    from ..api_routes.ws_routes import broadcast_to_group
                    asyncio.create_task(broadcast_to_group(_g["global_group_id"], {
                        "type": "message", "content": text,
                        "sender_id": None, "sender_agent_id": supervisor_id,
                    }))
            except Exception:
                pass
        except Exception as e:
            print("[gateway] 群结果落库失败: " + str(e))
        return
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
    stop_event = asyncio.Event()
    hb_task = None
    try:
        with db_cursor() as cur:
            cur.execute("SELECT target_user_id FROM conversations WHERE id=?", (run["conversation_id"],))
            row = cur.fetchone()
        target_uid = row["target_user_id"] if row else None
        if target_uid:
            hb_task = asyncio.create_task(_a2a_heartbeat(target_uid, stop_event))
        res = await agent_loop.run(
            run["user_id"], run["conversation_id"], run["goal"],
            max_steps=10, run_id=run_id, mode="strict",
        )
    except Exception as e:
        _finish(run_id, run["conversation_id"], run["supervisor_id"], "failed", "执行失败：" + str(e), "a2a")
        return {"ok": False, "error": str(e)}
    finally:
        stop_event.set()
        if hb_task:
            hb_task.cancel()
    status = "completed" if res.get("status") == "ok" else (
        "waiting_user" if res.get("status") in ("awaiting_approval", "awaiting_user") else "failed")
    _finish(run_id, run["conversation_id"], run["supervisor_id"], status,
            res.get("content") or "", "a2a")
    return {"ok": status == "completed", "status": status, "content": res.get("content")}


async def resume_run(run_id, answer_text):
    """ask_user v2：用户回答后继续同一个 run。"""
    run = _get_run(run_id)
    if not run:
        return {"ok": False, "error": "run not found"}
    source = "a2a"
    try:
        if int(run["conversation_id"]) < 0:
            source = "group"
        else:
            with db_cursor() as cur:
                cur.execute("SELECT is_friend_chat FROM conversations WHERE id=?", (run["conversation_id"],))
                r = cur.fetchone()
            if not r or not r["is_friend_chat"]:
                source = "schedule"
    except Exception:
        pass
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='running', finished_at=NULL WHERE id=?", (run_id,))
    try:
        res = await agent_loop.run(
            run["user_id"], run["conversation_id"], answer_text,
            max_steps=10, run_id=run_id, mode="strict", resume=True,
        )
    except Exception as e:
        _finish(run_id, run["conversation_id"], run["supervisor_id"], "failed",
                "继续执行失败：" + str(e), source)
        return {"ok": False, "error": str(e)}
    status = "completed" if res.get("status") == "ok" else (
        "waiting_user" if res.get("status") in ("awaiting_approval", "awaiting_user") else "failed")
    _finish(run_id, run["conversation_id"], run["supervisor_id"], status,
            res.get("content") or "", source)
    return {"ok": status == "completed", "status": status, "content": res.get("content")}


async def resume_after_approval(run_id):
    """审批通过后：执行被拦的工具，再把结果喂回同一 loop。"""
    run = _get_run(run_id)
    if not run:
        return {"ok": False, "error": "run not found"}
    from . import approval_service, agent_memory
    pending = approval_service.get_pending(run_id)
    source = "a2a"
    try:
        if int(run["conversation_id"]) < 0:
            source = "group"
        else:
            with db_cursor() as cur:
                cur.execute("SELECT is_friend_chat FROM conversations WHERE id=?", (run["conversation_id"],))
                r = cur.fetchone()
            if not r or not r["is_friend_chat"]:
                source = "schedule"
    except Exception:
        pass
    if pending:
        try:
            from .. import tool_gateway
            r = await tool_gateway.invoke_tool_async(pending["tool_id"], pending.get("args") or {})
            ok = bool(getattr(r, "success", False))
            text = str(getattr(r, "result", "") or getattr(r, "error", ""))[:4000]
        except Exception as e:
            ok, text = False, "工具执行失败：" + str(e)
        try:
            if agent_memory.replace_tool_result(run["conversation_id"], pending.get("tool_call_id"), text) == 0:
                agent_memory.append(run["conversation_id"], "tool", text, tool_call_id=pending.get("tool_call_id"))
        except Exception:
            pass
        approval_service.clear_pending(pending["id"])
    try:
        res = await agent_loop.run(
            run["user_id"], run["conversation_id"], run["goal"],
            max_steps=10, run_id=run_id, mode="strict", resume=True,
        )
    except Exception as e:
        _finish(run_id, run["conversation_id"], run["supervisor_id"], "failed",
                "审批后继续执行失败：" + str(e), source)
        return {"ok": False, "error": str(e)}
    status = "completed" if res.get("status") == "ok" else (
        "waiting_user" if res.get("status") in ("awaiting_approval", "awaiting_user") else "failed")
    _finish(run_id, run["conversation_id"], run["supervisor_id"], status,
            res.get("content") or "", source)
    return {"ok": status == "completed", "status": status,
            "content": res.get("content") or "", "steps": res.get("steps")}


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
        "waiting_user" if res.get("status") in ("awaiting_approval", "awaiting_user") else "failed")
    _finish(run_id, conversation_id, supervisor_id, status,
            res.get("content") or "", "schedule")
    return {"ok": status == "completed", "status": status, "content": res.get("content")}
