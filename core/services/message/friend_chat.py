import json
from datetime import datetime
from ...db import db_cursor
from .. import cross_account_delivery as _cad_fc

async def handle_friend_message(user_id, conversation_id, content, sender_agent_id, msg_type, attachments, _att_str, agent_id, mode):
    """
    处理好友单聊消息：
    1. 落自己的库（防刷新丢失）
    2. 投递给对方（跨账号）
    3. 返回特定 dict 以阻断 send.py 后续的 AI 调用
    """
    # 1. 先落自己的库
    with db_cursor(commit=True) as _c_fc_ins:
        _c_fc_ins.execute(
            "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'user', ?, ?, ?, ?)",
            (conversation_id, content, sender_agent_id, msg_type, _att_str)
        )
        _c_fc_ins.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))
    
    # 2. 再投递给对方
    try:
        await _cad_fc.deliver_to_linked_accounts(user_id, conversation_id, content, sender_agent_id, msg_type, attachments)
        print('[friend_chat] 好友投递成功: conv=' + str(conversation_id))
    except Exception as e:
        print('[friend_chat] 好友投递失败: ' + str(e))
    
    # 3. 纯好友文字聊天拦截退出
    if not sender_agent_id:
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': '',
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
        }
    return None
