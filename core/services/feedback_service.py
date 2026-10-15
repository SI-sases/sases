# core/services/feedback_service.py
"""反馈信号服务（v0.39.0）

- submit_explicit: 用户点击 👍/👎/🤷
- record_implicit: 系统自动记录（用户点⏹、重复任务等）
- record_follow_up: 24小时后自动归集
- 只写不消费——未来由 L4/L5/常识库读取
"""
import json
from datetime import datetime, timedelta

from ..db import db_cursor


# ========== 时效权重 ==========
def _calc_weight(created_at_iso: str) -> float:
    """距当前时间的权重：越近越值钱"""
    try:
        created = datetime.fromisoformat(created_at_iso)
        delta_days = (datetime.now() - created).total_seconds() / 86400
    except Exception:
        return 1.0
    if delta_days <= 1:
        return 1.0
    if delta_days <= 3:
        return 0.8
    if delta_days <= 7:
        return 0.6
    if delta_days <= 30:
        return 0.3
    return 0.1


# ========== 快照构建 ==========
def _build_task_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks 拉任务快照；任务完成后回退到 reviews"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_text, steps, supervisor_run_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        # 任务已完成：从 supervisor_runs.goal 拉目标
        with db_cursor() as cur:
            cur.execute(
                "SELECT goal FROM supervisor_runs WHERE id=(SELECT supervisor_run_id FROM swarm_reviews WHERE task_id=? LIMIT 1)",
                (task_id,)
            )
            r2 = cur.fetchone()
            _goal = r2["goal"] if r2 and r2["goal"] else ""
        return {
            "user_input": _goal[:2000],
            "mode": "swarm",
            "steps_total": 0,
            "steps_tools": [],
            "retry_count": 0,
            "has_answer": False,
            "context_hint": "",
        }
    try:
        steps = json.loads(row["steps"] or "[]")
    except Exception:
        steps = []
    tools = []
    for s in steps:
        mid = s.get("module_id") or ""
        if mid and mid not in tools:
            tools.append(mid)
    has_answer = any(
        (s.get("module_id") == "answer") or (s.get("command") == "answer")
        for s in steps
    )
    user_text = (row["user_text"] or "")[:2000]
    # 简单启发式：如果 user_text 含 .py/.md 等，视为上下文提示
    context_hint = ""
    if any(ext in user_text for ext in (".py", ".md", ".json", ".txt", ".js")):
        context_hint = "file_path_like"
    return {
        "user_input": user_text,
        "mode": "swarm",
        "steps_total": len(steps),
        "steps_tools": tools,
        "retry_count": 0,  # 从快照里读不到，用默认
        "has_answer": has_answer,
        "context_hint": context_hint,
    }


def _build_result_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks.results 拉结果快照；任务完成后回退到 reviews 统计"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT results, retry_count, status, created_at FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        # 任务已完成：从 swarm_reviews 聚合
        with db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN exec_status='success' THEN 1 ELSE 0 END) as ok FROM swarm_reviews WHERE task_id=?",
                (task_id,)
            )
            r2 = cur.fetchone()
        _total = r2["total"] if r2 else 0
        _ok = r2["ok"] if r2 and r2["ok"] else 0
        return {
            "status": "completed",
            "duration_ms": 0,
            "steps_done": _ok,
            "steps_total": _total,
            "final_output_len": 0,
            "restart_pending": False,
            "files_touched": [],
        }
    try:
        results = json.loads(row["results"] or "[]")
    except Exception:
        results = []
    files = []
    for r in results:
        cmd = str(r.get("command") or "")
        if cmd == "file_patch":
            meta = r.get("params") or {}
            fp = meta.get("file_path") if isinstance(meta, dict) else ""
            if fp and fp not in files:
                files.append(fp)
    # 是否 restart_pending
    restart_pending = row["status"] == "restart_pending"
    # 简单耗时估算：从第一条到最后一秒
    duration_ms = 0
    final_output_len = 0
    if results:
        final_output_len = len(str(results[-1].get("output") or ""))
    return {
        "status": row["status"] or "unknown",
        "duration_ms": duration_ms,
        "steps_done": len([r for r in results if r.get("status") == "success"]),
        "final_output_len": final_output_len,
        "restart_pending": restart_pending,
        "files_touched": files,
    }


# ========== 写 ==========
def submit_explicit(user_id: int, task_id: str, rating: str,
                    reason_tag: str = None, reason_text: str = None,
                    task_source: str = "swarm", conversation_id: int = None) -> dict:
    """用户点击 👍/👎/🤷"""
    if rating not in ("up", "down", "neutral"):
        return {"ok": False, "message": "rating 必须为 up/down/neutral"}

    # 权限校验：task 必须属于该用户
    # 优先 swarm_pending_tasks（任务运行中），任务完成后记录会被删
    # 回退到 swarm_reviews + conversations（任务完成后仍有审核日志）
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_id, conversation_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
        if not row:
            # 回退 1：从 swarm_reviews 拿 conversation_id
            cur.execute(
                "SELECT conversation_id FROM swarm_reviews WHERE task_id=? LIMIT 1",
                (task_id,)
            )
            rev = cur.fetchone()
            if rev and rev["conversation_id"]:
                _cid = rev["conversation_id"]
                # 从 conversations 拿 user_id
                cur.execute("SELECT user_id FROM conversations WHERE id=?", (_cid,))
                conv = cur.fetchone()
                if conv:
                    row = {"user_id": conv["user_id"], "conversation_id": _cid}
        if not row:
            return {"ok": False, "message": "任务不存在或已过期"}
        if int(row["user_id"]) != int(user_id):
            return {"ok": False, "message": "无权反馈"}
        if conversation_id is None:
            conversation_id = row["conversation_id"]

    # 已有反馈？标记旧的 is_latest=0（保留历史）
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE task_feedback SET is_latest=0 WHERE task_id=? AND user_id=?",
            (task_id, user_id)
        )

    task_snap = _build_task_snapshot(task_id)
    result_snap = _build_result_snapshot(task_id)
    now = datetime.now().isoformat()

    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO task_feedback
            (task_id, user_id, conversation_id, task_source, feedback_type,
             rating, reason_tag, reason_text, task_snapshot, result_snapshot,
             metadata, weight, is_latest, task_alive, created_at)
            VALUES (?, ?, ?, ?, 'explicit', ?, ?, ?, ?, ?, ?, 1.0, 1, 1, ?)
        """, (
            task_id, user_id, conversation_id, task_source,
            rating, reason_tag, (reason_text or "")[:500],
            json.dumps(task_snap, ensure_ascii=False),
            json.dumps(result_snap, ensure_ascii=False),
            "{}", now
        ))
        fid = cur.lastrowid
    return {"ok": True, "feedback_id": fid, "message": "已记录"}


def record_implicit(user_id: int, task_id: str, rating: str,
                    signal: str, task_source: str = "swarm") -> dict:
    """系统自动记录（用户点⏹、重复任务等）"""
    if rating not in ("up", "down", "neutral", "silent"):
        return {"ok": False, "message": "rating 非法"}

    task_snap = _build_task_snapshot(task_id)
    result_snap = _build_result_snapshot(task_id)
    now = datetime.now().isoformat()

    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO task_feedback
            (task_id, user_id, conversation_id, task_source, feedback_type,
             rating, reason_tag, reason_text, task_snapshot, result_snapshot,
             metadata, weight, is_latest, task_alive, created_at)
            VALUES (?, ?, NULL, ?, 'implicit', ?, NULL, ?, ?, ?, ?, 0.8, 1, 1, ?)
        """, (
            task_id, user_id, task_source,
            rating, signal,
            json.dumps(task_snap, ensure_ascii=False),
            json.dumps(result_snap, ensure_ascii=False),
            json.dumps({"signal": signal}, ensure_ascii=False),
            now
        ))
        fid = cur.lastrowid
    return {"ok": True, "feedback_id": fid}


# ========== 读 ==========
def get_user_feedback(user_id: int, limit: int = 50, offset: int = 0) -> list:
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, task_id, rating, reason_tag, reason_text,
                   task_snapshot, created_at, feedback_type
            FROM task_feedback
            WHERE user_id=? AND is_latest=1
            ORDER BY id DESC LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        rows = cur.fetchall()
    out = []
    for r in rows:
        try:
            snap = json.loads(r["task_snapshot"] or "{}")
            summary = (snap.get("user_input") or "")[:200]
        except Exception:
            summary = ""
        out.append({
            "feedback_id": r["id"],
            "task_id": r["task_id"],
            "rating": r["rating"],
            "reason_tag": r["reason_tag"],
            "reason_text": r["reason_text"],
            "task_summary": summary,
            "feedback_type": r["feedback_type"],
            "created_at": r["created_at"],
        })
    return out


def get_feedback_by_task(task_id: str) -> list:
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, user_id, rating, reason_tag, reason_text,
                   feedback_type, created_at
            FROM task_feedback
            WHERE task_id=? ORDER BY id DESC
        """, (task_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_stats(user_id: int = None, range_days: int = 7) -> dict:
    """聚合统计（未来仪表盘用）"""
    cutoff = (datetime.now() - timedelta(days=range_days)).isoformat()
    with db_cursor() as cur:
        if user_id:
            cur.execute("""
                SELECT rating, COUNT(*) as cnt FROM task_feedback
                WHERE created_at >= ? AND user_id=? AND is_latest=1
                GROUP BY rating
            """, (cutoff, user_id))
        else:
            cur.execute("""
                SELECT rating, COUNT(*) as cnt FROM task_feedback
                WHERE created_at >= ? AND is_latest=1
                GROUP BY rating
            """, (cutoff,))
        rows = cur.fetchall()
    stats = {"up": 0, "down": 0, "neutral": 0, "silent": 0}
    for r in rows:
        stats[r["rating"] or "unknown"] = r["cnt"]
    return stats