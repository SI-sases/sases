# core/services/trace_service.py
# -*- coding: utf-8 -*-
"""任务执行轨迹（run_trace）：追加写 + 脱敏 + 按 seq 续传 + 保留期清理。

窗口只是入口，任务才是主体；trace 按 run_id 存取，不建真实会话。
"""
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..db import db_cursor

LEVEL_MILESTONE = 1
LEVEL_STEP = 2
LEVEL_TOOL = 3
LEVEL_DEBUG = 4

_ACTIVE_STATUS = ("running", "running_resumed", "paused", "proposed", "restart_pending")

_SENSITIVE = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "***API_KEY***"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+"), "C:\\Users\\***"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "***IP***"),
    (re.compile(r"(?i)password\s*[=:]\s*\S+"), "password=***"),
    (re.compile(r"(?i)token\s*[=:]\s*\S+"), "token=***"),
    (re.compile(r"(?i)authorization:\s*bearer\s+\S+"), "authorization: bearer ***"),
]


def sanitize(text: Any, limit: int = 4000) -> str:
    s = str(text or "")
    for pat, rep in _SENSITIVE:
        s = pat.sub(lambda m, _r=rep: _r, s)
    if len(s) > limit:
        s = s[:limit] + " ...[truncated]"
    return s


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def emit(run_id: int, conversation_id: Optional[int], level: int, event_type: str,
         content: str = "", tool: str = "", status: str = "", duration_ms: int = 0,
         extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """追加一条 trace；seq 由 DB 内 MAX+1 保证单调。"""
    if not run_id:
        return {}
    text = sanitize(content)
    payload = json.dumps(extra, ensure_ascii=False) if extra else None
    ts = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO run_trace (run_id, conversation_id, seq, level, event_type, tool, status, content, duration_ms, extra, created_at) "
            "SELECT ?, ?, COALESCE((SELECT MAX(seq) FROM run_trace WHERE run_id=?), 0) + 1, ?, ?, ?, ?, ?, ?, ?, ?",
            (run_id, conversation_id, run_id, int(level), event_type, tool, status,
             text, int(duration_ms or 0), payload, ts),
        )
        rid = cur.lastrowid
        cur.execute("SELECT seq FROM run_trace WHERE id=?", (rid,))
        row = cur.fetchone()
    seq = (row["seq"] if isinstance(row, dict) else row[0]) if row else 0
    return {"run_id": run_id, "seq": seq, "level": level, "event_type": event_type,
            "tool": tool, "status": status, "content": text,
            "duration_ms": duration_ms, "created_at": ts}


def list_events(run_id: int, after_seq: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 500), 2000))
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, run_id, conversation_id, seq, level, event_type, tool, status, content, duration_ms, extra, created_at "
            "FROM run_trace WHERE run_id=? AND seq>? ORDER BY seq ASC LIMIT ?",
            (run_id, int(after_seq or 0), limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return rows


def _run_rows(sql: str, args: tuple) -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]


def active_runs(conversation_id: int, user_id: int) -> List[Dict[str, Any]]:
    marks = ",".join("?" for _ in _ACTIVE_STATUS)
    return _run_rows(
        "SELECT r.id, r.status, r.goal, r.conversation_id, r.created_at, "
        "COALESCE((SELECT MAX(seq) FROM run_trace t WHERE t.run_id=r.id),0) AS last_seq "
        "FROM supervisor_runs r JOIN conversations c ON c.id=r.conversation_id "
        "WHERE r.conversation_id=? AND c.user_id=? AND r.status IN (" + marks + ") "
        "ORDER BY r.id DESC LIMIT 20",
        (conversation_id, user_id) + tuple(_ACTIVE_STATUS),
    )


def recent_runs(conversation_id: int, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 10), 50))
    return _run_rows(
        "SELECT r.id, r.status, r.goal, r.conversation_id, r.created_at, r.finished_at, "
        "COALESCE((SELECT MAX(seq) FROM run_trace t WHERE t.run_id=r.id),0) AS last_seq "
        "FROM supervisor_runs r JOIN conversations c ON c.id=r.conversation_id "
        "WHERE r.conversation_id=? AND c.user_id=? ORDER BY r.id DESC LIMIT ?",
        (conversation_id, user_id, limit),
    )


def cleanup(level1_days: int = 30, detail_days: int = 7) -> int:
    """L1 保留 30 天，L2-L4 保留 7 天。返回删除条数。"""
    now = datetime.utcnow()
    cut_l1 = (now - timedelta(days=level1_days)).replace(microsecond=0).isoformat()
    cut_detail = (now - timedelta(days=detail_days)).replace(microsecond=0).isoformat()
    deleted = 0
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM run_trace WHERE level>=2 AND created_at < ?", (cut_detail,))
        deleted += cur.rowcount
        cur.execute("DELETE FROM run_trace WHERE level=1 AND created_at < ?", (cut_l1,))
        deleted += cur.rowcount
    return deleted
