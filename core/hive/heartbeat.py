"""core/hive/heartbeat.py —— 心跳对比 + 告警去重。"""
import asyncio
from datetime import datetime

from core.hive.config import NODE_ID, HIVE_PEERS, HEARTBEAT_INTERVAL, HIVE_MODE
from core.hive.ledger import compute_ledger_hash

_last_state = None


async def heartbeat_check():
    global _last_state
    if not HIVE_PEERS:
        return
    import httpx
    await asyncio.sleep(15)
    while True:
        try:
            my_hash, _, _ = compute_ledger_hash()
            mismatches = []
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                for peer in HIVE_PEERS:
                    try:
                        r = await client.get(f"{peer}/hive/anchor")
                        data = r.json()
                        peer_hash = data.get("anchor_hash")
                        peer_node = data.get("node_id", peer)
                        if peer_hash and peer_hash != my_hash:
                            mismatches.append((peer_node, peer_hash))
                    except Exception:
                        pass

            if not mismatches:
                _last_state = None
            else:
                current_state = tuple(sorted(mismatches))
                if current_state != _last_state:
                    _last_state = current_state
                    ts = datetime.now().isoformat()
                    for node, h in mismatches:
                        print(
                            f"[hive-heartbeat] {ts} MISMATCH: "
                            f"{NODE_ID}={my_hash[:16]} vs {node}={h[:16]}"
                        )
                        if HIVE_MODE == "enforce":
                            print(f"[hive-heartbeat] ENFORCE: 触发锁定 {node}（待实现）")
        except Exception as e:
            print(f"[hive-heartbeat] error: {e}")
        await asyncio.sleep(HEARTBEAT_INTERVAL)