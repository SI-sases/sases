# core/services/transfer_service.py
from datetime import datetime, timedelta
from ..db import db_cursor

# 红包默认有效期（小时）
RED_PACKET_EXPIRE_HOURS = 24


def get_sent_red_packets(user_id, limit=50):
    '''查询指定用户已发送的红包记录'''
    with db_cursor() as cur:
        cur.execute(
            'SELECT id, receiver_id, amount, status, message, created_at '
            'FROM transactions WHERE sender_id=? AND tx_type LIKE ? '
            'ORDER BY id DESC LIMIT ?',
            (user_id, '%red_packet%', limit)
        )
        return [dict(r) for r in cur.fetchall()]

import json
def create_transfer(sender_id: int, receiver_id: int, amount: float, message: str = '', credit_type: str = 'credits', conversation_id: int = None):
    """转账：立即扣发送方，加接收方，一步完成"""
    if amount <= 0:
        return None, "金额必须大于0"
    if sender_id == receiver_id:
        return None, "不能转账给自己"

    with db_cursor(commit=True) as cur:
        if credit_type == 'compute':
            cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (sender_id,))
            row = cur.fetchone()
            if not row or row["balance"] < amount:
                return None, "算力余额不足"
            cur.execute("UPDATE user_compute_balance SET balance = balance - ? WHERE user_id=?", (amount, sender_id))
            cur.execute("INSERT INTO user_compute_balance (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", (receiver_id, amount, amount))
        else:
            cur.execute("SELECT credits FROM users WHERE id=?", (sender_id,))
            row = cur.fetchone()
            if not row or row["credits"] < amount:
                return None, "积分不足"
            cur.execute("UPDATE users SET credits = credits - ? WHERE id=?", (amount, sender_id))
            cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (amount, receiver_id))

        now = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO transactions
            (sender_id, receiver_id, amount, tx_type, status, message, completed_at, credit_type)
            VALUES (?, ?, ?, 'transfer', 'completed', ?, ?, ?)
        """, (sender_id, receiver_id, amount, message, now, credit_type))
        tx_id = cur.lastrowid

        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, '转账支出', 'transfer', ?, ?)
        """, (sender_id, -amount, f"向用户{receiver_id}转账({credit_type})"))
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, '转账收入', 'transfer', ?, ?)
        """, (receiver_id, amount, f"来自用户{sender_id}的转账({credit_type})"))

        # 插入双向气泡
        try:

            payload = {"tx_id": tx_id, "amount": amount, "credit_type": credit_type, "message": message or "转账"}
            msg_content = "[TRANSFER]:" + json.dumps(payload, ensure_ascii=False)
            now_str = datetime.now().isoformat()

            a_conv_id = conversation_id
            if not a_conv_id:
                cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (sender_id, receiver_id))
                r = cur.fetchone()
                if r: a_conv_id = r["id"]

            cur.execute("SELECT id FROM conversations WHERE user_id=? AND target_user_id=? AND is_friend_chat=1", (receiver_id, sender_id))
            r2 = cur.fetchone()
            b_conv_id = r2["id"] if r2 else None

            if a_conv_id:
                cur.execute("INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, 'user', ?, ?)", (a_conv_id, msg_content, now_str))
            if b_conv_id:
                cur.execute("INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, 'user', ?, ?)", (b_conv_id, msg_content, now_str))
        except Exception as e:
            print("转账气泡插入失败:", e)

        return tx_id, None


# ========== 红包（先冻结，后领取/退回） ==========

def create_red_packet(sender_id: int, receiver_id: int, amount: float,
                      message: str = '', expire_hours: int = RED_PACKET_EXPIRE_HOURS):
    """发红包：立即扣发送方积分（冻结），等待接收方领取"""
    if amount <= 0:
        return None, "金额必须大于0"
    if sender_id == receiver_id:
        return None, "不能发红包给自己"

    with db_cursor(commit=True) as cur:
        # 检查余额
        cur.execute("SELECT credits FROM users WHERE id=?", (sender_id,))
        row = cur.fetchone()
        if not row or row["credits"] < amount:
            return None, "积分不足"

        # 立即扣发送方（冻结）
        cur.execute("UPDATE users SET credits = credits - ? WHERE id=?", (amount, sender_id))

        now = datetime.now()
        expires = now + timedelta(hours=expire_hours)

        # 创建 pending 红包
        cur.execute("""
            INSERT INTO transactions
            (sender_id, receiver_id, amount, tx_type, status, message, expires_at, credit_type)
            VALUES (?, ?, ?, 'red_packet', 'pending', ?, ?, ?)
        """, (sender_id, receiver_id, amount, message, expires.isoformat(), credit_type))
        tx_id = cur.lastrowid

        # 积分日志（支出）
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, '发红包支出', 'transfer', ?, ?)
        """, (sender_id, -amount, f"向用户{receiver_id}发红包"))

        return tx_id, None


def claim_red_packet(tx_id: int, receiver_id: int):
    """领取红包：把金额加给接收方"""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
        tx = cur.fetchone()
        if not tx:
            return False, "红包不存在"
        if tx["tx_type"] != "red_packet":
            return False, "非红包交易"
        if tx["receiver_id"] != receiver_id:
            return False, "无权领取"
        if tx["status"] != "pending":
            return False, f"红包状态为 {tx['status']}，无法领取"

        # 检查是否过期
        if tx["expires_at"]:
            try:
                expires = datetime.fromisoformat(tx["expires_at"])
                if datetime.now() > expires:
                    # 过期：退回发送方
                    cur.execute("UPDATE users SET credits = credits + ? WHERE id=?",
                                (tx["amount"], tx["sender_id"]))
                    cur.execute("UPDATE transactions SET status='refunded' WHERE id=?", (tx_id,))
                    cur.execute("""
                        INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                        VALUES (?, '红包过期退回', 'transfer', ?, ?)
                    """, (tx["sender_id"], tx["amount"], "红包过期未领取，已退回"))
                    return False, "红包已过期，已退回发送方"
            except Exception:
                pass

        now = datetime.now().isoformat()
        # 加接收方
        cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (tx["amount"], receiver_id))
        cur.execute("""
            UPDATE transactions SET status='completed', completed_at=?, claimed_at=?
            WHERE id=?
        """, (now, now, tx_id))

        # 积分日志（收入）
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, '红包收入', 'transfer', ?, ?)
        """, (receiver_id, tx["amount"], f"来自用户{tx['sender_id']}的红包"))

        return True, None


def refund_expired_packets():
    """扫描所有过期红包，退回发送方（供定时任务调用）"""
    count = 0
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT id, sender_id, amount FROM transactions
            WHERE tx_type='red_packet' AND status='pending'
              AND expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
        rows = cur.fetchall()

        for row in rows:
            cur.execute("UPDATE users SET credits = credits + ? WHERE id=?",
                        (row["amount"], row["sender_id"]))
            cur.execute("UPDATE transactions SET status='refunded' WHERE id=?", (row["id"],))
            cur.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '红包过期退回', 'transfer', ?, ?)
            """, (row["sender_id"], row["amount"], "红包过期未领取，已退回"))
            count += 1

    return count


# ========== 查询 ==========

def get_pending_transfers(user_id: int):
    """获取用户待领取的红包（未过期）"""
    now = datetime.now().isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT t.id, t.sender_id, u.username as sender_name, t.amount,
                   t.message, t.created_at, t.expires_at
            FROM transactions t
            JOIN users u ON t.sender_id = u.id
            WHERE t.receiver_id=? AND t.tx_type='red_packet' AND t.status='pending'
              AND (t.expires_at IS NULL OR t.expires_at > ?)
            ORDER BY t.created_at DESC
        """, (user_id, now))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_transaction(tx_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_transaction_history(user_id: int, limit: int = 50):
    """查询用户所有交易记录（发出或接收）"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT t.*,
                   s.username as sender_name,
                   r.username as receiver_name
            FROM transactions t
            LEFT JOIN users s ON t.sender_id = s.id
            LEFT JOIN users r ON t.receiver_id = r.id
            WHERE t.sender_id=? OR t.receiver_id=?
            ORDER BY t.created_at DESC
            LIMIT ?
        """, (user_id, user_id, limit))
        return [dict(row) for row in cur.fetchall()]


# 兼容旧接口
def complete_transfer(tx_id: int):
    """兼容旧调用：等价于领取红包"""
    tx = get_transaction(tx_id)
    if not tx:
        return False
    if tx["tx_type"] == "red_packet":
        ok, _ = claim_red_packet(tx_id, tx["receiver_id"])
        return ok
    return False


def refund_transfer(tx_id: int):
    """兼容旧调用：退款指定交易"""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM transactions WHERE id=? AND status='pending'", (tx_id,))
        tx = cur.fetchone()
        if not tx:
            return False
        cur.execute("UPDATE users SET credits = credits + ? WHERE id=?",
                    (tx["amount"], tx["sender_id"]))
        cur.execute("UPDATE transactions SET status='refunded' WHERE id=?", (tx_id,))
        return True

def insert_message(conversation_id: int, sender: str, content: str, sender_agent_id: str = None):
    """向会话插入一条消息（供红包/转账使用）"""
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, ?, ?, ?)",
                (conversation_id, sender, content, sender_agent_id)
            )
        else:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
                (conversation_id, sender, content)
            )
        cur.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), conversation_id)
        )
        return cur.lastrowid
