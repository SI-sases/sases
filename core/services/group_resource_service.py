"""蜂群模式 - 群资源池服务"""
import json
from datetime import datetime
from ..db import db_cursor


def _get_features(group_id):
    with db_cursor() as cur:
        cur.execute('SELECT features FROM groups WHERE id=?', (group_id,))
        r = cur.fetchone()
        if not r:
            return {}
        try:
            return json.loads(r['features'] or '{}')
        except Exception:
            return {}


def _set_features(group_id, features):
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET features=? WHERE id=?', (json.dumps(features, ensure_ascii=False), group_id))


def _check_owner(group_id, user_id):
    """检查是否是群主或管理员"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False
        if g['owner_id'] == user_id:
            return True
        cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        m = cur.fetchone()
        if m and m['role'] == 'admin':
            return True
    return False


# ========== 蜂群模式开关 ==========

def is_swarm_enabled(group_id):
    f = _get_features(group_id)
    return bool(f.get('swarm_enabled'))


def toggle_swarm(group_id, user_id, enabled):
    if not _check_owner(group_id, user_id):
        return False, '只有群主或管理员可以开关蜂群模式'
    f = _get_features(group_id)
    f['swarm_enabled'] = bool(enabled)
    _set_features(group_id, f)
    return True, {'swarm_enabled': f['swarm_enabled']}


# ========== 资源池绑定 ==========

def bind_agent_model(group_id, user_id, agent_id, model_id, daily_limit=100):
    """群主绑定智能体到模型"""
    if not _check_owner(group_id, user_id):
        return False, '只有群主或管理员可以配置'
    if not agent_id:
        return False, '缺少智能体 ID'
    with db_cursor(commit=True) as cur:
        cur.execute(
            'INSERT INTO group_resource_pool (group_id, agent_id, model_id, daily_limit, enabled) VALUES (?, ?, ?, ?, 1) ON CONFLICT(group_id, agent_id) DO UPDATE SET model_id=excluded.model_id, daily_limit=excluded.daily_limit, enabled=1',
            (group_id, agent_id, model_id, daily_limit)
        )
    return True, {'agent_id': agent_id, 'model_id': model_id, 'daily_limit': daily_limit}


def unbind_agent(group_id, user_id, agent_id):
    if not _check_owner(group_id, user_id):
        return False, '只有群主或管理员可以配置'
    with db_cursor(commit=True) as cur:
        cur.execute('DELETE FROM group_resource_pool WHERE group_id=? AND agent_id=?', (group_id, agent_id))
        return True, {'unbound': agent_id}


def list_pool(group_id, user_id):
    """列出群资源池（群主/管理员可看全部，员工看可用）"""
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute(
            'SELECT p.id, p.agent_id, p.model_id, p.daily_limit, p.enabled, p.created_at, m.name as model_name, m.provider FROM group_resource_pool p LEFT JOIN model_configs m ON p.model_id = m.id WHERE p.group_id=? ORDER BY p.id DESC',
            (group_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_agent_binding(group_id, agent_id):
    """查某智能体绑定的资源"""
    with db_cursor() as cur:
        cur.execute(
            'SELECT p.*, m.name as model_name, m.provider, m.model_type, m.node_url, m.model_name as local_model_name, m.api_key_encrypted FROM group_resource_pool p LEFT JOIN model_configs m ON p.model_id = m.id WHERE p.group_id=? AND p.agent_id=? AND p.enabled=1',
            (group_id, agent_id)
        )
        r = cur.fetchone()
        return dict(r) if r else None


# ========== 配额与使用 ==========

def check_quota(group_id, user_id, agent_id):
    """检查用户今日配额"""
    binding = get_agent_binding(group_id, agent_id)
    if not binding:
        return False, '智能体未绑定资源'
    limit = int(binding.get('daily_limit') or 100)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as c FROM group_resource_usage WHERE group_id=? AND user_id=? AND agent_id=? AND created_at LIKE ?",
            (group_id, user_id, agent_id, today + '%')
        )
        used = cur.fetchone()['c'] or 0
    if used >= limit:
        return False, f'今日配额已用完（{used}/{limit}）'
    return True, {'used': used, 'limit': limit, 'remaining': limit - used}


def record_usage(group_id, user_id, agent_id, model_id=None, tokens_used=0):
    """记录一次资源使用"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            'INSERT INTO group_resource_usage (group_id, user_id, agent_id, model_id, tokens_used) VALUES (?, ?, ?, ?, ?)',
            (group_id, user_id, agent_id, model_id, tokens_used)
        )
    return True


def get_usage_stats(group_id, user_id, days=7):
    """使用统计（群主/管理员可见）"""
    if not _check_owner(group_id, user_id):
        return None
    with db_cursor() as cur:
        # 今日总量
        today = datetime.utcnow().strftime('%Y-%m-%d')
        cur.execute(
            "SELECT COUNT(*) as calls, COALESCE(SUM(tokens_used), 0) as tokens FROM group_resource_usage WHERE group_id=? AND created_at LIKE ?",
            (group_id, today + '%')
        )
        today_stats = dict(cur.fetchone())

        # 今日 Top 10 用户
        cur.execute(
            "SELECT u.id, u.username, COUNT(*) as calls FROM group_resource_usage r LEFT JOIN users u ON r.user_id = u.id WHERE r.group_id=? AND r.created_at LIKE ? GROUP BY r.user_id ORDER BY calls DESC LIMIT 10",
            (group_id, today + '%')
        )
        top_users = [dict(r) for r in cur.fetchall()]

        # 近 N 天趋势
        cur.execute(
            "SELECT substr(created_at, 1, 10) as day, COUNT(*) as calls FROM group_resource_usage WHERE group_id=? GROUP BY day ORDER BY day DESC LIMIT ?",
            (group_id, days)
        )
        trend = [dict(r) for r in cur.fetchall()]

    return {
        'today': today_stats,
        'top_users': top_users,
        'trend': trend
    }

async def call_agent_with_group_resource(group_id, user_id, agent_id, question):
    """群共享调用：检查配额 → 调模型 → 记使用"""
    from . import model_service
    # 检查配额
    ok, quota = check_quota(group_id, user_id, agent_id)
    if not ok:
        return False, quota
    # 查智能体配置（可能在群主名下，不在员工名下）
    with db_cursor() as cur:
        cur.execute("SELECT * FROM model_configs WHERE id=?", (agent_id,))
        row = cur.fetchone()
    if not row:
        return False, '智能体配置不存在'
    model_config = dict(row)
    # 调模型
    try:
        from .message.model_call import call_model_with_config
        reply = await call_model_with_config(model_config, question)
    except Exception as e:
        return False, f'模型调用失败：{e}'
    # 记使用
    record_usage(group_id, user_id, agent_id, agent_id)
    return True, reply
