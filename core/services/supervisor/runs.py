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


def create_run(user_id, conversation_id, supervisor_id, goal, task_type=None, max_rounds: int = None):
    with db_cursor(commit=True) as cur:
        _tt = task_type if task_type is not None else 'unknown'
        _mr = max_rounds if max_rounds is not None else MAX_ROUNDS
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, _mr, _tt))
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
    _TERMINAL = ('completed', 'failed', 'cancelled', 'rejected', 'plan_failed',
                 'no_progress', 'timeout', 'interrupted', 'error', 'waiting_user')
    try:
        with db_cursor() as _c_chk:
            _c_chk.execute('SELECT status FROM supervisor_runs WHERE id=?', (run_id,))
            _row_chk = _c_chk.fetchone()
            if _row_chk:
                _cur_status = _row_chk['status'] if isinstance(_row_chk, dict) else _row_chk[0]
                if _cur_status in _TERMINAL:
                    print('[supervisor] finish_run 跳过: run ' + str(run_id) + ' 已是终态 ' + str(_cur_status) + '，忽略 ' + str(status))
                    return
    except Exception as _e_chk:
        print('[supervisor] finish_run 终态检查失败: ' + str(_e_chk))
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
                try:
                    import json
                    with db_cursor() as _c_his:
                        _c_his.execute('SELECT history FROM supervisor_runs WHERE id=?', (run_id,))
                        _his_row = _c_his.fetchone()
                        if _his_row and _his_row['history']:
                            _hist = json.loads(_his_row['history'])
                            if _hist and len(_hist) > 0:
                                _last = _hist[-1]
                                # 优先从 exec 字段提取（如果有具体的输出结果）
                                _exec_str = _last.get('exec', '')
                                if '|' in _exec_str:
                                    _ans = _exec_str.split('|')[-1].strip()
                                    if _ans:
                                        _msg_fin = '[SUMMARY]:' + _ans
                                # 备用方案：从 review.goal_reason 里提取
                                else:
                                    _review = _last.get('review', {})
                                    _reason = _review.get('goal_reason', '')
                                    import re
                                    match = re.search(r"(?:返回|得到)\s*(.*?)[，。]", _reason)
                                    if match:
                                        _ans = match.group(1).strip()
                                        _msg_fin = '[SUMMARY]:' + _ans
                                    elif _reason:
                                        _msg_fin = '[SUMMARY]:' + _reason[:100] + '...'
                except Exception as _e_hist:
                    print('[supervisor] history 提取异常:', _e_hist)
            try:
                _msg_fin
            except NameError:
                _msg_fin = '[SUMMARY]:OK 执行已结束'
            _im_fin(_conv_id, _msg_fin, sender_agent_id=_sup_id)
            # [A2A 跨端回传] 如果是好友会话，将执行结果投递回发起方
            try:
                import sqlite3, asyncio
                _conn_f = sqlite3.connect('users.db')
                _conn_f.row_factory = sqlite3.Row
                _cur_f = _conn_f.cursor()
                _cur_f.execute("SELECT user_id, target_user_id, is_friend_chat FROM conversations WHERE id=?", (_conv_id,))
                _c_row = _cur_f.fetchone()
                _conn_f.close()
                
                if _c_row and _c_row['is_friend_chat'] == 1 and _c_row['target_user_id']:
                    from ..cross_account_delivery import deliver_to_linked_accounts
                    try:
                        _loop = asyncio.get_running_loop()
                        _loop.create_task(deliver_to_linked_accounts(
                            user_id=_c_row['user_id'],
                            conversation_id=_conv_id,
                            content=_msg_fin,
                            sender_agent_id=_sup_id
                        ))
                    except RuntimeError:
                        asyncio.run(deliver_to_linked_accounts(
                            user_id=_c_row['user_id'],
                            conversation_id=_conv_id,
                            content=_msg_fin,
                            sender_agent_id=_sup_id
                        ))
                    print(f"[A2A 成功] 已将执行结果跨端回传给好友 {_c_row['target_user_id']}")
            except Exception as _e_a2a:
                print(f"[A2A 失败] 结果回传异常: {_e_a2a}")

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
