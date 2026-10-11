"""diag_forward.py —— 模拟 8002 转发给 8001，验证转发链路。"""
import os
os.environ['SASES_NODE_ID'] = 'node-B'

import httpx
from core.node.identity import sign, get_public_key_b64
from core.hive.config import NODE_ID

print('=== 1. 当前 NODE_ID ===')
print('NODE_ID:', NODE_ID)
print('public_key:', get_public_key_b64(NODE_ID)[:30])

msg = f'{NODE_ID}:diag-1:/messages/send'
sig = sign(NODE_ID, msg)
headers = {
    'X-Hive-Forwarded': 'true',
    'X-Hive-From-Node': NODE_ID,
    'X-Hive-Request-Id': 'diag-1',
    'X-Hive-Node-Signature': sig,
    'X-Hive-Sign-Message': msg,
}

print()
print('=== 2. 测试 8001 的 health ===')
try:
    r = httpx.get('http://127.0.0.1:8001/hive/health', timeout=5, trust_env=False)
    print('status:', r.status_code, 'body:', r.text[:200])
except Exception as e:
    print('exception:', type(e).__name__, str(e))

print()
print('=== 3. 带转发 header 请求 8001 ===')
try:
    r = httpx.post('http://127.0.0.1:8001/messages/send',
                   json={'content': 'diag-with-header'},
                   headers=headers,
                   timeout=30, trust_env=False)
    print('status:', r.status_code)
    print('body:', r.text[:300])
except Exception as e:
    print('exception:', type(e).__name__, str(e))

print()
print('=== 4. 不带转发 header 请求 8001 ===')
try:
    r = httpx.post('http://127.0.0.1:8001/messages/send',
                   json={'content': 'diag-no-header'},
                   timeout=30, trust_env=False)
    print('status:', r.status_code)
    print('body:', r.text[:300])
except Exception as e:
    print('exception:', type(e).__name__, str(e))
