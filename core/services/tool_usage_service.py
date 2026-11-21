# core/services/tool_usage_service.py
# -*- coding: utf-8 -*-
"""工具使用统计：按天聚合，用于判断哪些工具值得保留。"""
from datetime import datetime, date

from ..db import db_cursor


def record(user_id, tool_id, ok=True):
    if not user_id or not tool_id:
        return
    day = date.today().isoformat()
    now = datetime.now().isoformat()
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO tool_usage_daily (user_id, tool_id, day, calls, success, last_at) "
                "VALUES (?,?,?,1,?,?) ON CONFLICT(user_id, tool_id, day) "
                "DO UPDATE SET calls=calls+1, success=success+?, last_at=?",
                (int(user_id), str(tool_id), day, 1 if ok else 0, now, 1 if ok else 0, now),
            )
    except Exception as e:
        print("[tool_usage] 记录失败: " + str(e))


def summary(user_id=None, days=30):
    where = "day >= date('now', ?)"
    args = ["-%d days" % int(days)]
    if user_id:
        where += " AND user_id=?"
        args.append(int(user_id))
    with db_cursor() as cur:
        cur.execute(
            "SELECT tool_id, SUM(calls) AS calls, SUM(success) AS success, MAX(last_at) AS last_at "
            "FROM tool_usage_daily WHERE " + where + " GROUP BY tool_id ORDER BY calls DESC",
            tuple(args),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        c = int(r.get("calls") or 0)
        r["success_rate"] = round(int(r.get("success") or 0) / c, 3) if c else 0.0
    return rows


def prune(days=180):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM tool_usage_daily WHERE day < date('now', ?)", ("-%d days" % int(days),))
        return cur.rowcount
