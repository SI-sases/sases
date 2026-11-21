# core/services/swarm/callbacks.py
# -*- coding: utf-8 -*-
"""D: 执行回调（步骤结果落库 + 触发审核）。"""
import datetime
import json
from typing import Any, Dict

from ...db import db_cursor
from .. import swarm_service


async def report_step_done(conversation_id: int, payload: Dict[str, Any], executor_id: str):
    """把 [STEP_DONE] 写入消息表，并触发审核。"""
    content = "[STEP_DONE]:" + json.dumps(payload, ensure_ascii=False)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
            (conversation_id, content, executor_id),
        )
        cur.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.datetime.now().isoformat(), conversation_id),
        )
    await swarm_service.handle_step_done(conversation_id, payload, executor_id)
