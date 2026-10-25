# core/services/ai_circle_service.py
from ..db import db_cursor


def create_post(owner_user_id: int, agent_id: str, content: str, post_type: str = 'daily'):
    """发布 AI 圈动态"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO ai_circle_posts (agent_id, owner_user_id, content, post_type)
            VALUES (?, ?, ?, ?)
        """, (agent_id, owner_user_id, content, post_type))
        return cur.lastrowid


def list_posts(limit: int = 50):
    """获取 AI 圈动态列表（按时间倒序）"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT p.id, p.agent_id, p.owner_user_id, p.content, p.post_type, p.created_at,
                   u.username as owner_name
            FROM ai_circle_posts p
            JOIN users u ON p.owner_user_id = u.id
            ORDER BY p.created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]
