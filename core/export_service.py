# core/services/export_service.py
import json
from ..db import db_cursor


def export_user_data(user_id: int) -> dict:
    """导出用户所有数据，返回字典"""
    data = {}

    with db_cursor() as cur:
        # 用户基本信息
        cur.execute("SELECT id, username, sases_id, credits, created_at FROM users WHERE id=?", (user_id,))
        user_row = cur.fetchone()
        if not user_row:
            return {}
        data["user"] = dict(user_row)

        # API Keys（脱敏，只返回供应商和优先级）
        cur.execute("SELECT id, provider, priority, is_active, created_at FROM api_keys WHERE user_id=?", (user_id,))
        data["api_keys"] = [dict(row) for row in cur.fetchall()]

        # 模型配置（不含加密 API Key）
        cur.execute("""
            SELECT id, model_type, name, provider, node_url, model_name, capabilities,
                   is_shared, visibility, price, created_at
            FROM model_configs WHERE user_id=?
        """, (user_id,))
        data["model_configs"] = [dict(row) for row in cur.fetchall()]

        # 积分历史
        cur.execute("SELECT action, event_type, points, model_source, model_id, detail, created_at FROM contribution_log WHERE user_id=?", (user_id,))
        data["credits_history"] = [dict(row) for row in cur.fetchall()]

        # 知识库
        cur.execute("SELECT id, task, branch_a, branch_b, solution, verified, created_at FROM knowledge_base WHERE id IN (SELECT id FROM knowledge_base)")
        # 注意：knowledge_base 表可能没有 user_id，暂按全局导出，后续可加过滤
        data["knowledge"] = [dict(row) for row in cur.fetchall()]

        # 会话
        cur.execute("SELECT id, agent_id, title, created_at, updated_at FROM conversations WHERE user_id=?", (user_id,))
        conversations = [dict(row) for row in cur.fetchall()]
        data["conversations"] = conversations

        # 消息
        cur.execute("""
            SELECT m.* FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.user_id=?
        """, (user_id,))
        data["messages"] = [dict(row) for row in cur.fetchall()]

        # 好友关系
        cur.execute("SELECT id, friend_agent_id, target_user_id, status, created_at FROM agent_friendships WHERE user_id=?", (user_id,))
        data["friendships"] = [dict(row) for row in cur.fetchall()]

    return data
