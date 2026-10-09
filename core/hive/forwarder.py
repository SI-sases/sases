"""core/hive/forwarder.py —— 副本写代理转发 + 主节点验签。"""
import time
import uuid

from core.hive.config import NODE_ID, HIVE_MASTERS, FORWARD_MODE
from core.hive.client import hive_headers
from core.hive.identity import sign, verify


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
    return urls


async def forward_request(method, path, body, headers, query=''):
    """转发请求给主节点。返回 (status_code, response_dict) 或 (None, None)。"""
    if FORWARD_MODE != 'auto':
        return None, None
    targets = pick_master_urls()
    if not targets:
        return 503, {'error': 'no master available'}

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
    async with httpx.AsyncClient(timeout=10, trust_env=False, headers=hive_headers()) as client:
        for target in targets:
            try:
                url = f"{target}{path}"
                if query:
                    url = f"{url}?{query}"
                r = await client.request(method, url, content=body, headers=forward_headers)
                ct = r.headers.get('content-type', '')
                if ct.startswith('application/json'):
                    return r.status_code, r.json()
                return r.status_code, {'raw': r.text[:500]}
            except Exception as e:
                print(f"[forwarder] {target} failed: {e}")
                continue
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
