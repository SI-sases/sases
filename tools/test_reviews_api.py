# -*- coding: utf-8 -*-
import requests

BASE_URL = "http://127.0.0.1:8001"
USERNAME = "666666"
PASSWORD = "123456"

# 登录
resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
token = resp.json()["access_token"]
print(f"✅ 登录成功")

# 查询审核日志
resp = requests.get(
    f"{BASE_URL}/swarm/reviews?limit=10",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"状态码: {resp.status_code}")
data = resp.json()
reviews = data.get("reviews", [])
print(f"共 {len(reviews)} 条审核日志：\n")
for r in reviews:
    print(f"#{r['id']} | {r['task_id']} | step {r['step_id']} | {r['command'][:40]}")
    print(f"   exec={r['exec_status']} | review={r['review_result']} | reason={r['review_reason']}")
    print()
