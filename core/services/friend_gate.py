from core.db import db_cursor

def check_friend_gate(user_id, conversation_id, sender_agent_id, content, agent_id, mode):
    if not sender_agent_id or not conversation_id:
        return None

    with db_cursor() as _fc:
        _fc.execute("SELECT is_friend_chat, friend_mode FROM conversations WHERE id=?", (conversation_id,))
        _frow = _fc.fetchone()
        if _frow and _frow["is_friend_chat"] == 1:
            _fmode = _frow["friend_mode"]
            if _fmode == 'normal':
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': '你的消息已收到，我目前处于普通接听模式，无法执行指令。',
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                    'friend_mode': 'normal'
                }
            elif _fmode == 'free':
                from core.services.task_engine import dispatch_task
                dispatch_task(user_id, content, context_type="friend", context_id=str(conversation_id))
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': '收到，正在为你执行...',
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                    'friend_mode': 'free'
                }
    return None
