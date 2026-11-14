# core/services/scheduled_task_service.py
import json
import uuid
from datetime import datetime, timedelta
from ..db import db_cursor
from . import credit_service
from . import license_service


def create_task(user_id, name, cron_expr, task_template, conversation_id, supervisor_id, timezone='Asia/Shanghai'):
    task_id = 'sched_' + uuid.uuid4().hex[:16]
    now = datetime.now().isoformat()
    next_run = _compute_next_run(cron_expr)
    params = json.dumps({'conversation_id': conversation_id, 'supervisor_id': supervisor_id})
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
        from . import swarm_service

        run_id = create_run(
            user_id=user_id,
            conversation_id=cid,
            supervisor_id=sid,
            goal=goal,
            trigger_type='scheduled',
            trigger_task_id=task_id,
        )

        plan_result = await swarm_service.plan_task(
            user_id=user_id,
            conversation_id=cid,
            user_input=goal,
            supervisor_id=sid,
            supervisor_run_id=run_id,
        )

        # plan_task 返回 None / no_plan / error 时，标记 run 失败，避免永久卡 running
        if plan_result is None or (isinstance(plan_result, dict) and plan_result.get('status') in ('no_plan', 'error', 'busy')):
            from .supervisor.runs import finish_run
            try:
                finish_run(run_id, 'plan_failed')
            except Exception:
                pass
            reason = plan_result.get('reason') or plan_result.get('message') if isinstance(plan_result, dict) else 'plan_task returned None'
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE scheduled_tasks SET failure_count=failure_count+1, updated_at=? WHERE id=?",
                            (datetime.now().isoformat(), task_id))
            return {'ok': False, 'error': 'plan_failed: ' + str(reason)}

        next_run = _compute_next_run(task['cron_expr'])
        now = datetime.now().isoformat()
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE scheduled_tasks SET last_run_at=?, next_run_at=?, failure_count=0, updated_at=? WHERE id=?",
                        (now, next_run, now, task_id))
        return {'ok': True, 'run_id': run_id}
    except Exception as e:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE scheduled_tasks SET failure_count=failure_count+1, updated_at=? WHERE id=?",
                        (datetime.now().isoformat(), task_id))
        # 连续失败 3 次自动暂停
        with db_cursor() as cur:
            cur.execute("SELECT failure_count FROM scheduled_tasks WHERE id=?", (task_id,))
            r = cur.fetchone()
            if r and r['failure_count'] >= 3:
                pause_task(task_id, 'consecutive_failures')
        return {'ok': False, 'error': str(e)}


def _compute_next_run(cron_expr):
    """极简 cron：只支持 'M H * * *'（每天固定时间）"""
    parts = (cron_expr or '').split()
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        minute = int(parts[0])
        hour = int(parts[1])
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run.isoformat()
    return (datetime.now() + timedelta(days=1)).isoformat()