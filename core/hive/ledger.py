"""core/hive/ledger.py —— 账本快照计算。

只扫"官方账本"表，不扫用户私有数据。
所有官方节点对这些表应有一致视图。
"""
import hashlib
import json

# 锚定用：只扫跨节点应一致的数据（不含 transactions / contribution_log）
ANCHOR_TABLES = [
    ("groups",         ["id", "name", "owner_id"]),
    ("group_messages", ["id", "group_id", "sender_id", "content"]),
]

# 同步用：从节点镜像全量官方账本
SYNC_TABLES = [
    ("transactions",     ["id", "sender_id", "receiver_id", "amount", "tx_type", "status"]),
    ("contribution_log", ["id", "user_id", "event_type", "points"]),
    ("groups",           ["id", "name", "owner_id"]),
    ("group_messages",   ["id", "group_id", "sender_id", "content"]),
]

# 兼容旧引用
LEDGER_TABLES = SYNC_TABLES


def compute_ledger_hash():
    """返回 (hash, total_count, snapshot)。"""
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        snapshot = {}
        total = 0
        for table, cols in ANCHOR_TABLES:
            try:
                cur.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY id")
                rows = [tuple(r) for r in cur.fetchall()]
            except Exception:
                rows = []
            snapshot[table] = rows
            total += len(rows)
        payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return h, total, snapshot
    finally:
        conn.close()


def get_full_ledger():
    """返回完整账本数据（供 slave 同步用）——用 SYNC_TABLES。"""
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        snapshot = {}
        for table, cols in SYNC_TABLES:
            try:
                cur.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY id")
                rows = [tuple(r) for r in cur.fetchall()]
            except Exception:
                rows = []
            snapshot[table] = rows
        return snapshot
    finally:
        conn.close()