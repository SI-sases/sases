"""蜂群模式 - 每日空投服务"""
from datetime import datetime, timedelta
from ..db import db_cursor


DAILY_POOL = 10000.0
TOP_N_GUARANTEE = 10
TOP_N_AMOUNT = 500.0
SINGLE_GROUP_CAP = 3000.0
MIN_ACTIVITY = 10.0
MIN_TOTAL_CREDITS = 10.0


def _calc_activity(group_id, date_str):
    """计算某群某日的活跃度"""
    start = date_str + ' 00:00:00'
    end = date_str + ' 23:59:59'
    with db_cursor() as cur:
        cur.execute(
            'SELECT COUNT(DISTINCT created_by) as c FROM group_tasks WHERE group_id=? AND created_at BETWEEN ? AND ?',
            (group_id, start, end)
        )
        tasks = cur.fetchone()['c'] or 0
        cur.execute(
            'SELECT COUNT(DISTINCT submitted_by) as c FROM group_task_submissions s JOIN group_tasks t ON s.task_id=t.id WHERE t.group_id=? AND s.created_at BETWEEN ? AND ?',
            (group_id, start, end)
        )
        subs = cur.fetchone()['c'] or 0
        cur.execute(
            'SELECT COUNT(DISTINCT user_id) as c FROM group_stakes WHERE group_id=? AND created_at <= ? AND (status=? OR withdrawn_at IS NULL OR withdrawn_at > ?)',
            (group_id, end, 'active', start)
        )
        stakers = cur.fetchone()['c'] or 0
    return tasks * 10 + subs * 5 + stakers * 3


def _get_eligible_groups(date_str):
    """筛选有资格参与空投的群"""
    with db_cursor() as cur:
        cur.execute('SELECT id, credits, COALESCE(staked_credits,0) as staked, COALESCE(airdrop_enabled,1) as enabled, airdrop_paused_until FROM groups')
        groups = cur.fetchall()
    now = datetime.utcnow()
    eligible = []
    for g in groups:
        if not g['enabled']:
            continue
        if g['airdrop_paused_until']:
            try:
                if datetime.fromisoformat(g['airdrop_paused_until']) > now:
                    continue
            except Exception:
                pass
        total = (g['credits'] or 0) + (g['staked'] or 0)
        if total < MIN_TOTAL_CREDITS:
            continue
        # 质押人数检查已移除
        activity = _calc_activity(g['id'], date_str)
        eligible.append({'group_id': g['id'], 'activity': activity})
    return eligible


def run_daily_airdrop(date_str=None):
    """执行每日空投"""
    if not date_str:
        date_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    with db_cursor() as cur:
        cur.execute('SELECT COUNT(*) as c FROM group_airdrop_log WHERE airdrop_date=?', (date_str,))
        if (cur.fetchone()['c'] or 0) > 0:
            return {'skipped': True, 'reason': 'already done', 'date': date_str}
    eligible = _get_eligible_groups(date_str)
    if not eligible:
        return {'skipped': True, 'reason': 'no eligible groups', 'date': date_str}
    eligible.sort(key=lambda x: x['activity'], reverse=True)
    remaining = DAILY_POOL
    top_n = eligible[:TOP_N_GUARANTEE]
    for g in top_n:
        g['amount'] = TOP_N_AMOUNT
        remaining -= TOP_N_AMOUNT
    others = eligible[TOP_N_GUARANTEE:]
    total_activity = sum(g['activity'] for g in others)
    if total_activity > 0 and remaining > 0:
        for g in others:
            g['amount'] = round(remaining * g['activity'] / total_activity, 2)
    else:
        for g in others:
            g['amount'] = 0
    for g in eligible:
        if g.get('amount', 0) > SINGLE_GROUP_CAP:
            g['amount'] = SINGLE_GROUP_CAP
    total_distributed = 0
    with db_cursor(commit=True) as cur:
        for idx, g in enumerate(eligible, 1):
            amt = round(g.get('amount', 0), 2)
            if amt <= 0:
                continue
            cur.execute('UPDATE groups SET credits = COALESCE(credits,0) + ? WHERE id=?', (amt, g['group_id']))
            cur.execute('INSERT INTO group_airdrop_log (group_id, airdrop_date, activity_score, rank, amount) VALUES (?, ?, ?, ?, ?)', (g['group_id'], date_str, g['activity'], idx, amt))
            cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (g['group_id'], None, amt, 'airdrop', '每日空投 ' + date_str + ' rank=' + str(idx)))
            total_distributed += amt
    return {'date': date_str, 'groups': len(eligible), 'distributed': round(total_distributed, 2)}


def get_airdrop_history(group_id, limit=30):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_airdrop_log WHERE group_id=? ORDER BY id DESC LIMIT ?', (group_id, limit))
        return [dict(r) for r in cur.fetchall()]
