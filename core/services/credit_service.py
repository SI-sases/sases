# core/services/credit_service.py
from ..db import db_cursor
from datetime import datetime


def get_balance(user_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT credits FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
    if not user:
        return None
    return user["credits"] or 0


def get_history(user_id: int, limit: int = 50):
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, action, event_type, points, model_source, detail, created_at
            FROM contribution_log
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def add_credit(user_id: int, amount: float, action: str = "手动调整", detail: str = "", event_type: str = "manual"):
    """增加积分（或负数扣减），并写入日志"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (amount, user_id))
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, action, event_type, amount, detail, datetime.now().isoformat()))
    return True


def get_today_passive_points(user_id: int) -> int:
    """获取用户今日被动授粉积分"""
    today_start = datetime.combine(datetime.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='passive_pollination' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


def _ensure_pool_table():
    with db_cursor(commit=True) as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS credit_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            source TEXT,
            created_at TEXT
        )""")


def get_pool_balance():
    _ensure_pool_table()
    with db_cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM credit_pool")
        return cur.fetchone()[0]


def _add_to_pool(amount, source):
    _ensure_pool_table()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO credit_pool (amount, source, created_at) VALUES (?, ?, ?)",
            (amount, source, datetime.now().isoformat())
        )


def get_pool_history(limit: int = 50):
    _ensure_pool_table()
    with db_cursor() as cur:
        cur.execute("SELECT id, amount, source, created_at FROM credit_pool ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def deduct_credits(user_id: int, amount: float, reason: str = "", detail: str = ""):
    """扣减积分，50% 存入积分库（v0.20）"""
    _amt = abs(amount)
    result = add_credit(user_id, -_amt, action=reason or "扣减", detail=detail, event_type="deduct")
    if result and _amt > 0:
        try:
            _add_to_pool(_amt * 0.5, source=reason or "deduct")
        except Exception as _pe:
            print(f'[credit] 存入积分库失败: {_pe}')
    return result
