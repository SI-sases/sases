# core/services/wisdom_space_service.py
from ..db import db_cursor


def get_nodes(user_id: int):
    """获取智维空间节点列表，基于智能体和用户贡献"""
    nodes = []

    with db_cursor() as cur:
        # 1. 智能体节点（用户的智能体）
        cur.execute("""
            SELECT id, model_type, name, provider, model_name, is_shared, visibility, created_at
            FROM model_configs
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,))
        for row in cur.fetchall():
            nodes.append({
                "node_type": "agent",
                "node_id": row["id"],
                "name": row["name"],
                "detail": f"{row['model_type']} · {row['provider'] or row['model_name']}",
                "shared": bool(row["is_shared"]),
                "visibility": row["visibility"],
                "created_at": row["created_at"]
            })

        # 2. 贡献节点（积分历史中正数记录）
        cur.execute("""
            SELECT id, action, points, created_at
            FROM contribution_log
            WHERE user_id=? AND points > 0
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
        for row in cur.fetchall():
            nodes.append({
                "node_type": "contribution",
                "node_id": f"contrib-{row['id']}",
                "name": row["action"] or "贡献",
                "detail": f"+{row['points']} 积分",
                "created_at": row["created_at"]
            })

        # 3. 知识库节点
        cur.execute("SELECT id, task, verified, created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 20")
        for row in cur.fetchall():
            nodes.append({
                "node_type": "knowledge",
                "node_id": f"kb-{row['id']}",
                "name": row["task"],
                "detail": "已验证" if row["verified"] else "未验证",
                "created_at": row["created_at"]
            })

    return nodes
