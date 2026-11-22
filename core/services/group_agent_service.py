# core/services/group_agent_service.py
# -*- coding: utf-8 -*-
"""Step 3: 群 @智能体 → execution gateway / agent loop。

群会话用负数 conversation_id（-group_id）作为 agent_messages 的 session key，
不影响真实 conversations。
"""
from ..db import db_cursor
from . import agent_loop, agent_memory
from . import group_resource_service


def session_key(group_id):
    return -int(group_id)


def ensure_session(group_id, limit=20):
    key = session_key(group_id)
    if agent_memory.count(key) > 0:
        return key
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute(
            "SELECT sender_agent_id, content FROM group_messages WHERE group_id=? ORDER BY id DESC LIMIT ?",
            (group_id, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    rows.reverse()
    for r in rows:
        text = str(r.get("content") or "")
        if not text or text.startswith(("[TASK_CARD]:", "[RED_PACKET]", "[GROUP_")):
            continue
        agent_memory.append(key, "assistant" if r.get("sender_agent_id") else "user", text)
    return key


async def reply(group_id, user_id, agent_id, question, execute=False):
    ok, quota = group_resource_service.check_quota(group_id, user_id, agent_id)
    if not ok:
        return False, quota
    with db_cursor() as _gc:
        _gc.execute("SELECT mode FROM groups WHERE id=?", (group_id,))
        _gr = _gc.fetchone()
    group_mode = str((_gr["mode"] if _gr else "normal") or "normal")
    swarm = (group_mode == "swarm") or group_resource_service.is_swarm_enabled(group_id)
    ensure_session(group_id)
    key = session_key(group_id)
    mode = "strict" if execute else "fast"
    allowed = None if execute else []
    max_steps = 8 if (execute and swarm) else (6 if execute else 2)

    async def _progress(ev):
        try:
            from ..db import db_cursor as _dc
            with _dc() as _c:
                _c.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
                _r = _c.fetchone()
            if _r and _r["global_group_id"]:
                from ..api_routes.ws_routes import broadcast_to_group
                await broadcast_to_group(_r["global_group_id"], {
                    "type": "agent_progress",
                    "agent_id": agent_id,
                    "tool": (ev or {}).get("tool") or "",
                    "step": (ev or {}).get("step") or 0,
                })
        except Exception:
            pass

    try:
        from ..db import db_cursor as _dc_g
        with _dc_g() as _cg:
            _cg.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _gr = _cg.fetchone()
        _global_gid = _gr["global_group_id"] if _gr else ""
    except Exception:
        _global_gid = ""

    async def _on_token(piece):
        if not piece or not _global_gid:
            return
        try:
            from ..api_routes.ws_routes import broadcast_to_group
            await broadcast_to_group(_global_gid, {
                "type": "token", "msg_id": str(key), "delta": piece,
                "sender_agent_id": agent_id,
            })
        except Exception:
            pass

    try:
        if execute:
            from . import run_service, supervisor_service
            _rr = await run_service.run_once(
                user_id, key, question, source="group", supervisor_id=agent_id,
                max_steps=max_steps, allowed_tool_ids=allowed,
                finish=False, on_event=_progress, on_token=_on_token,
            )
            res = _rr.get("loop") or {}
            try:
                supervisor_service.finish_run(
                    _rr.get("run_id"), "completed" if res.get("status") == "ok" else "failed")
            except Exception:
                pass
        else:
            res = await agent_loop.run(
                user_id, key, question,
                allowed_tool_ids=allowed,
                max_steps=max_steps,
                mode=mode,
                supervisor_id=agent_id,
                on_event=_progress,
                on_token=_on_token,
            )
    except Exception as e:
        return False, "群智能体执行失败：" + str(e)
    text = (res.get("content") or "").strip()
    if not text:
        return False, "群智能体没有返回内容"
    group_resource_service.record_usage(group_id, user_id, agent_id, agent_id)
    return True, text
