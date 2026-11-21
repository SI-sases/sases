# core/services/message/reply.py
# -*- coding: utf-8 -*-
"""D: 回复落库（消息 + 会话时间）。"""
from datetime import datetime

from ...db import db_cursor


def insert_message(conversation_id, content, sender_agent_id=None,
                   msg_type="standard", attachments="[]", sender="assistant"):
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, sender, content, sender_agent_id, msg_type, attachments),
            )
        else:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, sender, content, msg_type, attachments),
            )
        mid = cur.lastrowid
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), conversation_id))
    try:
        from .. import agent_memory as _am
        _am.append(conversation_id, sender, content)
    except Exception as e:
        print("[agent_memory] reply 双写失败: " + str(e))
    return mid
