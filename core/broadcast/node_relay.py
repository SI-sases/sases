"""core/broadcast/node_relay.py —— L2 节点间广播。

流程：
  节点 A 广播 → push 给 peers → peers 本地广播（不再 push）
"""
import asyncio
import uuid
from collections import deque

from core.hive.config import NODE_ID, HIVE_PEERS
from core.node.client import hive_headers


_seen_events = deque(maxlen=500)
_seen_set = set()


def _mark_seen(event_id):
    if event_id in _seen_set:
        return False
    if len(_seen_events) >= _seen_events.maxlen:
        oldest = _seen_events[0]
        _seen_set.discard(oldest)
    _seen_events.append(event_id)
    _seen_set.add(event_id)
    return True


async def _do_push(body):
    import httpx
    async with httpx.AsyncClient(timeout=5, trust_env=False, headers=hive_headers()) as client:
        for peer in HIVE_PEERS:
            try:
                await client.post(f"{peer}/hive/broadcast/receive", json=body)
            except Exception as e:
                print(f"[node_relay] push to {peer} failed: {type(e).__name__}")


async def push_broadcast_to_peers(kind, target, message, event_id=None):
    """kind: 'user' | 'group'
       target: user_id 或 global_group_id
    """
    if not HIVE_PEERS:
        return
    if event_id is None:
        event_id = str(uuid.uuid4())
    body = {
        "origin": NODE_ID,
        "event_id": event_id,
        "kind": kind,
        "target": target,
        "message": message,
    }
    asyncio.create_task(_do_push(body))


async def handle_receive(body):
    """slave 收到 master 的广播，本地再广播一次（不再 push）。"""
    origin = body.get("origin")
    event_id = body.get("event_id")
    kind = body.get("kind")
    target = body.get("target")
    message = body.get("message")
    if origin == NODE_ID:
        return {"ok": True, "skipped": "self origin"}
    if not _mark_seen(event_id):
        return {"ok": True, "skipped": "duplicate"}
    from core.broadcast import ws_hub
    if kind == "user":
        await ws_hub.broadcast_to_user(int(target), message, relay=False)
    elif kind == "group":
        await ws_hub.broadcast_to_group(str(target), message, relay=False)
    return {"ok": True}