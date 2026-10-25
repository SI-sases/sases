"""群红包服务 - 抢红包模式"""
import random
import json
from datetime import datetime, timedelta
from ..db import db_cursor


def _now():
    return datetime.utcnow()


def _gen_notice(packet, action='created'):
    payload = {
        'packet_id': packet['id'],
        'sender_id': packet['sender_id'],
        'total_amount': packet['total_amount'],
        'total_count': packet['total_count'],
        'message': packet.get('message') or '',
        'source_type': packet.get('source_type', 'user'),
        'packet_type': packet.get('packet_type', 'lucky')
    }
    return '[RED_PACKET]:' + json.dumps(payload, ensure_ascii=False)


def create_packet(group_id, user_id, total_amount, total_count, message='', source_type='user', packet_type='lucky'):
    """创建群红包"""
    try:
        total_amount = float(total_amount)
        total_count = int(total_count)
    except (TypeError, ValueError):
        return False, '参数格式错误'
    if total_amount < 1:
        return False, '红包总金额最少 1'
    if total_count < 1:
        return False, '红包个数最少 1'
    if total_amount < total_count * 0.01:
        return False, '金额不足以分配到每份'
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            return False, '你不是群成员'
        if source_type == 'user':
            cur.execute('SELECT credits FROM users WHERE id=?', (user_id,))
            row = cur.fetchone()
            if not row or (row['credits'] or 0) < total_amount:
                return False, '个人积分不足'
        elif source_type == 'group_pool':
            cur.execute('SELECT owner_id, credits FROM groups WHERE id=?', (group_id,))
            row = cur.fetchone()
            if not row or row['owner_id'] != user_id:
                return False, '只有群主可以发群福利'
            if (row['credits'] or 0) < total_amount:
                return False, '群池可用余额不足'
    expires = (_now() + timedelta(hours=24)).isoformat()
    with db_cursor(commit=True) as cur:
        if source_type == 'user':
            cur.execute('UPDATE users SET credits = credits - ? WHERE id=?', (total_amount, user_id))
        elif source_type == 'group_pool':
            cur.execute('UPDATE groups SET credits = credits - ? WHERE id=?', (total_amount, group_id))
        cur.execute(
            'INSERT INTO group_red_packets (group_id, sender_id, source_type, total_amount, total_count, remaining_amount, message, status, expires_at, packet_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (group_id, user_id, source_type, total_amount, total_count, total_amount, message, 'active', expires, packet_type)
        )
        packet_id = cur.lastrowid
    packet = {'id': packet_id, 'sender_id': user_id, 'total_amount': total_amount,
              'total_count': total_count, 'message': message, 'source_type': source_type, 'packet_type': packet_type}
    with db_cursor(commit=True) as cur:
        notice = _gen_notice(packet)
        cur.execute(
            'INSERT INTO group_messages (group_id, sender_id, content, message_type, related_id) VALUES (?, ?, ?, ?, ?)',
            (group_id, user_id, notice, 'red_packet', packet_id)
        )
    return True, {'packet_id': packet_id}


def claim_packet(packet_id, user_id):
    """抢红包"""
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_red_packets WHERE id=?', (packet_id,))
        p = cur.fetchone()
        if not p:
            return False, '红包不存在'
        if p['status'] != 'active':
            return False, '红包已抢完或已过期'
        exp = p['expires_at']
        if exp:
            try:
                if datetime.fromisoformat(exp) < _now():
                    return False, '红包已过期'
            except Exception:
                pass
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (p['group_id'], user_id))
        if not cur.fetchone():
            return False, '你不是群成员'
        cur.execute('SELECT id FROM group_red_packet_claims WHERE packet_id=? AND user_id=?', (packet_id, user_id))
        if cur.fetchone():
            return False, '你已经抢过了'
    remaining_amount = float(p['remaining_amount'])
    remaining_count = int(p['total_count']) - int(p['claimed_count'])
    if remaining_count <= 0:
        return False, '红包已抢完'
    _ptype = 'lucky'
    try:
        _ptype = p['packet_type'] or 'lucky'
    except (KeyError, IndexError):
        _ptype = 'lucky'
    if remaining_count == 1:
        amount = round(remaining_amount, 2)
    elif _ptype == 'normal':
        amount = round(float(p['total_amount']) / int(p['total_count']), 2)
        if amount > remaining_amount:
            amount = round(remaining_amount, 2)
    else:
        max_amt = remaining_amount / remaining_count * 2
        amount = round(random.uniform(0.01, max_amt - 0.01), 2)
        if amount < 0.01:
            amount = 0.01
        if amount > remaining_amount - 0.01 * (remaining_count - 1):
            amount = round(remaining_amount - 0.01 * (remaining_count - 1), 2)
    new_remaining = round(remaining_amount - amount, 2)
    new_count = int(p['claimed_count']) + 1
    new_status = 'empty' if new_count >= int(p['total_count']) else 'active'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (amount, user_id))
        cur.execute(
            'UPDATE group_red_packets SET claimed_count=?, remaining_amount=?, status=? WHERE id=?',
            (new_count, new_remaining, new_status, packet_id)
        )
        cur.execute(
            'INSERT INTO group_red_packet_claims (packet_id, user_id, amount) VALUES (?, ?, ?)',
            (packet_id, user_id, amount)
        )
    return True, {'amount': amount, 'remaining_count': int(p['total_count']) - new_count}


def get_packet_detail(packet_id, user_id):
    """红包详情（含领取列表，用于拆红包页面）"""
    with db_cursor() as cur:
        cur.execute('SELECT * FROM group_red_packets WHERE id=?', (packet_id,))
        p = cur.fetchone()
        if not p:
            return None
        cur.execute(
            'SELECT c.user_id, c.amount, c.claimed_at, u.username FROM group_red_packet_claims c LEFT JOIN users u ON c.user_id = u.id WHERE c.packet_id=? ORDER BY c.id ASC',
            (packet_id,)
        )
        claims = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT username FROM users WHERE id=?', (p['sender_id'],))
        s = cur.fetchone()
    claimed_by_me = None
    for c in claims:
        if c['user_id'] == user_id:
            claimed_by_me = c['amount']
            break
    return {
        'packet_id': p['id'],
        'sender_id': p['sender_id'],
        'sender_name': s['username'] if s else '',
        'total_amount': p['total_amount'],
        'total_count': p['total_count'],
        'claimed_count': p['claimed_count'],
        'status': p['status'],
        'message': p['message'],
        'source_type': p['source_type'],
        'packet_type': p['packet_type'] if 'packet_type' in p.keys() else 'lucky',
        'created_at': p['created_at'],
        'claims': claims,
        'claimed_by_me': claimed_by_me
    }


def expire_packets():
    """过期红包退款：user 退回发送者，group_pool 退回群池"""
    now = _now()
    expired = []
    with db_cursor() as cur:
        cur.execute("SELECT * FROM group_red_packets WHERE status='active' AND expires_at IS NOT NULL")
        rows = cur.fetchall()
    for p in rows:
        try:
            if datetime.fromisoformat(p['expires_at']) >= now:
                continue
        except Exception:
            continue
        remaining = float(p['remaining_amount'])
        if remaining <= 0:
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE group_red_packets SET status='expired' WHERE id=?", (p['id'],))
            expired.append(p['id'])
            continue
        with db_cursor(commit=True) as cur:
            if p['source_type'] == 'group_pool':
                cur.execute('UPDATE groups SET credits = credits + ? WHERE id=?', (remaining, p['group_id']))
                cur.execute('INSERT INTO group_credit_log (group_id, user_id, amount, tx_type, detail) VALUES (?, ?, ?, ?, ?)',
                            (p['group_id'], None, remaining, 'red_packet_refund', '红包过期退回群池 #' + str(p['id'])))
            else:
                cur.execute('UPDATE users SET credits = credits + ? WHERE id=?', (remaining, p['sender_id']))
            cur.execute("UPDATE group_red_packets SET status='expired' WHERE id=?", (p['id'],))
        expired.append(p['id'])
    return expired