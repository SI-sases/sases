# core/services/run_journal.py
# -*- coding: utf-8 -*-
"""P0：run 租约、步骤日志、停滞/截止检测。"""
from datetime import datetime, timedelta
from typing import Optional, Set

from ..db import db_cursor


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _soon(seconds: int) -> str:
    return (datetime.utcnow() + timedelta(seconds=int(seconds))).replace(microsecond=0).isoformat()


def acquire_lease(run_id: int, owner: str, ttl: int = 30) -> bool:
    """原子抢租约；已过期、无主或自己持有则成功。"""
    if not run_id:
        return False
    now, until = _now(), _soon(ttl)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE supervisor_runs SET lease_owner=?, lease_until=?, heartbeat_at=? "
            "WHERE id=? AND (lease_owner IS NULL OR lease_owner=? OR lease_until IS NULL OR lease_until<?)",
            (owner, until, now, run_id, owner, now),
        )
        return cur.rowcount > 0


def heartbeat(run_id: int, owner: str, ttl: int = 30) -> bool:
    if not run_id:
        return False
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE supervisor_runs SET heartbeat_at=?, lease_until=? WHERE id=? AND lease_owner=?",
            (_now(), _soon(ttl), run_id, owner),
        )
        return cur.rowcount > 0


def release(run_id: int, owner: str):
    if not run_id:
        return
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET lease_owner=NULL, lease_until=NULL WHERE id=? AND lease_owner=?",
                    (run_id, owner))


def set_deadline(run_id: int, seconds: int = 1800):
    if not run_id:
        return
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE supervisor_runs SET deadline_at=? WHERE id=? AND (deadline_at IS NULL OR deadline_at<?)",
            (_soon(seconds), run_id, _now()),
        )


def deadline_expired(run_id: int) -> bool:
    if not run_id:
        return False
    with db_cursor() as cur:
        cur.execute("SELECT deadline_at FROM supervisor_runs WHERE id=?", (run_id,))
        r = cur.fetchone()
    if not r:
        return False
    d = r["deadline_at"] if isinstance(r, dict) else r[0]
    return bool(d and d < _now())


def step_begin(run_id: int, step_id: str, tool_id: str = "", owner: str = "", key: str = "") -> bool:
    if not run_id:
        return False
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO run_steps (run_id, step_id, tool_id, status, attempt, idempotency_key, "
            "lease_owner, lease_until, started_at) VALUES (?,?,?, 'running', 1, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, step_id) DO UPDATE SET status='running', attempt=run_steps.attempt+1, "
            "tool_id=excluded.tool_id, idempotency_key=excluded.idempotency_key, "
            "lease_owner=excluded.lease_owner, lease_until=excluded.lease_until, started_at=excluded.started_at, error=NULL",
            (run_id, str(step_id), tool_id, key or None, owner, _soon(30), _now()),
        )
        return True


def step_end(run_id: int, step_id: str, status: str, output_ref: Optional[str] = None,
             error: Optional[str] = None) -> bool:
    if not run_id:
        return False
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE run_steps SET status=?, output_ref=?, error=?, finished_at=? WHERE run_id=? AND step_id=?",
            ("done" if status == "success" else "failed", output_ref, error, _now(), run_id, str(step_id)),
        )
        return cur.rowcount > 0


def done_step_ids(run_id: int) -> Set[str]:
    if not run_id:
        return set()
    with db_cursor() as cur:
        cur.execute("SELECT step_id FROM run_steps WHERE run_id=? AND status='done'", (run_id,))
        return {str(r["step_id"] if isinstance(r, dict) else r[0]) for r in cur.fetchall()}


def recover_stale() -> int:
    """把租约过期的 running 步骤标记失败，并清掉过期 run 租约。"""
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE run_steps SET status='failed', error='lease_expired', finished_at=? "
            "WHERE status='running' AND lease_until IS NOT NULL AND lease_until<?",
            (now, now),
        )
        n = cur.rowcount
        cur.execute("UPDATE supervisor_runs SET lease_owner=NULL, lease_until=NULL "
                    "WHERE lease_until IS NOT NULL AND lease_until<?", (now,))
    if n:
        print("[journal] 回收过期步骤 " + str(n) + " 个")
    return n


def is_stalled(run_id: int, seconds: int = 180) -> bool:
    if not run_id:
        return False
    with db_cursor() as cur:
        cur.execute("SELECT heartbeat_at FROM supervisor_runs WHERE id=?", (run_id,))
        r = cur.fetchone()
    if not r:
        return False
    hb = r["heartbeat_at"] if isinstance(r, dict) else r[0]
    if not hb:
        return False
    return hb < (datetime.utcnow() - timedelta(seconds=int(seconds))).replace(microsecond=0).isoformat()


# ========== P0-3 副作用幂等 ==========
def effect_get(key: str):
    if not key:
        return None
    with db_cursor() as cur:
        cur.execute("SELECT result_json FROM tool_effects WHERE idempotency_key=?", (key,))
        r = cur.fetchone()
    if not r:
        return None
    return r["result_json"] if isinstance(r, dict) else r[0]


def effect_put(key: str, tool_id: str, result_json: str):
    if not key:
        return
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT OR IGNORE INTO tool_effects (idempotency_key, tool_id, result_json, created_at) VALUES (?,?,?,?)",
            (key, tool_id, result_json, _now()),
        )
