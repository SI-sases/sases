import httpx
import os
import sys
# 确保能导入 core
sys.path.insert(0, os.getcwd())
from core.security import create_access_token

# 1. 伪造 admin 的 token
token = create_access_token({"sub": "1", "username": "admin"})

# 2. 请求发卡接口（trust_env=False 绕开代理）
client = httpx.Client(trust_env=False)
headers = {"Authorization": f"Bearer {token}"}
payload = {"count": 2, "key_type": "week", "days": 7}

try:
    resp = client.post("http://127.0.0.1:8001/admin/generate_keys", json=payload, headers=headers, timeout=5)
    print("状态码:", resp.status_code)
    print("返回:", resp.text)
except Exception as e:
    print("连接失败:", str(e))