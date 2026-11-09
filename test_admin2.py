import httpx
from core.security import create_access_token

# 1. 直接伪造一个 admin (id=1) 的 token
token = create_access_token({"sub": "1", "username": "admin"})
print("已生成测试 Token")

# 2. 请求发卡接口
headers = {"Authorization": f"Bearer {token}"}
payload = {"count": 2, "key_type": "week", "days": 7}
resp = httpx.post("http://127.0.0.1:8001/admin/generate_keys", json=payload, headers=headers)

print("状态码:", resp.status_code)
print("返回:", resp.text)