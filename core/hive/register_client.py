"""core/hive/register_client.py —— 节点自动注册客户端。

启动时向已知 peers 注册自己，并拉回对方的节点列表。
"""
import asyncio

from core.hive.config import NODE_ID, HIVE_ROLE, HIVE_PEERS, HIVE_MASTERS, HIVE_TOKEN
from core.hive.client import hive_headers
from core.hive.identity import get_public_key_b64, sign


def _my_url(port_env='SASES_PORT'):
    import os
    port = os.environ.get(port_env, '8001')
    return f"http://127.0.0.1:{port}"


def _targets():
    seen = set()
    out = []
    for u in (HIVE_PEERS + HIVE_MASTERS):
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def register_with_peers():
    """向所有已知 peers 注册自己，并拉回节点列表。"""
    targets = _targets()
    if not targets:
        print('[hive-register] no peers to register with')
        return

    import httpx
    my_pub = get_public_key_b64(NODE_ID)
    my_url = _my_url()
    msg = f"{NODE_ID}:{my_url}:{HIVE_ROLE}"
    sig = sign(NODE_ID, msg)
    body = {
        'node_id': NODE_ID,
        'public_key': my_pub,
        'url': my_url,
        'role': HIVE_ROLE,
        'signature': sig,
    }

    from core.hive.registry import upsert_node

    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        for target in targets:
            try:
                r = await client.post(
                    f"{target}/hive/register",
                    json=body,
                    headers=hive_headers(),
                )
                if r.status_code != 200:
                    print(f"[hive-register] {target} → {r.status_code}")
                    continue
                data = r.json()
                nodes = data.get('nodes', [])
                for n in nodes:
                    upsert_node(n['node_id'], n.get('public_key', ''), n.get('url', ''), n.get('role', 'slave'))
                print(f"[hive-register] {target} → ok, {len(nodes)} nodes cached")
            except Exception as e:
                print(f"[hive-register] {target} failed: {e}")


async def periodic_register_task():
    """启动后注册一次，之后每 5 分钟重新注册（保持 last_seen 新鲜）。"""
    await asyncio.sleep(20)
    while True:
        try:
            await register_with_peers()
        except Exception as e:
            print(f'[hive-register] error: {e}')
        await asyncio.sleep(300)
