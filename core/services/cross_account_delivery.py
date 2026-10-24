# core/services/cross_account_delivery.py
import json
import asyncio
from core.db import db_cursor

import json
import asyncio
from datetime import datetime
from ..db import db_cursor

async def deliver_to_linked_accounts(user_id, conversation_id, content, sender_agent_id, msg_type='standard', attachments=None):
    try:
        _att_str = json.dumps(attachments) if attachments else None
        _target_uid = None
        _target_conv_id = None
        _msg_id = None

        with db_cursor(commit=True) as cur:
            # 1. 查找对方的 user_id
            cur.execute("SELECT target_user_id FROM conversations WHERE id=?", (conversation_id,))
            _t_row = cur.fetchone()
            if _t_row and _t_row["target_user_id"]:
                _target_uid = _t_row["target_user_id"]
                
                # 2. 查对方的会话
                cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (_target_uid, user_id))
                _t_conv = cur.fetchone()
                if _t_conv:
                    _target_conv_id = _t_conv["id"]
                    
                    # 3. 写入对方数据库
                    cur.execute(
                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?)",
                        (_target_conv_id, 'friend', content, sender_agent_id, msg_type, _att_str)
                    )
                    _msg_id = cur.lastrowid
                    cur.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (_target_conv_id,))
        
        # 4. 事务提交后，执行 WebSocket 广播
        if _target_uid and _target_conv_id and _msg_id:
            try:
                from core.api_routes.ws_routes import broadcast_to_user
                payload = {
                    "type": "sases_new_message",
                    "sender": "friend",
                    "conversation_id": _target_conv_id,
                    "message_id": _msg_id,
                    "content": content,
                    "sender_agent_id": sender_agent_id
                }
                await broadcast_to_user(_target_uid, payload)
                print(f"[投递成功] 已推送给用户 {_target_uid}, msg_id={_msg_id}")
            except Exception as ex:
                print(f"[投递广播失败] {ex}")
    except Exception as e:
        print(f"[message] 跨账号投递失败: {e}")
