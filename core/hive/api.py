"""core/hive/api.py —— /hive/* 路由。"""
from fastapi import APIRouter

from core.hive.config import NODE_ID, HIVE_ROLE, HIVE_PEERS
from core.hive.ledger import compute_ledger_hash, get_full_ledger
from core.hive.anchor import get_latest_anchor

router = APIRouter(prefix="/hive", tags=["hive"])


@router.get("/hash")
def hive_hash():
    h, count, _ = compute_ledger_hash()
    return {"node_id": NODE_ID, "hash": h, "count": count}


@router.get("/anchor")
def hive_anchor():
    a = get_latest_anchor(NODE_ID)
    if not a:
        h, count, _ = compute_ledger_hash()
        return {
            "node_id": NODE_ID,
            "anchor_hash": h,
            "record_count": count,
            "ts": None,
        }
    return {
        "node_id": a["node_id"],
        "anchor_hash": a["anchor_hash"],
        "record_count": a["record_count"],
        "ts": a["ts"],
    }


@router.get("/anchors")
def hive_anchors(limit: int = 20):
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT node_id, ts, anchor_hash, record_count FROM credit_anchors "
            "WHERE node_id=? ORDER BY id DESC LIMIT ?",
            (NODE_ID, limit),
        )
        rows = cur.fetchall()
        return {
            "anchors": [
                dict(zip(["node_id", "ts", "anchor_hash", "record_count"], r))
                for r in rows
            ]
        }
    finally:
        conn.close()


@router.get("/ledger")
def hive_ledger():
    """返回全量账本（供 slave 同步用）。"""
    return {"node_id": NODE_ID, "ledger": get_full_ledger()}