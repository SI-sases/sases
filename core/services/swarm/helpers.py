from datetime import datetime
from typing import Optional
from ...db import db_cursor

# ========== 工具函数 ==========

def pick_swarm_agents(user_id: int) -> tuple:
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, name FROM model_configs WHERE user_id=? ORDER BY id ASC",
            (user_id,)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return None, None

    commander_id = None
    executor_id = None

    for r in rows:
        name = (r.get("name") or "").lower()
        if commander_id is None and ("指挥" in name or "commander" in name):
            commander_id = r["id"]
        if executor_id is None and ("执行" in name or "executor" in name):
            executor_id = r["id"]

    if commander_id is None:
        commander_id = rows[0]["id"]
    if executor_id is None:
        if len(rows) >= 2:
            for r in rows:
                if r["id"] != commander_id:
                    executor_id = r["id"]
                    break
            if executor_id is None:
                executor_id = commander_id
        else:
            executor_id = commander_id

    return commander_id, executor_id


def _get_conversation_history(conversation_id: int, limit: int = 10) -> str:
    if not conversation_id:
        return ""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT sender, content, sender_agent_id
            FROM messages
            WHERE conversation_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return ""

    rows.reverse()

    lines = []
    for r in rows:
        content = (r.get("content") or "").strip()
        if content.startswith("[TASK]:") or content.startswith("[STEP_DONE]:"):
            continue
        if content.startswith("[RETRY_TASK]:"):
            continue
        if content.startswith("[TASK_DRAFT]:"):
            continue
        if not content:
            continue
        if len(content) > 200:
            content = content[:200] + "..."

        sender = r.get("sender", "?")
        if sender == "user":
            who = "用户"
        else:
            who = "AI"
        lines.append(f"{who}: {content}")

    if not lines:
        return ""

    return "\n".join(lines[-limit:])


def _insert_message(conversation_id: int, content: str, sender_agent_id: Optional[str] = None):
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                (conversation_id, content, sender_agent_id)
            )
        else:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                (conversation_id, content)
            )
        cur.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), conversation_id)
        )
        _msg_id = cur.lastrowid
        cur.execute("SELECT user_id FROM conversations WHERE id=?", (conversation_id,))
        _row_u = cur.fetchone()
        _uid = _row_u["user_id"] if _row_u else None
    _protocols = ('[TASK]:', '[STEP_DONE]:', '[RETRY_TASK]:', '[TASK_DRAFT]:', '[SUPERVISOR_PROGRESS]:')
    _should_bc = _uid and sender_agent_id and not (content or '').startswith(_protocols)
    if _should_bc:
        try:
            import asyncio as _aio
            from ...api_routes.ws_routes import broadcast_to_user as _bc_u
            _loop = _aio.get_running_loop()
            _display = content or ''
            if _display.startswith('[SUMMARY]:'):
                _display = _display[len('[SUMMARY]:'):]
            _loop.create_task(_bc_u(_uid, {
                'type': 'new_message',
                'message_id': _msg_id,
                'conversation_id': conversation_id,
                'sender': 'assistant' if sender_agent_id else 'user',
                'content': _display,
                'sender_agent_id': sender_agent_id,
                'created_at': datetime.now().isoformat(),
            }))
        except RuntimeError:
            pass
        except Exception as _e_bc:
            print('[ws] insert_message broadcast failed: ' + str(_e_bc))
    return _msg_id
