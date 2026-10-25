# core/services/stats_service.py
import os
import json
from ..db import db_cursor


def get_admin_user_ids():
    """从数据库查询所有管理员用户 ID"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE is_admin=1")
        rows = cur.fetchall()
    return {row["id"] for row in rows}


def get_leaderboard():
    """获取贡献排行榜（按贡献值排序，排除管理员账号）"""
    admin_ids = get_admin_user_ids()

    # 如果没有管理员，避免 SQL 语法错误
    if admin_ids:
        placeholders = ','.join('?' for _ in admin_ids)
        query = f"""
            SELECT u.id, u.username, u.sases_id,
                   COALESCE(SUM(cl.points), 0) AS contribution_score
            FROM users u
            LEFT JOIN contribution_log cl ON u.id = cl.user_id AND cl.points > 0
            WHERE u.id NOT IN ({placeholders})
            GROUP BY u.id
            ORDER BY contribution_score DESC, u.id ASC
            LIMIT 50
        """
        params = tuple(admin_ids)
    else:
        query = """
            SELECT u.id, u.username, u.sases_id,
                   COALESCE(SUM(cl.points), 0) AS contribution_score
            FROM users u
            LEFT JOIN contribution_log cl ON u.id = cl.user_id AND cl.points > 0
            GROUP BY u.id
            ORDER BY contribution_score DESC, u.id ASC
            LIMIT 50
        """
        params = ()

    with db_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    leaderboard = []
    for idx, row in enumerate(rows, start=1):
        leaderboard.append({
            "rank": idx,
            "user_id": row["id"],
            "username": row["username"],
            "sases_id": row["sases_id"] or "",
            "contribution_score": row["contribution_score"] or 0,
            "avatar": row["username"][0].upper() if row["username"] else "?"
        })

    return leaderboard


def get_harness_modules():
    """获取可用的 Harness 模块列表"""
    modules = []
    modules_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'harness_modules')
    if os.path.exists(modules_dir):
        for item in os.listdir(modules_dir):
            manifest_path = os.path.join(modules_dir, item, 'manifest.json')
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    modules.append({
                        "id": manifest.get("id", item),
                        "name": manifest.get("name", item),
                        "description": manifest.get("description", "")
                    })
                except Exception:
                    pass
    return modules
