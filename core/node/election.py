"""core/node/election.py —— 简化选举协议（3 节点官方集群）。

规则：
- 优先级数字小的先当选（8001=10 > 8002=20 > 8003=30）
- 通过 epoch 号防止裂脑
- epoch 持久化到 node_registry，重启不丢
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


def set_my_role(role):
    _election_state["my_role"] = role
    print(f"[election] my role changed to: {role}")


# ========== epoch 持久化 ==========

def save_epoch_to_db(epoch):
    """把 epoch 写入 node_registry（自己那行）。"""
    try:
        from core.db import db_cursor
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE node_registry SET master_epoch=? WHERE node_id=?",
                (epoch, NODE_ID)
            )
        print(f"[election] epoch saved to db: {epoch}")
    except Exception as e:
        print(f"[election] save epoch failed: {e}")


def check_higher_epoch_on_startup():
    """启动时检查 registry 中是否有更高 epoch 的 master。若有则降级。"""
    try:
        from core.db import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT node_id, master_epoch FROM node_registry "
                "WHERE master_epoch > ? AND node_id != ?",
                (_election_state["current_epoch"], NODE_ID)
            )
            rows = cur.fetchall()
            if rows:
                max_epoch = max(r[1] for r in rows)
                higher_node = [r[0] for r in rows if r[1] == max_epoch][0]
                _election_state["current_epoch"] = max_epoch
                _election_state["my_role"] = "slave"
                print(f"[election] startup: found higher epoch {max_epoch} at {higher_node}, downgrading to slave")
        finally:
            conn.close()
    except Exception as e:
        print(f"[election] check higher epoch failed: {e}")



def load_epoch_from_db():
    """从 node_registry 读 epoch。"""
    try:
        from core.db import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT master_epoch FROM node_registry WHERE node_id=?", (NODE_ID,))
            row = cur.fetchone()
            if row and row[0]:
                _election_state["current_epoch"] = int(row[0])
                print(f"[election] loaded epoch from db: {row[0]}")
        finally:
            conn.close()
    except Exception as e:
        print(f"[election] load epoch failed: {e}")


def get_peer_epochs():
    """通过 /hive/election/state 查询 peers 的 epoch。"""
    import httpx
    epochs = []
    for peer in HIVE_PEERS:
        try:
            r = httpx.get(f"{peer}/hive/election/state", timeout=3, trust_env=False)
            if r.status_code == 200:
                epochs.append(r.json().get("current_epoch", 0))
        except Exception:
            continue
    return epochs


# ========== 初始化 ==========

def check_peer_epochs():
    """向 peers 查 epoch，若发现更高 epoch 的 master，降级自己。"""
    try:
        import httpx
        for peer in HIVE_PEERS:
            try:
                r = httpx.get(f"{peer}/hive/election/state", timeout=3, trust_env=False)
                if r.status_code != 200:
                    continue
                data = r.json()
                peer_epoch = data.get("current_epoch", 0)
                peer_role = data.get("my_role", "slave")
                if peer_role == "master" and peer_epoch >= _election_state["current_epoch"]:
                    _election_state["current_epoch"] = peer_epoch
                    _election_state["my_role"] = "slave"
                    # 关键：降级后立即把 master 填入 HIVE_MASTERS
                    import core.hive.config as _cfg
                    if peer not in _cfg.HIVE_MASTERS:
                        _cfg.HIVE_MASTERS = [peer]
                    print(f"[election] startup: peer {peer} is master (epoch={peer_epoch}), downgrading to slave, HIVE_MASTERS={_cfg.HIVE_MASTERS}")
                    return True
            except Exception:
                continue
    except Exception as e:
        print(f"[election] check peers failed: {e}")
    return False



def init_priority():
    """根据 NODE_ID 设置初始优先级（小数字优先）+ 从 DB 加载 epoch。"""
    import os as _os
    _node_id = _os.environ.get("SASES_NODE_ID", NODE_ID)
    mapping = {
        "node-A": 10,
        "node-B": 20,
        "node-C": 30,
    }
    p = mapping.get(_node_id, 100)
    _election_state["my_priority"] = p
    if _node_id == "node-A":
        _election_state["my_role"] = "master"

    load_epoch_from_db()
    check_higher_epoch_on_startup()
    check_peer_epochs()
    print(f"[election] init: node={_node_id}, priority={p}, role={_election_state['my_role']}, epoch={_election_state['current_epoch']}")


# ========== 健康检测 ==========

async def check_master_health(master_url):
    """检查主节点是否存活。返回 True/False。"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False, headers=hive_headers()) as client:
            r = await client.get(f"{master_url}/hive/health")
            return r.status_code == 200
    except Exception:
        return False


# ========== 选举 ==========

async def propose_election():
    """发起选举：向 peers 请求投票。"""
    _election_state["last_election_at"] = time.time()
    _election_state["votes_received"] = set()

    # 先查询 peers 的 epoch，取最大值 +1
    peer_epochs = get_peer_epochs()
    max_epoch = _election_state["current_epoch"]
    if peer_epochs:
        max_epoch = max([max_epoch] + peer_epochs)
    new_epoch = max_epoch + 1
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
        # 持久化 epoch
        save_epoch_to_db(new_epoch)
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

    # 接受：更新本地 epoch 并持久化
    _election_state["current_epoch"] = new_epoch
    _election_state["my_role"] = "slave"
    save_epoch_to_db(new_epoch)
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
