# core/services/seed_service.py
import json
import os
import secrets
import string
from ..db import db_cursor


def list_seed_tasks(user_id: int = None):
    """获取所有种子任务（若提供 user_id 则过滤）"""
    with db_cursor() as cur:
        if user_id:
            cur.execute("SELECT * FROM seed_tasks WHERE user_id=? ORDER BY created_at DESC", (user_id,))
        else:
            cur.execute("SELECT * FROM seed_tasks ORDER BY created_at DESC")
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def create_seed_task(description: str, domain: str = None, difficulty: str = "medium", user_id: int = None):
    """创建新的种子任务"""
    task_id = "SEED-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO seed_tasks (id, description, domain, difficulty, user_id, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (task_id, description, domain, difficulty, user_id))
    return task_id


def get_seed_task(task_id: str):
    """获取单个种子任务"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM seed_tasks WHERE id=?", (task_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def update_seed_task_status(task_id: str, status: str):
    """更新种子任务状态"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE seed_tasks SET status=? WHERE id=?", (status, task_id))


def process_external_seed(seed_data: dict):
    """处理外部传入的种子数据，写入数据库"""
    # 简单校验
    if "description" not in seed_data or not seed_data["description"]:
        raise ValueError("种子描述不能为空")
    domain = seed_data.get("domain", "综合")
    difficulty = seed_data.get("difficulty", "medium")
    return create_seed_task(seed_data["description"], domain, difficulty)
