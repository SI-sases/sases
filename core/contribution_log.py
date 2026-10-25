import sqlite3
import json
import time
import os

from core import config

DB_FILE = config.DB_FILE

def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_log_table():
    with _get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contribution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            target_id TEXT,
            metadata TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 添加索引，提高查询性能
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contrib_user ON contribution_log(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contrib_event ON contribution_log(event_type)")

def log_event(user_id, event_type, target_id=None, metadata=None):
    """记录一条贡献事件到数据库。"""
    init_log_table()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO contribution_log (user_id, event_type, target_id, metadata) VALUES (?, ?, ?, ?)",
            (user_id, event_type, target_id, json.dumps(metadata or {}, ensure_ascii=False))
        )

def get_user_logs(user_id, limit=50):
    """获取指定用户的贡献日志。"""
    init_log_table()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, event_type, target_id, metadata, timestamp FROM contribution_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [{
            "id": r["id"],
            "event_type": r["event_type"],
            "target_id": r["target_id"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
            "timestamp": r["timestamp"]
        } for r in rows]

def get_all_logs(limit=100):
    """获取全部贡献日志（管理员用）。"""
    init_log_table()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, user_id, event_type, target_id, metadata, timestamp FROM contribution_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{
            "id": r["id"],
            "user_id": r["user_id"],
            "event_type": r["event_type"],
            "target_id": r["target_id"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
            "timestamp": r["timestamp"]
        } for r in rows]

def count_logs():
    """返回日志总条数。"""
    init_log_table()
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM contribution_log").fetchone()[0]

def get_contrib_leaderboard(top_n=10):
    """
    计算贡献指数排行榜。
    不同事件类型赋予不同权重：
      - seed_submit: 1.0
      - manual_pollinate: 3.0
      - credit_award: 0.5
      - 其他: 1.0
    返回列表: [{"user_id": int, "score": float}]
    """
    init_log_table()
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT user_id, SUM(
                CASE
                    WHEN event_type = 'seed_submit' THEN 1.0
                    WHEN event_type = 'manual_pollinate' THEN 3.0
                    WHEN event_type = 'credit_award' THEN 0.5
                    ELSE 1.0
                END
            ) as score
            FROM contribution_log
            GROUP BY user_id
            ORDER BY score DESC
            LIMIT ?
        """, (top_n,)).fetchall()
        return [{"user_id": r["user_id"], "score": r["score"]} for r in rows]
