"""蜂群模式 - 群任务服务"""
import secrets
from datetime import datetime, timedelta
import httpx
from ..db import db_cursor
from .. import config as _cfg


def _now_iso():
    return datetime.utcnow().isoformat()


def _gen_task_id():
    return (_cfg.HIVE_NODE_ID or 'unknown') + ':t-' + secrets.token_hex(8)


def _gen_sub_id():
    return (_cfg.HIVE_NODE_ID or 'unknown') + ':s-' + secrets.token_hex(8)


def _broadcast(endpoint, payload):
    if _cfg.HIVE_MODE == 'off':
        return
    for peer in (_cfg.HIVE_PEERS or []):
        try:
            httpx.post(peer.rstrip('/') + endpoint, json=payload, timeout=3)
        except Exception as e:
            print('[group_task] broadcast failed: ' + str(e))


def _get_global_group_id(group_id):
    with db_cursor() as cur:
        cur.execute('SELECT global_group_id FROM groups WHERE id=?', (group_id,))
        r = cur.fetchone()
        return r['global_group_id'] if r else None


def publish_task(group_id, user_id, title, description, category, reward):
    if reward < 10:
        return False, '质押积分最少 10 分'
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            return False, '你不是群成员'
        cur.execute('SELECT credits FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if not row or (row['credits'] or 0) < reward:
            return False, '个人积分不足'
    gtask_id = _gen_task_id()
    deadline = (datetime.utcnow() + timedelta(hours=48)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits - ? WHERE id=?', (reward, user_id))
        cur.execute('INSERT INTO group_tasks (group_id, global_task_id, title, description, task_category, created_by, reward_credits, status, judging_deadline, origin_node) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (group_id, gtask_id, title, description, category, user_id, reward, 'open', deadline, _cfg.HIVE_NODE_ID))
        task_id = cur.lastrowid
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (group_id, user_id, reward, 'task_escrow', '发布任务质押 task_id=' + str(task_id)))
    gid = _get_global_group_id(group_id)
    if gid:
        _broadcast('/hive/sync/task', {'global_group_id': gid, 'global_task_id': gtask_id, 'title': title, 'description': description, 'task_category': category, 'reward_credits': reward, 'origin_node': _cfg.HIVE_NODE_ID})
    import json as _json
    _card_payload = _json.dumps({'task_id': task_id, 'title': title, 'reward': reward, 'status': 'open'}, ensure_ascii=False)
    _card_msg = '[TASK_CARD]:' + _card_payload
    with db_cursor(commit=True) as _cur_card:
        _cur_card.execute('INSERT INTO group_messages (group_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)', (group_id, user_id, _card_msg, 'task_card'))


    return True, {'task_id': task_id, 'global_task_id': gtask_id}


def list_tasks(group_id, status=None):
    with db_cursor() as cur:
        if status:
            cur.execute('SELECT * FROM group_tasks WHERE group_id=? AND status=? ORDER BY id DESC', (group_id, status))
        else:
            cur.execute('SELECT * FROM group_tasks WHERE group_id=? ORDER BY id DESC LIMIT 50', (group_id,))
        return [dict(r) for r in cur.fetchall()]


def get_task_detail(task_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_tasks WHERE id=?', (task_id,))
        t = cur.fetchone()
        if not t:
            return None
        task = dict(t)
        cur.execute('SELECT s.*, u.username as submitter_name FROM group_task_submissions s LEFT JOIN users u ON s.submitted_by = u.id WHERE s.task_id = ? ORDER BY s.id ASC', (task_id,))
        subs = [dict(r) for r in cur.fetchall()]
        if task['status'] == 'open':
            for s in subs:
                s['submitter_name'] = '匿名'
                s['submitted_by'] = None
        task['submissions'] = subs
        return task


def submit_solution(task_id, user_id, agent_id, content, content_type='text'):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_tasks WHERE id=?', (task_id,))
        t = cur.fetchone()
        if not t:
            return False, '任务不存在'
        if t['status'] != 'open':
            return False, '任务已关闭'
        if t['created_by'] == user_id:
            return False, '不能给自己发布的任务提交方案'
        cur.execute('SELECT COUNT(*) as c FROM group_task_submissions WHERE task_id=? AND submitted_by=?', (task_id, user_id))
        if cur.fetchone()['c'] >= 1:
            return False, '每人只能提交 1 个方案'
    sub_id = _gen_sub_id()
    with db_cursor(commit=True) as cur:
        cur.execute('INSERT INTO group_task_submissions (task_id, global_submission_id, submitted_by, agent_id, content, content_type) VALUES (?, ?, ?, ?, ?, ?)', (task_id, sub_id, user_id, agent_id, content, content_type))
        sid = cur.lastrowid
    gid = _get_global_group_id(t['group_id'])
    if gid:
        _broadcast('/hive/sync/submission', {'global_group_id': gid, 'global_task_id': t['global_task_id'], 'global_submission_id': sub_id, 'content': content, 'content_type': content_type, 'origin_node': _cfg.HIVE_NODE_ID})
    return True, {'submission_id': sid}


def select_winner(task_id, user_id, submission_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_tasks WHERE id=?', (task_id,))
        t = cur.fetchone()
        if not t:
            return False, '任务不存在'
        if t['created_by'] != user_id:
            return False, '只有发布者可以选择'
        if t['status'] != 'open':
            return False, '任务状态不允许'
        cur.execute('SELECT * FROM group_task_submissions WHERE id=? AND task_id=?', (submission_id, task_id))
        sub = cur.fetchone()
        if not sub:
            return False, '提交不存在'
        if sub['submitted_by'] == user_id:
            return False, '不能选自己'
    reward = t['reward_credits']
    winner_gets = round(reward * 0.95, 2)
    pool_gets = round(reward * 0.05, 2)
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (winner_gets, sub['submitted_by']))
        cur.execute('UPDATE groups SET credits = credits + ? WHERE id=?', (pool_gets, t['group_id']))
        cur.execute('UPDATE group_tasks SET status=?, selected_submission_id=? WHERE id=?', ('done', submission_id, task_id))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (t['group_id'], None, pool_gets, 'task_commission', 'task_' + str(task_id) + ' 抽成 5%'))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (t['group_id'], sub['submitted_by'], winner_gets, 'task_payout', 'task_' + str(task_id) + ' 结算 95%'))
    # 知识库回流（直接 SQL，绕过权限校验）
    try:
        import json as _json_k
        with db_cursor(commit=True) as _cur_k:
            _cur_k.execute(
                'INSERT INTO knowledge_docs (scope, group_id, title, content, category, tags, source_type, source_id, contributor_id, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                ('group', t['group_id'], t['title'], sub['content'], 'task_result', '', 'task_result', str(t['id']), sub['submitted_by'], 'group')
            )
        print(f'[task] 方案已回流知识库 task={t["id"]}')
    except Exception as _e:
        print(f'[task] 知识库回流失败: {_e}')
    gid = _get_global_group_id(t['group_id'])
    if gid:
        _broadcast('/hive/sync/task-result', {'global_group_id': gid, 'global_task_id': t['global_task_id'], 'global_submission_id': sub['global_submission_id'], 'origin_node': _cfg.HIVE_NODE_ID})
    return True, {'winner_gets': winner_gets, 'pool_gets': pool_gets}


def reject_all(task_id, user_id, reason):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_tasks WHERE id=?', (task_id,))
        t = cur.fetchone()
        if not t:
            return False, '任务不存在'
        if t['created_by'] != user_id:
            return False, '只有发布者可以拒绝'
        if t['status'] != 'open':
            return False, '任务状态不允许'
    reward = t['reward_credits']
    refund = round(reward * 0.5, 2)
    pool_gets = round(reward * 0.5, 2)
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (refund, user_id))
        cur.execute('UPDATE groups SET credits = credits + ? WHERE id=?', (pool_gets, t['group_id']))
        cur.execute('UPDATE group_tasks SET status=?, reject_reason=? WHERE id=?', ('done', reason, task_id))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (t['group_id'], user_id, refund, 'task_refund', 'task_' + str(task_id) + ' 全部不合格退款 50%'))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (t['group_id'], None, pool_gets, 'task_penalty', 'task_' + str(task_id) + ' 全部不合格罚没 50%'))
    return True, {'refund': refund, 'penalty': pool_gets}


def expire_overdue_tasks():
    now = datetime.utcnow().isoformat()
    expired = []
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_tasks WHERE status=? AND judging_deadline < ?', ('open', now))
        rows = cur.fetchall()
    for t in rows:
        with db_cursor(commit=True) as cur:
            cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (t['reward_credits'], t['created_by']))
            cur.execute('UPDATE group_tasks SET status=? WHERE id=?', ('expired', t['id']))
            cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (t['group_id'], t['created_by'], t['reward_credits'], 'task_expired_refund', 'task_' + str(t['id']) + ' 超时作废全额退回'))
        expired.append(t['id'])
    return expired


def get_group_pool(group_id):
    with db_cursor() as cur:
        cur.execute('SELECT credits, staked_credits FROM groups WHERE id=?', (group_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {'available': r['credits'] or 0, 'staked': r['staked_credits'] or 0}


def repush_pending_tasks(hours=12):
    """重播超过 N 小时未完成的任务卡片"""
    from datetime import datetime, timedelta
    import json as _json
    now = datetime.utcnow()
    threshold = (now - timedelta(hours=hours)).isoformat()
    repushed = []
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM group_tasks WHERE status='open' AND (last_repushed_at IS NULL AND created_at < ? OR last_repushed_at IS NOT NULL AND last_repushed_at < ?)",
            (threshold, threshold)
        )
        rows = cur.fetchall()
    for t in rows:
        try:
            payload = _json.dumps({
                'task_id': t['id'],
                'title': t['title'],
                'reward': t['reward_credits'],
                'status': t['status']
            }, ensure_ascii=False)
            card_msg = '[TASK_CARD]:' + payload
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO group_messages (group_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (t['group_id'], t['created_by'], card_msg, 'task_card')
                )
                cur.execute(
                    "UPDATE group_tasks SET last_repushed_at=?, repush_count=COALESCE(repush_count,0)+1 WHERE id=?",
                    (now.isoformat(), t['id'])
                )
            repushed.append(t['id'])
        except Exception as e:
            print(f'[repush] task {t["id"]} failed: {e}')
    return repushed
