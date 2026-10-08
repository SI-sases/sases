"""core/hive/api.py —— /hive/* 路由。"""
from fastapi import APIRouter, Depends, Header, HTTPException

from core.hive.config import NODE_ID, HIVE_ROLE, HIVE_PEERS
from core.hive.ledger import compute_ledger_hash, get_full_ledger
from core.hive.anchor import get_latest_anchor

def _check_hive_token(authorization: str = Header("")):
    from core.hive.config import HIVE_TOKEN
    if not HIVE_TOKEN:
        return
    if authorization != f"Bearer {HIVE_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid hive token")


router = APIRouter(
    prefix="/hive",
    tags=["hive"],
    dependencies=[Depends(_check_hive_token)],
)


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


@router.get("/status")
def hive_status():
    from core.hive.sync import get_sync_health
    return {
        "node_id": NODE_ID,
        "role": HIVE_ROLE,
        "sync": get_sync_health(),
        "latest_anchor": get_latest_anchor(NODE_ID),
    }



@router.get("/ledger")
def hive_ledger():
    """返回全量账本（供 slave 同步用）。"""
    return {"node_id": NODE_ID, "ledger": get_full_ledger()}

# ========== 公开端点（不需要 token） ==========
router_public = APIRouter(prefix='/hive', tags=['hive-public'])


@router_public.post('/register')
def hive_register(body: dict):
    node_id = body.get('node_id')
    public_key = body.get('public_key')
    url = body.get('url')
    role = body.get('role', 'slave')
    signature = body.get('signature')
    if not all([node_id, public_key, url, signature]):
        raise HTTPException(status_code=400, detail='missing fields')
    from core.hive.identity import verify
    msg = f'{node_id}:{url}:{role}'
    if not verify(public_key, signature, msg):
        raise HTTPException(status_code=401, detail='invalid signature')
    from core.hive.registry import upsert_node, list_nodes
    upsert_node(node_id, public_key, url, role)
    return {'node_id': NODE_ID, 'nodes': list_nodes()}


@router_public.get('/nodes')
def hive_nodes():
    from core.hive.registry import list_nodes
    return {'node_id': NODE_ID, 'nodes': list_nodes()}
