# core/services/scheduled_task_service.py
import json
import uuid
from datetime import datetime, timedelta
from ..db import db_cursor
from . import credit_service
from . import license_service


def create_task(user_id, name, cron_expr, task_template, conversation_id, supervisor_id, timezone='Asia/Shanghai', capsule_snapshot=None):
    task_id = 'sched_' + uuid.uuid4().hex[:16]
    now = datetime.now().isoformat()
    next_run = _compute_next_run(cron_expr)
    params = json.dumps({
        'conversation_id': conversation_id,
        'supervisor_id': supervisor_id,
        'capsule_snapshot': capsule_snapshot or {},
    })
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO scheduled_tasks (id, user_id, name, cron_expr, timezone, task_template, task_params, enabled, missed_policy, failure_count, next_run_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'catch_up', 0, ?, ?, ?)",
            (task_id, user_id, name, cron_expr, timezone, task_template, params, next_run, now, now)
        )
    return task_id


def list_tasks(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM scheduled_tasks WHERE user_id=? ORDER BY created_at DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_task(task_id, user_id=None):
    with db_cursor() as cur:
        if user_id:
            cur.execute("SELECT * FROM scheduled_tasks WHERE id=? AND user_id=?", (task_id, user_id))
        else:
            cur.execute("SELECT * FROM scheduled_tasks WHERE id=?", (task_id,))
        r = cur.fetchone()
        return dict(r) if r else None


def delete_task(task_id, user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM scheduled_tasks WHERE id=? AND user_id=?", (task_id, user_id))
        return cur.rowcount > 0


def toggle_task(task_id, user_id, enabled):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE scheduled_tasks SET enabled=?, updated_at=? WHERE id=? AND user_id=?",
                    (1 if enabled else 0, datetime.now().isoformat(), task_id, user_id))
        return cur.rowcount > 0


def pause_task(task_id, reason):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE scheduled_tasks SET enabled=0, paused_reason=?, updated_at=? WHERE id=?",
                    (reason, datetime.now().isoformat(), task_id))


async def execute_task(task):
    user_id = task['user_id']
    task_id = task['id']

    # 闸门 1：CDK
    try:
        lic_ok, lic_reason = license_service.verify_license_json()
        if not lic_ok:
            pause_task(task_id, 'license_expired:' + str(lic_reason))
            return {'ok': False, 'error': 'license_expired'}
    except Exception as e:
        pause_task(task_id, 'license_check_error')
        return {'ok': False, 'error': 'license_check_error: ' + str(e)}

    # 闸门 2：积分
    try:
        balance = credit_service.get_balance(user_id)
        if balance < 5:
            pause_task(task_id, 'insufficient_credits')
            return {'ok': False, 'error': 'insufficient_credits'}
    except Exception as e:
        return {'ok': False, 'error': 'credit_check_error: ' + str(e)}

    params = json.loads(task.get('task_params') or '{}')
    cid = params.get('conversation_id')
    sid = params.get('supervisor_id')
    if not cid or not sid:
        pause_task(task_id, 'missing_params')
        return {'ok': False, 'error': 'missing_params'}

    goal = '#4: ' + task['task_template']

    try:
        from .supervisor.runs import create_run
        from . import run_service

        run_id = create_run(
            user_id=user_id,
            conversation_id=cid,
            supervisor_id=sid,
            goal=goal,
        )

        gw = await run_service.run_once(
            user_id, cid, goal, source="schedule", supervisor_id=sid,
            max_steps=8, run_id=run_id,
        )
        if gw.get("status") != "completed":
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE scheduled_tasks SET failure_count=failure_count+1, "
                            "next_run_at=?, updated_at=? WHERE id=?",
                            (_backoff_next(task.get('failure_count') or 0), datetime.now().isoformat(), task_id))
            return {'ok': False, 'error': 'loop_failed: ' + str(gw.get('status') or gw.get('error'))}

        next_run = _compute_next_run(task['cron_expr'])
        now = datetime.now().isoformat()
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE scheduled_tasks SET last_run_at=?, next_run_at=?, failure_count=0, updated_at=? WHERE id=?",
                        (now, next_run, now, task_id))
        return {'ok': True, 'run_id': run_id}
    except Exception as e:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE scheduled_tasks SET failure_count=failure_count+1, "
                        "next_run_at=?, updated_at=? WHERE id=?",
                        (_backoff_next(task.get('failure_count') or 0), datetime.now().isoformat(), task_id))
        # 连续失败 3 次自动暂停
        with db_cursor() as cur:
            cur.execute("SELECT failure_count FROM scheduled_tasks WHERE id=?", (task_id,))
            r = cur.fetchone()
            if r and r['failure_count'] >= 3:
                pause_task(task_id, 'consecutive_failures')
        return {'ok': False, 'error': str(e)}


def _backoff_next(failure_count):
    try:
        n = max(0, int(failure_count or 0))
    except Exception:
        n = 0
    seconds = min(3600, 60 * (2 ** min(n, 5)))
    return (datetime.now() + timedelta(seconds=seconds)).isoformat()


def _compute_next_run(cron_expr):
    """极简 cron：支持 'M H * * *'（每天）、'M H * * D'（每周，0=周一）、'M */N * * *'（每 N 小时）。"""
    parts = (cron_expr or '').split()
    now = datetime.now()
    try:
        if len(parts) >= 5 and parts[1].startswith('*/') and parts[1][2:].isdigit():
            step = max(1, int(parts[1][2:]))
            minute = int(parts[0])
            nxt = now.replace(minute=minute, second=0, microsecond=0)
            while nxt <= now:
                nxt += timedelta(hours=step)
            return nxt.isoformat()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            minute = int(parts[0])
            hour = int(parts[1])
            nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if len(parts) >= 5 and parts[4].isdigit():
                target = int(parts[4])  # 0=Monday
                days_ahead = (target - now.weekday()) % 7
                nxt = nxt + timedelta(days=days_ahead)
            if nxt <= now:
                nxt += timedelta(days=7 if (len(parts) >= 5 and parts[4].isdigit()) else 1)
            return nxt.isoformat()
    except Exception as e:
        print('[scheduled] _compute_next_run 失败: ' + str(e))
    return (now + timedelta(days=1)).isoformat()