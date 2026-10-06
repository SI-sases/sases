# core/services/anchor_service.py
"""蜂群积分锚定服务（P0：自证模式）。"""
import hashlib
import json
from datetime import datetime, timezone

from core.config import NODE_ID


def compute_anchor():
    """扫描积分相关数据，算出快照 hash。返回 (hash, record_count, snapshot)。"""
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, credits FROM users ORDER BY id")
        users = [(r[0], float(r[1] or 0)) for r in cur.fetchall()]

        cur.execute("SELECT id, user_id, points FROM contribution_log ORDER BY id")
        logs = [(r[0], r[1], float(r[2] or 0)) for r in cur.fetchall()]

        cur.execute("SELECT id, sender_id, receiver_id, amount, status FROM transactions ORDER BY id")
        txs = [tuple(r) for r in cur.fetchall()]

        snapshot = {
            "node_id": NODE_ID,
            "users": users,
            "logs": logs,
            "txs": txs,
        }
        payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        count = len(users) + len(logs) + len(txs)
        return h, count, snapshot
    finally:
        conn.close()


def write_anchor():
    """计算并写入 credit_anchors。返回 (hash, count)。"""
    from core.db import db_cursor
    h, count, _ = compute_anchor()
    ts = datetime.now(timezone.utc).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO credit_anchors (node_id, ts, anchor_hash, record_count) VALUES (?,?,?,?)",
            (NODE_ID, ts, h, count),
        )
    return h, count


def get_latest_anchor(node_id=None):
    """查询最新锚定。node_id 为空则查全表最新一条。"""
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        if node_id:
            cur.execute(
                "SELECT node_id, ts, anchor_hash, record_count FROM credit_anchors "
                "WHERE node_id=? ORDER BY id DESC LIMIT 1",
                (node_id,),
            )
        else:
            cur.execute(
                "SELECT node_id, ts, anchor_hash, record_count FROM credit_anchors "
                "ORDER BY id DESC LIMIT 1"
            )
        row = cur.fetchone()
        return dict(zip(["node_id", "ts", "anchor_hash", "record_count"], row)) if row else None
    finally:
        conn.close()
