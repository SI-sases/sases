# core/services/group_agent_service.py
# -*- coding: utf-8 -*-
"""Step 3: 群 @智能体 → execution gateway / agent loop。

群会话用负数 conversation_id（-group_id）作为 agent_messages 的 session key，
不影响真实 conversations。
"""
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
    ensure_session(group_id)
    key = session_key(group_id)
    mode = "strict" if execute else "fast"
    allowed = None if execute else []
    try:
        res = await agent_loop.run(
            user_id, key, question,
            allowed_tool_ids=allowed,
            max_steps=6 if execute else 2,
            mode=mode,
        )
    except Exception as e:
        return False, "群智能体执行失败：" + str(e)
    text = (res.get("content") or "").strip()
    if not text:
        return False, "群智能体没有返回内容"
    group_resource_service.record_usage(group_id, user_id, agent_id, agent_id)
    return True, text
