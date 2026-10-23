import json
from datetime import datetime
from ...db import db_cursor
from .. import credit_service
from ..swarm.helpers import _insert_message as _im_fin
from .context import _dict
from .constants import MAX_ROUNDS, CREDITS_PER_ROUND

def get_run(run_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM supervisor_runs WHERE id=?', (run_id,))
        return _dict(cur.fetchone())


def create_proposed_run(user_id, conversation_id, supervisor_id, goal, task_type=None):
    """创建 proposed 状态的 run，等用户确认"""
    with db_cursor(commit=True) as cur:
        _tt = task_type if task_type is not None else 'unknown'
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'proposed', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, MAX_ROUNDS, _tt))
        return cur.lastrowid


def confirm_run(run_id, user_id):
    """用户确认，改状态为 running"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='running' WHERE id=? AND user_id=? AND status='proposed'", (run_id, user_id))
        return cur.rowcount > 0


def reject_run(run_id, user_id):
    """用户拒绝，改状态为 rejected"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='rejected', finished_at=? WHERE id=? AND user_id=? AND status='proposed'", (datetime.now().isoformat(), run_id, user_id))
        return cur.rowcount > 0


def get_proposed_run(user_id, conversation_id=None):
    """取最近一条 proposed run"""
    with db_cursor() as cur:
        if conversation_id:
            cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND conversation_id=? AND status='proposed' ORDER BY id DESC LIMIT 1", (user_id, conversation_id))
        else:
            cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND status='proposed' ORDER BY id DESC LIMIT 1", (user_id,))
        return _dict(cur.fetchone())



def get_active_run(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND status IN ('running', 'running_resumed', 'restart_pending') ORDER BY id DESC LIMIT 1", (user_id,))
        run = _dict(cur.fetchone())

    if run and run.get('status') == 'running':
        try:
            from datetime import timedelta
            history = json.loads(run['history'] or '[]')
            last_at = None
            if history:
                last_at = history[-1].get('at')
            if not last_at:
                last_at = run.get('created_at')
            if last_at:
                last_dt = datetime.fromisoformat(last_at.replace('Z', '').replace(' ', 'T'))
                if datetime.now() - last_dt > timedelta(minutes=5):
                    print('[supervisor] run ' + str(run['id']) + ' timeout 5 min, auto abort')
                    finish_run(run['id'], 'timeout')
                    return None
        except Exception as e:
            print('[supervisor] timeout check failed: ' + str(e))

    return run

    # 只有 running 状态才检查超时；proposed 等用户确认，不自动清
    if run and run.get('status') == 'running':
        try:
            from datetime import timedelta
            history = json.loads(run['history'] or '[]')
            last_at = None
            if history:
                last_at = history[-1].get('at')
            if not last_at:
                last_at = run.get('created_at')
            if last_at:
                last_dt = datetime.fromisoformat(last_at.replace('Z', '').replace(' ', 'T'))
                if datetime.now() - last_dt > timedelta(minutes=5):
                    print('[supervisor] run ' + str(run['id']) + ' 超时 30 分钟，自动中断')
                    finish_run(run['id'], 'timeout')
                    return None
        except Exception as e:
            print('[supervisor] 超时检测失败: ' + str(e))

    return run


def create_run(user_id, conversation_id, supervisor_id, goal, task_type=None):
    with db_cursor(commit=True) as cur:
        _tt = task_type if task_type is not None else 'unknown'
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, MAX_ROUNDS, _tt))
        return cur.lastrowid


def cancel_run(run_id, user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='cancelled', finished_at=? WHERE id=? AND user_id=? AND status IN ('running', 'proposed')", (datetime.now().isoformat(), run_id, user_id))
        _ok = cur.rowcount > 0
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE swarm_pending_tasks SET cancelled=1, status='cancelled', updated_at=? WHERE supervisor_run_id=? AND status IN ('pending', 'running')", (datetime.now().isoformat(), run_id))
            _n = cur.rowcount
            if _n:
                print('[supervisor] cancel_run ' + str(run_id) + ' 同时取消 ' + str(_n) + ' 个 swarm 任务')
    except Exception as e:
        print('[supervisor] cancel_run 中断 swarm 失败: ' + str(e))
    return _ok


def finish_run(run_id, status='completed'):
    _conv_id = None
    _sup_id = None
    try:
        with db_cursor() as _c_pre:
            _c_pre.execute('SELECT conversation_id, supervisor_id FROM supervisor_runs WHERE id=?', (run_id,))
            _r_pre = _dict(_c_pre.fetchone())
            if _r_pre:
                _conv_id = _r_pre.get('conversation_id')
                _sup_id = _r_pre.get('supervisor_id')
    except Exception as _e_pre:
        print('[supervisor] finish_run 预查失败: ' + str(_e_pre))
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET status=?, finished_at=? WHERE id=?', (status, datetime.now().isoformat(), run_id))
    try:
        if _conv_id:
            from ..swarm.helpers import _insert_message as _im_fin
            if status == 'completed':
                _msg_fin = '[SUMMARY]:OK 执行已结束'
            elif status == 'waiting_user':
                _msg_fin = '[SUMMARY]:等待你补充信息后继续（可立即发新任务）'
            elif status == 'restart_pending':
                _msg_fin = '[SUMMARY]:改动完成，等待重启验证'
            elif status in ('failed', 'plan_failed', 'error', 'timeout', 'interrupted'):
                _msg_fin = '[SUMMARY]:执行失败（' + str(status) + '）'
            else:
                _msg_fin = '[SUMMARY]:执行结束（' + str(status) + '）'
            _im_fin(_conv_id, _msg_fin, sender_agent_id=_sup_id)
            print('[supervisor] finish_run 推送: ' + _msg_fin)
    except Exception as _e_fin:
        print('[supervisor] finish_run 推送失败: ' + str(_e_fin))
    print('[supervisor] finish_run: ' + str(run_id) + ' -> ' + status)

# (旧版 build_context 已删除，用第 12 行版本)

def record_round(run_id, plan_summary, exec_summary, review=None):
    run = get_run(run_id)
    if not run:
        return
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    new_round = (run['current_round'] or 0) + 1
    history.append({'round': new_round, 'plan': (plan_summary or '')[:300], 'exec': (exec_summary or '')[:500], 'review': review, 'at': datetime.now().isoformat()})
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET history=?, current_round=? WHERE id=?', (json.dumps(history, ensure_ascii=False), new_round, run_id))


def deduct_round(run_id):
    run = get_run(run_id)
    if not run:
        return False
    try:
        bal = credit_service.get_balance(run['user_id'])
    except Exception as e:
        print('[supervisor] 查询余额失败: ' + str(e))
        return False
    if bal < CREDITS_PER_ROUND:
        return False
    try:
        credit_service.deduct_credits(run['user_id'], CREDITS_PER_ROUND, reason='自主模式第' + str((run['current_round'] or 0) + 1) + '轮')
    except Exception as e:
        print('[supervisor] 扣分失败: ' + str(e))
        return False
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET credits_used = credits_used + ? WHERE id=?', (CREDITS_PER_ROUND, run_id))
    return True
