import json
from datetime import datetime
from typing import Optional
from ...db import db_cursor

def list_conversations(user_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT c.id, c.title, c.agent_id, c.updated_at, c.unread_count, c.is_pinned,
                   c.target_user_id, c.is_friend_chat, c.friend_mode,
                   (SELECT content FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_message,
                   (SELECT sender FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_sender,
                   (SELECT sender_agent_id FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_sender_agent_id
            FROM conversations c
            WHERE c.user_id=?
            ORDER BY c.is_pinned DESC, c.updated_at DESC
        """, (user_id,))
        rows = cur.fetchall()

    conversations = []
    for row in rows:
        row = dict(row)
        if row.get("last_sender_agent_id"):
            with db_cursor() as cur2:
                cur2.execute("SELECT name FROM model_configs WHERE id=?", (row["last_sender_agent_id"],))
                agent = cur2.fetchone()
                row["last_sender_name"] = agent["name"] if agent else "智能体"
        else:
            row["last_sender_name"] = "我" if row.get("last_sender") == "user" else "AI"
        conversations.append(row)

    return conversations

def create_conversation(user_id: int, agent_id: str = None, title: str = "新会话"):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO conversations (user_id, agent_id, title)
            VALUES (?, ?, ?)
        """, (user_id, agent_id, title))
        return cur.lastrowid

def get_messages(user_id: int, conversation_id: int, limit: int = 50, offset: int = 0, after_id: Optional[int] = None):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
        if not cur.fetchone():
            return None

        query = """
            SELECT m.id, m.sender, m.content, m.sender_agent_id, m.created_at,
                   m.hlc_ts, m.origin_node,
                   CASE WHEN m.sender_agent_id IS NOT NULL THEN mc.name
                        WHEN m.sender = 'user' THEN '我'
                        ELSE 'AI' END as sender_name
            FROM messages m
            LEFT JOIN model_configs mc ON m.sender_agent_id = mc.id
            WHERE m.conversation_id=?
        """
        params = [conversation_id]

        if after_id is not None:
            query += " AND m.id > ?"
            params.append(after_id)

        query += " ORDER BY m.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

    messages = [dict(row) for row in rows]
    messages.reverse()
    return messages

def mark_conversation_read(user_id: int, conversation_id: int):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE conversations SET unread_count=0 WHERE id=? AND user_id=?", (conversation_id, user_id))
    return True

def toggle_pin_conversation(user_id: int, conversation_id: int, pinned: bool):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE conversations SET is_pinned=? WHERE id=? AND user_id=?", (1 if pinned else 0, conversation_id, user_id))
    return True

def delete_conversation(user_id: int, conversation_id: int):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM swarm_pending_tasks WHERE conversation_id=?", (conversation_id,))
        cur.execute("DELETE FROM swarm_reviews WHERE conversation_id=?", (conversation_id,))
        cur.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        cur.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
    return True

