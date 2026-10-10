"""core/node/election.py —— 简化选举协议（3 节点官方集群）。

规则：
- 优先级数字小的先当选（8001=10 > 8002=20 > 8003=30）
- 通过 epoch 号防止裂脑
- 只有超过半数节点同意才当选
"""
import asyncio
import time

from core.hive.config import NODE_ID, HIVE_PEERS
from core.node.identity import sign, verify
from core.node.client import hive_headers


_election_state = {
    "current_epoch": 0,
    "my_role": "slave",
    "my_priority": 100,
    "last_election_at": 0,
    "votes_received": set(),
}


def get_election_state():
    return dict(_election_state)


def set_my_priority(p):
    _election_state["my_priority"] = p


def init_priority():
    """根据 NODE_ID 设置初始优先级（小数字优先）。"""
    mapping = {
        "node-A": 10,
        "node-B": 20,
        "node-C": 30,
    }
    p = mapping.get(NODE_ID, 100)
    _election_state["my_priority"] = p
    if NODE_ID == "node-A":
        _election_state["my_role"] = "master"
    print(f"[election] init: node={NODE_ID}, priority={p}, role={_election_state['my_role']}")



def set_my_role(role):
    _election_state["my_role"] = role
    print(f"[election] my role changed to: {role}")


async def check_master_health(master_url):
    """检查主节点是否存活。返回 True/False。"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False, headers=hive_headers()) as client:
            r = await client.get(f"{master_url}/hive/health")
            return r.status_code == 200
    except Exception:
        return False


async def propose_election():
    """发起选举：向 peers 请求投票。"""
    _election_state["last_election_at"] = time.time()
    _election_state["votes_received"] = set()

    new_epoch = _election_state["current_epoch"] + 1
    my_priority = _election_state["my_priority"]

    msg = f"{NODE_ID}:{new_epoch}:{my_priority}"
    sig = sign(NODE_ID, msg)

    body = {
        "candidate_id": NODE_ID,
        "new_epoch": new_epoch,
        "priority": my_priority,
        "signature": sig,
        "sign_message": msg,
    }

    import httpx
    votes = 0
    total = len(HIVE_PEERS) + 1
    needed = total // 2 + 1

    async with httpx.AsyncClient(timeout=5, trust_env=False, headers=hive_headers()) as client:
        for peer in HIVE_PEERS:
            try:
                r = await client.post(f"{peer}/hive/election/vote", json=body)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("vote") == "yes":
                        votes += 1
            except Exception:
                continue

    if votes + 1 >= needed:
        _election_state["current_epoch"] = new_epoch
        set_my_role("master")
        print(f"[election] WON: epoch={new_epoch}, votes={votes + 1}/{total}")
        # 当选后清空 masters（自己是主，不需要从别人同步）
        import core.hive.config as _cfg
        _cfg.HIVE_MASTERS = []
        return True
    else:
        print(f"[election] LOST: votes={votes + 1}/{total}")
        return False


def handle_vote_request(body):
    """处理其他节点的投票请求。返回 (vote, reason)。"""
    candidate_id = body.get("candidate_id")
    new_epoch = body.get("new_epoch")
    priority = body.get("priority")
    sig = body.get("signature")
    msg = body.get("sign_message")

    if not all([candidate_id, new_epoch, sig, msg]):
        return "no", "missing fields"

    from core.node.registry import get_node
    node = get_node(candidate_id)
    if not node:
        return "no", "candidate not registered"

    pub = node.get("public_key")
    if not verify(pub, sig, msg):
        return "no", "invalid signature"

    current_epoch = _election_state["current_epoch"]
    if new_epoch <= current_epoch:
        return "no", f"epoch too old ({new_epoch} <= {current_epoch})"

    my_priority = _election_state["my_priority"]
    if priority > my_priority:
        return "no", f"candidate priority lower ({priority} > {my_priority})"

    _election_state["current_epoch"] = new_epoch
    _election_state["my_role"] = "slave"
    return "yes", "voted"


async def periodic_election_check():
    """后台任务：检测主节点是否失效，若失效则发起选举。"""
    await asyncio.sleep(30)

    while True:
        try:
            if _election_state["my_role"] == "master":
                await asyncio.sleep(10)
                continue

            from core.hive.config import HIVE_MASTERS
            if not HIVE_MASTERS:
                await asyncio.sleep(10)
                continue

            master = HIVE_MASTERS[0]
            alive = await check_master_health(master)
            if alive:
                await asyncio.sleep(10)
                continue

            print(f"[election] master {master} unreachable, proposing election...")
            won = await propose_election()
            if won:
                from core.node.registry import upsert_node
                upsert_node(NODE_ID, "", "", "master")
        except Exception as e:
            print(f"[election] periodic check error: {e}")

        await asyncio.sleep(10)
