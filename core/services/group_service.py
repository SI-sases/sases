# core/services/group_service.py
from ..db import db_cursor


def create_group(name: str, owner_id: int):
    """创建群聊，返回群 ID。HIVE_MODE 启用时生成 global_group_id 并广播给 peers。"""
    import secrets as _sec
    from .. import config as _cfg
    _global_gid = None
    _origin_node = _cfg.HIVE_NODE_ID or None
    if _cfg.HIVE_MODE != 'off' and _cfg.HIVE_NODE_ID:
        _global_gid = _cfg.HIVE_NODE_ID + ':g-' + _sec.token_hex(6)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO groups (name, owner_id, mode, global_group_id, origin_node) VALUES (?, ?, 'normal', ?, ?)",
            (name, owner_id, _global_gid, _origin_node)
        )
        group_id = cur.lastrowid
        _owner_sases_id = None
        try:
            cur.execute("SELECT sases_id FROM users WHERE id=?", (owner_id,))
            _r = cur.fetchone()
            if _r:
                _owner_sases_id = _r['sases_id']
        except Exception:
            pass
        cur.execute("INSERT INTO group_members (group_id, user_id, role, origin_node, user_sases_id) VALUES (?, ?, 'owner', ?, ?)",
                    (group_id, owner_id, _origin_node, _owner_sases_id))
    if _global_gid and _cfg.HIVE_MODE != 'off' and _cfg.HIVE_PEERS:
        try:
            import httpx as _httpx
            _payload = {
                'global_group_id': _global_gid,
                'origin_node': _origin_node,
                'name': name,
                'owner_sases_id': _owner_sases_id,
                'mode': 'normal',
            }
            for _peer in _cfg.HIVE_PEERS:
                try:
                    _httpx.post(_peer.rstrip('/') + '/hive/sync/group', json=_payload, timeout=3)
                except Exception as _pe:
                    print('[group] hive broadcast failed: ' + str(_pe))
        except Exception as _e:
            print('[group] hive broadcast error: ' + str(_e))
    return group_id


def invite_to_group(group_id: int, inviter_id: int, invitee: str):
    """邀请用户或智能体加入群聊。invitee 可以是用户名、SASES ID、智能体 ID 或智能体名称。"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, inviter_id))
        if not cur.fetchone():
            return False, "邀请者不是群成员"

        from .. import config as _cfg_i
        _origin = _cfg_i.HIVE_NODE_ID if _cfg_i.HIVE_MODE != 'off' else None

        cur.execute("SELECT id FROM users WHERE username=? OR sases_id=?", (invitee, invitee))
        user = cur.fetchone()
        if user:
            target_user_id = user["id"]
            _target_sases = None
            cur.execute("SELECT sases_id FROM users WHERE id=?", (target_user_id,))
            _ru = cur.fetchone()
            if _ru:
                _target_sases = _ru['sases_id']
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, target_user_id))
            if cur.fetchone():
                return False, "用户已在群中"
            # 邀请确认：若开启且邀请者非管理员 → 写入待批准队列
            _f = _get_features_safe(group_id)
            if _f.get('invite_confirm') and not _is_owner_or_admin(group_id, inviter_id):
                with db_cursor(commit=True) as _curp:
                    _curp.execute("INSERT INTO group_invite_pending (group_id, inviter_id, invitee) VALUES (?, ?, ?)", (group_id, inviter_id, invitee))
                return True, "已发送邀请，等待群主批准"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, user_id, origin_node, user_sases_id) VALUES (?, ?, ?, ?)", (group_id, target_user_id, _origin, _target_sases))
                cur2.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
                _gg = cur2.fetchone()
            if _gg and _gg['global_group_id']:
                _broadcast_member(_gg['global_group_id'], _target_sases, 'member')
            return True, "邀请用户成功"

        cur.execute("""
            SELECT id FROM model_configs
            WHERE (id=? OR name=?) AND user_id=?
        """, (invitee, invitee, inviter_id))
        agent = cur.fetchone()
        if agent:
            agent_id = agent["id"]
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, agent_id))
            if cur.fetchone():
                return False, "智能体已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, user_id, agent_id, role, origin_node) VALUES (?, ?, ?, 'agent', ?)", (group_id, inviter_id, agent_id, _origin))
            return True, "邀请智能体成功"

        return False, "找不到该用户或智能体，或智能体不属于你"


def _broadcast_member_remove(global_group_id, member_sases_id):
    from .. import config as _cfg
    if _cfg.HIVE_MODE == 'off' or not _cfg.HIVE_PEERS or not global_group_id:
        return
    try:
        import httpx as _httpx
        _payload = {'global_group_id': global_group_id, 'member_sases_id': member_sases_id, 'origin_node': _cfg.HIVE_NODE_ID}
        for _peer in _cfg.HIVE_PEERS:
            try:
                _httpx.post(_peer.rstrip('/') + '/hive/sync/member-remove', json=_payload, timeout=3)
            except Exception as _pe:
                print('[group] member-remove broadcast failed: ' + str(_pe))
    except Exception as _e:
        print('[group] member-remove broadcast error: ' + str(_e))


def _broadcast_member(global_group_id, member_sases_id, role='member'):
    from .. import config as _cfg
    if _cfg.HIVE_MODE == 'off' or not _cfg.HIVE_PEERS or not global_group_id:
        return
    try:
        import httpx as _httpx
        _payload = {'global_group_id': global_group_id, 'member_sases_id': member_sases_id, 'role': role, 'origin_node': _cfg.HIVE_NODE_ID}
        for _peer in _cfg.HIVE_PEERS:
            try:
                _httpx.post(_peer.rstrip('/') + '/hive/sync/member', json=_payload, timeout=3)
            except Exception as _pe:
                print('[group] member broadcast failed: ' + str(_pe))
    except Exception as _e:
        print('[group] member broadcast error: ' + str(_e))


def list_user_groups(user_id: int):
    """获取用户所在的群聊列表"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT g.id, g.name, g.owner_id, g.mode, COALESCE(g.is_pinned, 0) as is_pinned,
                   (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) as member_count,
                   (SELECT COUNT(*) FROM group_messages gm3
                    WHERE gm3.group_id = g.id
                      AND gm3.created_at > COALESCE(gm2.last_read_at, '1970-01-01')
                      AND (gm3.sender_id IS NULL OR gm3.sender_id != ?)) as unread_count
            FROM groups g
            JOIN group_members gm2 ON g.id = gm2.group_id
            WHERE gm2.user_id = ?
            ORDER BY COALESCE(g.is_pinned, 0) DESC, g.created_at DESC
        """, (user_id, user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def mark_group_read(group_id: int, user_id: int):
    """标记群聊已读（更新 last_read_at）"""
    from datetime import datetime as _dt
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_members SET last_read_at=? WHERE group_id=? AND user_id=?", (_dt.now().isoformat(), group_id, user_id))
        return cur.rowcount > 0



def toggle_group_pin(group_id: int, user_id: int, pinned: bool):
    """置顶/取消置顶群聊（仅检查成员身份）"""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return False
        cur.execute("UPDATE groups SET is_pinned=? WHERE id=?", (1 if pinned else 0, group_id))
        return True



def get_group_info(group_id: int):
    """获取群基本信息，包括模式和 global_group_id"""
    with db_cursor() as cur:
        cur.execute("SELECT id, name, owner_id, mode, global_group_id, origin_node FROM groups WHERE id=?", (group_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def get_group_mode(group_id: int):
    """获取群模式"""
    with db_cursor() as cur:
        cur.execute("SELECT mode FROM groups WHERE id=?", (group_id,))
        row = cur.fetchone()
        return row["mode"] if row else None


def set_group_mode(group_id: int, mode: str, user_id: int = None):
    """设置群模式（仅群主可操作）"""
    if user_id is not None:
        with db_cursor() as cur:
            cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
            group = cur.fetchone()
            if not group:
                return False, "群不存在"
            if group["owner_id"] == user_id:
                pass
            else:
                cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
                m = cur.fetchone()
                if not m or m["role"] != "admin":
                    return False, "只有群主或管理员可以切换模式"

    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET mode=? WHERE id=?", (mode, group_id))
        return True, "切换成功"


def get_group_messages(group_id: int, user_id: int):
    """获取群聊消息（需为群成员）"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute("""
            SELECT m.id, m.content, m.created_at,
                   CASE WHEN m.sender_agent_id IS NOT NULL THEN mc.name
                        ELSE u.username END as sender_name,
                   m.sender_id, m.sender_agent_id
            FROM group_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            LEFT JOIN model_configs mc ON m.sender_agent_id = mc.id
            WHERE m.group_id = ?
            ORDER BY m.created_at ASC
            LIMIT 100
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def send_group_message(group_id: int, sender_id: int, content: str, sender_agent_id: str = None):
    """发送群聊消息，可为用户或智能体。HIVE_MODE 启用时广播给 peers。"""
    import secrets as _sec
    from .. import config as _cfg
    mode = get_group_mode(group_id)

    _global_gid = None
    _global_msg_id = None
    _sender_sases_id = None
    with db_cursor() as _cur_g:
        _cur_g.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _rg = _cur_g.fetchone()
        if _rg:
            _global_gid = _rg['global_group_id']
    if _cfg.HIVE_MODE != 'off' and _global_gid:
        _global_msg_id = (_cfg.HIVE_NODE_ID or 'unknown') + ':m-' + _sec.token_hex(8)

    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            _in_members = cur.fetchone()
            if not _in_members:
                # 回退：检查是否在群资源池（蜂群模式共享）
                cur.execute("SELECT id FROM group_resource_pool WHERE group_id=? AND agent_id=? AND enabled=1", (group_id, sender_agent_id))
                if not cur.fetchone():
                    return False, "智能体不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_id, sender_agent_id, content, global_msg_id, origin_node, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (group_id, sender_id, sender_agent_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None, 'standard', None))
        else:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, sender_id))
            if not cur.fetchone():
                return False, "用户不在群中"
            cur.execute("SELECT sases_id FROM users WHERE id=?", (sender_id,))
            _ru = cur.fetchone()
            if _ru:
                _sender_sases_id = _ru['sases_id']
            cur.execute("INSERT INTO group_messages (group_id, sender_id, content, global_msg_id, origin_node, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?, ?)", (group_id, sender_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None, 'standard', None))

    if _global_msg_id and _global_gid and _cfg.HIVE_PEERS:
        try:
            import httpx as _httpx
            _payload = {
                'global_group_id': _global_gid,
                'global_msg_id': _global_msg_id,
                'sender_sases_id': _sender_sases_id,
                'sender_agent_id': sender_agent_id,
                'content': content,
                'origin_node': _cfg.HIVE_NODE_ID,
            }
            for _peer in _cfg.HIVE_PEERS:
                try:
                    _httpx.post(_peer.rstrip('/') + '/hive/sync/message', json=_payload, timeout=3)
                except Exception as _pe:
                    print('[group] msg broadcast failed: ' + str(_pe))
        except Exception as _e:
            print('[group] msg broadcast error: ' + str(_e))
    return True, "发送成功"


def list_group_members(group_id: int):
    """获取群成员列表，包括用户和智能体"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT gm.user_id, gm.agent_id, gm.role,
                   COALESCE(u.username, mc.name) as display_name,
                   CASE WHEN gm.agent_id IS NOT NULL THEN 'agent' ELSE 'user' END as member_type
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            LEFT JOIN model_configs mc ON gm.agent_id = mc.id
            WHERE gm.group_id = ?
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_group_credits(group_id: int):
    """获取群积分（暂返回0，后续可统计）"""
    return 0.0


def remove_member_from_group(group_id: int, remover_id: int, member_identifier: str):
    """移除群成员（仅群主可操作）"""
    with db_cursor() as cur:
        cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
        group = cur.fetchone()
        if not group or group["owner_id"] != remover_id:
            return False, "只有群主可以移除成员"

        cur.execute("""
            SELECT gm.id, gm.user_id, u.sases_id
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id=?
              AND (CAST(gm.user_id AS TEXT)=?
                   OR gm.agent_id=?
                   OR u.sases_id=?
                   OR gm.user_sases_id=?
                   OR gm.user_id IN (SELECT id FROM users WHERE username=?)
                   OR gm.agent_id IN (SELECT id FROM model_configs WHERE name=?))
        """, (group_id, member_identifier, member_identifier, member_identifier, member_identifier, member_identifier, member_identifier))
        member = cur.fetchone()
        if not member:
            return False, "成员不存在"

        _member_sases = member['sases_id'] if member else None
        with db_cursor(commit=True) as cur2:
            cur2.execute("DELETE FROM group_members WHERE id=?", (member["id"],))
            cur2.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _gg = cur2.fetchone()
        if _member_sases and _gg and _gg['global_group_id']:
            _broadcast_member_remove(_gg['global_group_id'], _member_sases)
        return True, "移除成功"


def leave_group(group_id: int, user_id: int):
    """成员退出群聊"""
    _sases = None
    _gg = None
    with db_cursor() as cur:
        cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
        _r = cur.fetchone()
        if _r:
            _sases = _r['sases_id']
        cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _g = cur.fetchone()
        if _g:
            _gg = _g['global_group_id']
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    if _sases and _gg:
        _broadcast_member_remove(_gg, _sases)
    return {"ok": True}


def dismiss_group(group_id: int):
    # 校验群主权限由调用方传入的 user_id 完成；此处统一提交事务

    """群主解散群聊"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM groups WHERE id=?", (group_id,))
        return {"ok": True}


# ========== 蜂群模式：质押 ==========




def stake_credits(group_id, user_id, amount):
    """用户质押积分到群"""
    if amount < 10:
        return False, '最少质押 10 积分'
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            return False, '你不是群成员'
        cur.execute('SELECT credits FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if not row or (row['credits'] or 0) < amount:
            return False, '个人积分不足'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits - ? WHERE id=?', (amount, user_id))
        cur.execute('UPDATE groups SET staked_credits = COALESCE(staked_credits, 0) + ? WHERE id=?', (amount, group_id))
        cur.execute('INSERT INTO group_stakes (group_id, user_id, amount, status) VALUES (?, ?, ?, ?)', (group_id, user_id, amount, 'active'))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (group_id, user_id, amount, 'stake', '质押积分'))
    return True, {'staked': amount}


def withdraw_stake(group_id, user_id):
    """提取质押（需超过 30 天）"""
    from datetime import datetime
    now = datetime.utcnow()
    with db_cursor() as cur:
        cur.execute("SELECT id, amount, created_at FROM group_stakes WHERE group_id=? AND user_id=? AND status='active'", (group_id, user_id))
        rows = cur.fetchall()
    if not rows:
        return False, '没有活跃质押'
    total = 0
    for r in rows:
        try:
            created = datetime.fromisoformat(r['created_at'])
        except Exception:
            created = now
        if (now - created).days >= 30:
            total += r['amount']
    if total <= 0:
        return False, '质押未满 30 天'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (total, user_id))
        cur.execute('UPDATE groups SET staked_credits = MAX(0, COALESCE(staked_credits, 0) - ?) WHERE id=?', (total, group_id))
        cur.execute("UPDATE group_stakes SET status='withdrawn', withdrawn_at=? WHERE group_id=? AND user_id=? AND status='active'", (now.isoformat(), group_id, user_id))
        cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)', (group_id, user_id, -total, 'unstake', '提取质押'))
    return True, {'withdrawn': total}


def list_active_stakes(group_id):
    with db_cursor() as cur:
        cur.execute("SELECT gs.*, u.username FROM group_stakes gs LEFT JOIN users u ON gs.user_id = u.id WHERE gs.group_id=? AND gs.status='active' ORDER BY gs.id DESC", (group_id,))
        return [dict(r) for r in cur.fetchall()]


# ========== 蜂群模式：群红包 ==========

def configure_red_packet(group_id, user_id, hour, audience):
    """群主配置红包参数"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        row = cur.fetchone()
        if not row or row['owner_id'] != user_id:
            return False, '只有群主可以配置'
        if hour < 0 or hour > 23:
            return False, '小时必须在 0-23 之间'
        if audience not in ('all', 'stakers'):
            return False, 'audience 只能是 all 或 stakers'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET red_packet_hour=?, red_packet_audience=? WHERE id=?', (hour, audience, group_id))
    return True, {'hour': hour, 'audience': audience}


def distribute_group_red_packet(group_id, user_id, total_amount=None, total_count=None):
    """群主发放群福利手气红包（从群池扣分）"""
    from . import group_red_packet_service
    with db_cursor() as cur:
        cur.execute('SELECT owner_id, credits, staked_credits FROM groups WHERE id=?', (group_id,))
        row = cur.fetchone()
        if not row or row['owner_id'] != user_id:
            return False, '只有群主可以发群福利'
        pool = row['credits'] or 0
        total_pool = pool + (row['staked_credits'] or 0)
        if total_pool < 1000:
            return False, '群积分总值不足 1000'
        if pool <= 0:
            return False, '群池可用余额为空'
    if total_amount is None:
        total_amount = round(pool * 0.1, 2)
        if total_amount < 1:
            total_amount = 1.0
    if total_count is None:
        total_count = 5
    if total_amount > pool:
        total_amount = pool
    ok, res = group_red_packet_service.create_packet(
        group_id, user_id, total_amount, int(total_count),
        message='群福利红包', source_type='group_pool', packet_type='lucky'
    )
    if not ok:
        return False, res
    # 记录发放日期，防止重复
    from datetime import datetime
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET last_red_packet_date=? WHERE id=?', (today, group_id))
    return True, res

def get_group_pool_detail(group_id):
    """查群池详情"""
    with db_cursor() as cur:
        cur.execute('SELECT credits, staked_credits, red_packet_hour, red_packet_audience FROM groups WHERE id=?', (group_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            'available': r['credits'] or 0,
            'staked': r['staked_credits'] or 0,
            'total': (r['credits'] or 0) + (r['staked_credits'] or 0),
            'red_packet_hour': r['red_packet_hour'],
            'red_packet_audience': r['red_packet_audience']
        }


# ========== 群管理员管理 ==========

def _is_owner(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        return g and g['owner_id'] == user_id


def _is_owner_or_admin(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False
        if g['owner_id'] == user_id:
            return True
        cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        m = cur.fetchone()
        return bool(m and m['role'] == 'admin')


def set_member_role(group_id, operator_id, target_username_or_id, new_role):
    """群主/管理员设置成员角色（admin/member），只有群主可以设 admin"""
    if not _is_owner_or_admin(group_id, operator_id):
        return False, '只有群主或管理员可以操作'
    if new_role not in ('admin', 'member'):
        return False, '角色只能是 admin 或 member'
    # 只有群主可以任命管理员
    if new_role == 'admin' and not _is_owner(group_id, operator_id):
        return False, '只有群主可以任命管理员'
    with db_cursor() as cur:
        # 解析目标用户
        target_uid = None
        try:
            target_uid = int(target_username_or_id)
        except (ValueError, TypeError):
            pass
        if target_uid is None:
            cur.execute('SELECT id FROM users WHERE username=? OR sases_id=?', (target_username_or_id, target_username_or_id))
            u = cur.fetchone()
            if not u:
                return False, '用户不存在'
            target_uid = u['id']
        # 确认目标在群里
        cur.execute('SELECT role FROM group_members WHERE group_id=? AND user_id=?', (group_id, target_uid))
        m = cur.fetchone()
        if not m:
            return False, '该用户不在群里'
        if m['role'] == 'owner':
            return False, '不能修改群主角色'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET role=? WHERE group_id=? AND user_id=?', (new_role, group_id, target_uid))
    return True, {'user_id': target_uid, 'role': new_role}


def list_admins(group_id):
    """列出群主和管理员"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return []
        owner_id = g['owner_id']
        cur.execute('SELECT id, username FROM users WHERE id=?', (owner_id,))
        owner = cur.fetchone()
        result = []
        if owner:
            result.append({'user_id': owner['id'], 'username': owner['username'], 'role': 'owner'})
        cur.execute("SELECT m.user_id, u.username FROM group_members m LEFT JOIN users u ON m.user_id=u.id WHERE m.group_id=? AND m.role='admin'", (group_id,))
        for r in cur.fetchall():
            result.append({'user_id': r['user_id'], 'username': r['username'], 'role': 'admin'})
        return result


# ========== @智能体触发 AI 回复 ==========

def _find_agent_id_by_name(group_id, name):
    """按名字找群成员里的智能体 ID（支持带或不带 @）"""
    if not name:
        return None
    name = name.strip().lstrip('@').strip()
    if not name:
        return None
    with db_cursor() as cur:
        # 1. 优先查群成员绑定的智能体
        cur.execute(
            "SELECT mc.id FROM group_members gm LEFT JOIN model_configs mc ON gm.agent_id = mc.id WHERE gm.group_id=? AND mc.name=? LIMIT 1",
            (group_id, name)
        )
        r = cur.fetchone()
        if r and r['id']:
            return r['id']
        # 2. 查群资源池里的模型配置
        cur.execute(
            "SELECT mc.id FROM group_resource_pool p LEFT JOIN model_configs mc ON p.agent_id = mc.id WHERE p.group_id=? AND p.enabled=1 AND mc.name=? LIMIT 1",
            (group_id, name)
        )
        r = cur.fetchone()
        if r and r['id']:
            return r['id']
    return None


def _is_human_in_group(group_id, name):
    """检查 name 是否是真人群成员"""
    if not name:
        return False
    name = name.strip().lstrip('@').strip()
    with db_cursor() as cur:
        cur.execute(
            "SELECT u.id FROM group_members gm LEFT JOIN users u ON gm.user_id = u.id WHERE gm.group_id=? AND u.username=? LIMIT 1",
            (group_id, name)
        )
        return cur.fetchone() is not None


def parse_at_prefix(content):
    """解析 @名字 前缀，返回 (agent_name, rest_question) 或 (None, content)"""
    if not content or not content.startswith('@'):
        return None, content
    # @名字 后面必须是空格或字符串结束
    parts = content[1:].split(' ', 1)
    if not parts or not parts[0]:
        return None, content
    agent_name = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ''
    return agent_name, rest


def insert_agent_message(group_id, agent_id, content, trigger_user_id=0):
    """把智能体的回复插入群消息表"""
    import secrets as _sec
    from .. import config as _cfg
    _gmid = None
    with db_cursor() as _cur:
        _cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _r = _cur.fetchone()
        if _r and _r['global_group_id']:
            _gmid = (_cfg.HIVE_NODE_ID or 'unknown') + ':m-' + _sec.token_hex(8)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO group_messages (group_id, sender_id, sender_agent_id, content, global_msg_id, origin_node, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (group_id, trigger_user_id, agent_id, content, _gmid, _cfg.HIVE_NODE_ID if _gmid else None, 'standard', None)
        )
        msg_id = cur.lastrowid
    return msg_id


# ========== 群公告 ==========

def get_announcement(group_id):
    """读取群公告"""
    with db_cursor() as cur:
        cur.execute("SELECT announcement FROM groups WHERE id=?", (group_id,))
        r = cur.fetchone()
        return r['announcement'] if r and r['announcement'] else ''


def set_announcement(group_id, user_id, content):
    """设置群公告（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以编辑群公告'
    if content and len(content) > 2000:
        return False, '群公告不能超过 2000 字'
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET announcement=? WHERE id=?", (content or '', group_id))
    return True, {'announcement': content or ''}


def transfer_owner(group_id, current_owner_id, target_username_or_id):
    """群主转让：原群主 → admin，新群主 → owner"""
    if not _is_owner(group_id, current_owner_id):
        return False, '只有群主可以转让管理权'
    # 解析目标用户：先按 username/sases_id 查，再尝试 ID
    target_uid = None
    with db_cursor() as cur:
        cur.execute('SELECT id FROM users WHERE username=? OR sases_id=?', (target_username_or_id, target_username_or_id))
        u = cur.fetchone()
        if u:
            target_uid = u['id']
        else:
            try:
                _try_id = int(target_username_or_id)
                cur.execute('SELECT id FROM users WHERE id=?', (_try_id,))
                u2 = cur.fetchone()
                if u2:
                    target_uid = u2['id']
            except (ValueError, TypeError):
                pass
        if target_uid is None:
            return False, '用户不存在'
    with db_cursor() as cur:
        if target_uid == current_owner_id:
            return False, '不能转让给自己'
        cur.execute('SELECT role FROM group_members WHERE group_id=? AND user_id=?', (group_id, target_uid))
        m = cur.fetchone()
        if not m:
            return False, '该用户不在群里'
    with db_cursor(commit=True) as cur:
        # 更新 groups.owner_id
        cur.execute('UPDATE groups SET owner_id=? WHERE id=?', (target_uid, group_id))
        # 新群主：role=owner
        cur.execute("UPDATE group_members SET role='owner' WHERE group_id=? AND user_id=?", (group_id, target_uid))
        # 原群主：role=admin
        cur.execute("UPDATE group_members SET role='admin' WHERE group_id=? AND user_id=?", (group_id, current_owner_id))
    return True, {'new_owner_id': target_uid}


# ========== 群聊邀请确认 ==========

def _get_features_safe(group_id):
    with db_cursor() as cur:
        cur.execute("SELECT features FROM groups WHERE id=?", (group_id,))
        r = cur.fetchone()
        if not r:
            return {}
        try:
            import json as _j
            return _j.loads(r['features'] or '{}')
        except Exception:
            return {}


def _set_features_safe(group_id, f):
    import json as _j
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET features=? WHERE id=?", (_j.dumps(f, ensure_ascii=False), group_id))


def get_invite_confirm(group_id):
    f = _get_features_safe(group_id)
    return bool(f.get('invite_confirm'))


def set_invite_confirm(group_id, user_id, enabled):
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以设置'
    f = _get_features_safe(group_id)
    f['invite_confirm'] = bool(enabled)
    _set_features_safe(group_id, f)
    return True, {'invite_confirm': f['invite_confirm']}


def list_pending_invites(group_id, user_id):
    """列出待批准邀请（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return None
    with db_cursor() as cur:
        cur.execute("SELECT id, inviter_id, invitee, created_at FROM group_invite_pending WHERE group_id=? AND status='pending' ORDER BY id DESC", (group_id,))
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            cur.execute("SELECT username FROM users WHERE id=?", (d['inviter_id'],))
            u = cur.fetchone()
            d['inviter_name'] = u['username'] if u else '?'
            rows.append(d)
        return rows


def approve_invite(group_id, user_id, pending_id):
    """批准邀请"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以操作'
    with db_cursor() as cur:
        cur.execute("SELECT invitee FROM group_invite_pending WHERE id=? AND group_id=? AND status='pending'", (pending_id, group_id))
        r = cur.fetchone()
        if not r:
            return False, '待批准记录不存在'
        invitee = r['invitee']
    # 调用原 invite_to_group（此时 current user 是管理员，直接进群）
    ok, msg = invite_to_group(group_id, user_id, invitee)
    if not ok:
        return False, msg
    from datetime import datetime
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_invite_pending SET status='approved', resolved_at=?, resolved_by=? WHERE id=?", (datetime.utcnow().isoformat(), user_id, pending_id))
    return True, {'approved': pending_id}


def reject_invite(group_id, user_id, pending_id):
    """拒绝邀请"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以操作'
    from datetime import datetime
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_invite_pending SET status='rejected', resolved_at=?, resolved_by=? WHERE id=? AND group_id=? AND status='pending'", (datetime.utcnow().isoformat(), user_id, pending_id, group_id))
        if cur.rowcount == 0:
            return False, '待批准记录不存在'
    return True, {'rejected': pending_id}


def list_group_files(group_id, user_id, limit=100):
    """列出群里所有共享文件"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute("""
            SELECT m.id, m.content, m.created_at, m.sender_id, m.sender_agent_id,
                   u.username as sender_name
            FROM group_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            WHERE m.group_id = ? AND m.content LIKE '[FILE]:%'
            ORDER BY m.id DESC LIMIT ?
        """, (group_id, limit))
        rows = cur.fetchall()
    files = []
    for r in rows:
        content = r['content'] or ''
        body = content[len('[FILE]:'):]
        parts = body.split('|')
        if len(parts) < 3:
            continue
        files.append({
            'msg_id': r['id'],
            'url': parts[0],
            'name': parts[1],
            'size': parts[2],
            'sender_name': r['sender_name'] or '群友',
            'created_at': r['created_at']
        })
    return files


# ========== 群名称/昵称/免打扰 ==========

def update_group_name(group_id, user_id, new_name):
    """改群名（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以改群名'
    if not new_name or not new_name.strip():
        return False, '群名不能为空'
    if len(new_name) > 50:
        return False, '群名不能超过 50 字'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET name=? WHERE id=?', (new_name.strip(), group_id))
    return True, {'name': new_name.strip()}


def set_my_nickname(group_id, user_id, nickname):
    """设置自己在群里的昵称"""
    if len(nickname or '') > 20:
        return False, '昵称不能超过 20 字'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET nickname=? WHERE group_id=? AND user_id=?', (nickname or '', group_id, user_id))
    return True, {'nickname': nickname or ''}


def toggle_mute(group_id, user_id, muted):
    """消息免打扰"""
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET is_muted=? WHERE group_id=? AND user_id=?', (1 if muted else 0, group_id, user_id))
    return True, {'is_muted': bool(muted)}
