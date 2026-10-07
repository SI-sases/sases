"""core/hive/anchor.py —— 锚定写入 + 后台任务。"""
import asyncio
from datetime import datetime, timezone

from core.hive.config import NODE_ID, ANCHOR_INTERVAL
from core.hive.ledger import compute_ledger_hash


def write_ledger_anchor():
    """计算并写入账本锚定。返回 (hash, count)。"""
    from core.db import db_cursor
    h, count, _ = compute_ledger_hash()
    ts = datetime.now(timezone.utc).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO credit_anchors (node_id, ts, anchor_hash, record_count) "
            "VALUES (?,?,?,?)",
            (NODE_ID, ts, h, count),
        )
    return h, count


def get_latest_anchor(node_id=None):
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
        if not row:
            return None
        return dict(zip(["node_id", "ts", "anchor_hash", "record_count"], row))
    finally:
        conn.close()


async def periodic_anchor_task():
    """每 ANCHOR_INTERVAL 秒写一次锚定。"""
    await asyncio.sleep(30)
    while True:
        try:
            h, count = write_ledger_anchor()
            print(f"[hive-anchor] {h[:16]}... count={count}")
        except Exception as e:
            print(f"[hive-anchor] error: {e}")
        await asyncio.sleep(ANCHOR_INTERVAL)