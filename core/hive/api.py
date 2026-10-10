"""core/hive/api.py —— /hive/* 路由。"""
from fastapi import APIRouter, Depends, Header, HTTPException

from core.hive.config import NODE_ID, HIVE_ROLE, HIVE_PEERS
from core.ledger.ledger import compute_ledger_hash, get_full_ledger
from core.ledger.anchor import get_latest_anchor

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
    from core.ledger.sync import get_sync_health
    return {
        "node_id": NODE_ID,
        "role": HIVE_ROLE,
        "replica_mode": __import__('core.hive.config', fromlist=['REPLICA_MODE']).REPLICA_MODE,
        "sync": get_sync_health(),
        "latest_anchor": get_latest_anchor(NODE_ID),
    }



@router.get("/config")
def hive_config():
    """返回当前节点的生效配置（合并后）。"""
    from core.hive import config as _c
    return {
        "node_id": _c.NODE_ID,
        "role": _c.HIVE_ROLE,
        "enable_hive": _c.ENABLE_HIVE,
        "masters": _c.HIVE_MASTERS,
        "peers": _c.HIVE_PEERS,
        "mode": _c.HIVE_MODE,
        "token_set": bool(_c.HIVE_TOKEN),
        "degrade_threshold": _c.DEGRADE_THRESHOLD,
        "intervals": {
            "anchor": _c.ANCHOR_INTERVAL,
            "heartbeat": _c.HEARTBEAT_INTERVAL,
            "vote": _c.VOTE_INTERVAL,
            "sync": _c.SYNC_INTERVAL,
        },
        "config_file": _c._JSON_CONFIG_PATH,
        "config_file_exists": __import__('os').path.exists(_c._JSON_CONFIG_PATH),
    }



@router.get("/replica/export")
def hive_replica_export():
    """主节点：导出核心业务表（供副本拉取）。"""
    from core.ledger.replica import export_replica
    return {"node_id": NODE_ID, "tables": export_replica()}



@router.get("/forward/stats")
def hive_forward_stats():
    """转发统计（副本调用）。"""
    from core.node.forwarder import get_forward_stats
    return {"node_id": NODE_ID, "stats": get_forward_stats()}



@router.get("/health")
def hive_health():
    """健康检查端点（用于选举检测）。"""
    return {"ok": True, "node_id": NODE_ID, "role": HIVE_ROLE}


@router.post("/election/vote")
def hive_election_vote(body: dict):
    """处理选举投票请求。"""
    from core.node.election import handle_vote_request
    vote, reason = handle_vote_request(body)
    return {"vote": vote, "reason": reason, "voter_id": NODE_ID}


@router.get("/election/state")
def hive_election_state():
    """查看当前选举状态。"""
    from core.node.election import get_election_state
    return {"node_id": NODE_ID, **get_election_state()}



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
    from core.node.identity import verify
    msg = f'{node_id}:{url}:{role}'
    if not verify(public_key, signature, msg):
        raise HTTPException(status_code=401, detail='invalid signature')
    from core.node.registry import upsert_node, list_nodes
    upsert_node(node_id, public_key, url, role)
    return {'node_id': NODE_ID, 'nodes': list_nodes()}


@router_public.get('/nodes')
def hive_nodes():
    from core.node.registry import list_nodes
    return {'node_id': NODE_ID, 'nodes': list_nodes()}
