# -*- coding: utf-8 -*-
"""任务状态快照服务——active_task_snapshot 唯一写入口"""
import json
import hashlib
import re
from datetime import datetime
from core.db import db_cursor


def _now():
    return datetime.utcnow().isoformat()


def _fp(goal):
    s = re.sub(r'\\s+', '', goal or '')
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _update(conv_id, task_id, status, snap):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE conversations SET active_task_id=?, active_task_status=?, active_task_snapshot=? WHERE id=?",
            (task_id, status, json.dumps(snap, ensure_ascii=False), conv_id)
        )


def open_task(conv_id, task_id, goal, user_id=None):
    fp = _fp(goal)
    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM supervisor_runs WHERE task_fingerprint=? AND (status='running' OR (status='completed' AND finished_at > datetime('now','-5 minutes')))",
            (fp,)
        )
        dup = cur.fetchone()
    if dup:
        _dup_id = dup['id'] if isinstance(dup, dict) else dup[0]
        return {"status": "duplicate", "existing_task_id": _dup_id}
    snap = {
        "task_id": task_id, "goal": goal, "status": "running",
        "progress": {"total": 0, "completed": 0, "current_step": 1},
        "current_step_desc": "", "failed_summary": [],
        "tried_strategies": [], "last_user_intent": "new_task",
        "updated_at": _now()
    }
    _update(conv_id, task_id, "running", snap)
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET task_fingerprint=? WHERE id=?", (fp, task_id))
    return {"status": "opened", "task_id": task_id}


def update_progress(conv_id, step, status, failed_info=None):
    with db_cursor() as cur:
        cur.execute("SELECT active_task_snapshot FROM conversations WHERE id=?", (conv_id,))
        row = cur.fetchone()
    if not row:
        return
    raw = row['active_task_snapshot'] if isinstance(row, dict) else row[0]
    if not raw:
        return
    try:
        snap = json.loads(raw)
    except Exception:
        return
    if status == "success":
        snap["progress"]["completed"] = step
    snap["progress"]["current_step"] = step + 1
    if failed_info:
        snap["failed_summary"].append({
            "step": step,
            "tool": failed_info.get("tool"),
            "reason": str(failed_info.get("reason"))[:200]
        })
        snap["failed_summary"] = snap["failed_summary"][-5:]
    snap["updated_at"] = _now()
    _update(conv_id, snap["task_id"], "running", snap)


def finish_task(conv_id, status, evidence=None):
    with db_cursor() as cur:
        cur.execute("SELECT active_task_snapshot FROM conversations WHERE id=?", (conv_id,))
        row = cur.fetchone()
    if not row:
        return
    raw = row['active_task_snapshot'] if isinstance(row, dict) else row[0]
    if not raw:
        return
    try:
        snap = json.loads(raw)
    except Exception:
        return
    snap["status"] = status
    snap["finished_at"] = _now()
    if evidence:
        snap["evidence"] = evidence
    _update(conv_id, snap["task_id"], status, snap)


def get_snapshot(conv_id):
    with db_cursor() as cur:
        cur.execute("SELECT active_task_snapshot FROM conversations WHERE id=?", (conv_id,))
        row = cur.fetchone()
    if not row:
        return {}
    raw = row['active_task_snapshot'] if isinstance(row, dict) else row[0]
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def set_user_intent(conv_id, intent, message):
    with db_cursor() as cur:
        cur.execute("SELECT active_task_snapshot FROM conversations WHERE id=?", (conv_id,))
        row = cur.fetchone()
    if not row:
        return
    raw = row['active_task_snapshot'] if isinstance(row, dict) else row[0]
    if not raw:
        return
    try:
        snap = json.loads(raw)
    except Exception:
        return
    snap["last_user_intent"] = intent
    snap["last_user_message"] = (message or "")[:200]
    snap["updated_at"] = _now()
    _update(conv_id, snap["task_id"], snap["status"], snap)


_TERMINAL_RUN = ("completed", "failed", "cancelled", "canceled", "loop_detected", "no_progress", "stopped", "aborted", "error")


def _judge_snapshot(snap, run_status, now, max_age_hours=24):
    st = snap.get("status")
    age_h = None
    try:
        age_h = (now - datetime.fromisoformat(str(snap.get("updated_at")))).total_seconds() / 3600.0
    except Exception:
        age_h = None
    if st == "running":
        if run_status is None or run_status in _TERMINAL_RUN or (age_h is not None and age_h > 12):
            if age_h is not None and age_h > max_age_hours:
                return "zombie_old"
            return "zombie"
        return "ok"
    if st in ("paused", "failed"):
        if age_h is not None and age_h > max_age_hours:
            return "expired"
    return "ok"


def get_snapshot_fresh(conv_id, max_age_hours=24):
    snap = get_snapshot(conv_id)
    if not snap:
        return {}
    try:
        run_status = None
        if snap.get("status") == "running":
            if snap.get("task_id") is None:
                return snap
            with db_cursor() as cur:
                cur.execute("SELECT status FROM supervisor_runs WHERE id=?", (snap.get("task_id"),))
                r = cur.fetchone()
            if r:
                run_status = r["status"] if isinstance(r, dict) else r[0]
        verdict = _judge_snapshot(snap, run_status, datetime.utcnow(), max_age_hours)
        if verdict == "expired":
            return {}
        if verdict in ("zombie", "zombie_old"):
            snap["status"] = "failed"
            snap["finished_at"] = _now()
            fs = snap.get("failed_summary") or []
            fs.append({"step": (snap.get("progress") or {}).get("current_step", 0), "tool": "", "reason": "zombie snapshot, run is no longer active"})
            snap["failed_summary"] = fs[-5:]
            _update(conv_id, snap.get("task_id"), "failed", snap)
            if verdict == "zombie_old":
                # 保留 snapshot 让用户能看到"任务失败了"，而不是完全消失
                return snap
        return snap
    except Exception:
        return snap
