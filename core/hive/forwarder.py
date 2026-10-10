"""core/hive/forwarder.py —— 副本写代理转发 + 主节点验签。"""
import time
import uuid

from core.hive.config import NODE_ID, HIVE_MASTERS, FORWARD_MODE
from core.hive.client import hive_headers
from core.hive.identity import sign, verify


# 熔断器
_circuit = {}
CIRCUIT_FAIL_THRESHOLD = 3
CIRCUIT_COOLDOWN_SEC = 60

# 统计
_stats = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "total_latency_ms": 0,
}


def get_forward_stats():
    s = dict(_stats)
    s["avg_latency_ms"] = round(s["total_latency_ms"] / s["total"], 1) if s["total"] else 0
    s.pop("total_latency_ms", None)
    return s


def _is_circuit_open(url):
    state = _circuit.get(url)
    if not state:
        return False
    if state.get("cooldown_until", 0) > time.time():
        return True
    return False


def _mark_url_fail(url):
    state = _circuit.setdefault(url, {"fails": 0, "cooldown_until": 0})
    state["fails"] += 1
    if state["fails"] >= CIRCUIT_FAIL_THRESHOLD:
        state["cooldown_until"] = time.time() + CIRCUIT_COOLDOWN_SEC
        print(f"[forwarder] circuit OPEN for {url} (cooldown {CIRCUIT_COOLDOWN_SEC}s)")


def _mark_url_success(url):
    if url in _circuit:
        _circuit[url] = {"fails": 0, "cooldown_until": 0}



def pick_master_urls():
    """从 node_registry 查 role=master 的节点，按顺序返回 URL。"""
    from core.hive.registry import list_nodes
    masters = [n for n in list_nodes() if n.get('role') == 'master' and n.get('status') == 'active']
    urls = [m['url'] for m in masters if m.get('url')]
    for u in HIVE_MASTERS:
        if u not in urls:
            urls.append(u)
    import os
    my_port = os.environ.get('SASES_PORT', '8001')
    urls = [u for u in urls if f':{my_port}' not in u]
    urls = [u for u in urls if not _is_circuit_open(u)]
    return urls


async def _trigger_replica_sync():
    """副本转发成功后，异步触发一次同步（不阻塞响应）。"""
    try:
        from core.hive.replica import do_one_sync
        ok, total = await do_one_sync()
        if ok:
            print(f"[forwarder] triggered sync: {total} rows")
    except Exception as e:
        print(f"[forwarder] trigger sync failed: {e}")



async def forward_request(method, path, body, headers, query=''):
    """转发请求给主节点。返回 (status_code, response_dict) 或 (None, None)。"""
    if FORWARD_MODE != 'auto':
        return None, None
    targets = pick_master_urls()
    if not targets:
        return 503, {'error': 'no master available (all circuit open or none registered)'}

    _stats["total"] += 1
    start = time.time()

    request_id = str(uuid.uuid4())
    msg = f"{NODE_ID}:{request_id}:{path}"
    node_sig = sign(NODE_ID, msg)

    forward_headers = {}
    for k, v in headers.items():
        kl = k.lower()
        if kl in ('content-type', 'authorization', 'accept'):
            forward_headers[k] = v
    forward_headers['X-Hive-Forwarded'] = 'true'
    forward_headers['X-Hive-From-Node'] = NODE_ID
    forward_headers['X-Hive-Request-Id'] = request_id
    forward_headers['X-Hive-Node-Signature'] = node_sig
    forward_headers['X-Hive-Sign-Message'] = msg

    import httpx
    async with httpx.AsyncClient(timeout=5, trust_env=False, headers=hive_headers()) as client:
        for target in targets:
            try:
                url = f"{target}{path}"
                if query:
                    url = f"{url}?{query}"
                r = await client.request(method, url, content=body, headers=forward_headers)
                elapsed_ms = int((time.time() - start) * 1000)
                _stats["total_latency_ms"] += elapsed_ms
                _stats["success"] += 1
                _mark_url_success(target)
                ct = r.headers.get('content-type', '')
                if ct.startswith('application/json'):
                    return r.status_code, r.json()
                return r.status_code, {'raw': r.text[:500]}
            except Exception as e:
                print(f"[forwarder] {target} failed: {e}")
                _mark_url_fail(target)
                continue
    _stats["failed"] += 1
    return 503, {'error': 'all masters unreachable'}


def verify_forward_signature(headers):
    """主节点：验证转发请求的节点签名。"""
    node_id = headers.get('X-Hive-From-Node')
    msg = headers.get('X-Hive-Sign-Message')
    sig = headers.get('X-Hive-Node-Signature')
    if not all([node_id, msg, sig]):
        return False, 'missing headers'
    from core.hive.registry import get_node
    node = get_node(node_id)
    if not node:
        return False, 'node not registered'
    pub = node.get('public_key')
    if not pub:
        return False, 'no public key'
    if not verify(pub, sig, msg):
        return False, 'signature invalid'
    return True, ''


def check_and_record_request(request_id, node_id):
    """幂等检查：返回 True 表示重复请求。"""
    from core.db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM forwarded_requests WHERE request_id=?", (request_id,))
        if cur.fetchone():
            return True
        cur.execute(
            "INSERT INTO forwarded_requests (request_id, node_id) VALUES (?, ?)",
            (request_id, node_id)
        )
        return False
