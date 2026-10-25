# -*- coding: utf-8 -*-
import requests

BASE_URL = "http://127.0.0.1:8001"
USERNAME = "666666"
PASSWORD = "123456"
COMMANDER_ID = "sases_api_w6t6g2zl"
EXECUTOR_ID = "sases_api_npaeckg1"

# 1. 登录
print("[1] 登录中...")
resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
if resp.status_code != 200:
    print(f"登录失败: {resp.text}")
    exit(1)
token = resp.json()["access_token"]
print(f"    ✅ 登录成功")

# 2. 查看会话列表
print("\n[2] 获取会话列表...")
resp = requests.get(
    f"{BASE_URL}/messages/conversations",
    headers={"Authorization": f"Bearer {token}"}
)
conversations = resp.json().get("conversations", [])
if not conversations:
    print("    ❌ 你没有会话。请先在浏览器打开 http://127.0.0.1:8001 新建一个会话")
    exit(1)

print("    你的会话列表：")
for i, c in enumerate(conversations):
    print(f"      [{i}] ID={c['id']} | 标题={c['title']}")

# 3. 自动选择第一个会话（如需选择其他，修改 idx）
idx = 0
conv_id = conversations[idx]['id']
print(f"\n[3] 使用会话 ID = {conv_id}")

# 4. 输入任务
task = input("\n[4] 请输入任务描述（如：列出当前目录）: ").strip()
if not task:
    task = "列出当前目录"
    print(f"    使用默认任务: {task}")

# 5. 调用 /swarm/plan
print(f"\n[5] 调用 /swarm/plan ...")
resp = requests.post(
    f"{BASE_URL}/swarm/plan",
    json={
        "conversation_id": conv_id,
        "user_input": task,
        "commander_id": COMMANDER_ID,
        "executor_id": EXECUTOR_ID
    },
    headers={"Authorization": f"Bearer {token}"}
)
print(f"    状态码: {resp.status_code}")
print(f"    返回结果: {resp.json()}")

print("\n✅ 完成。现在打开浏览器，进入这个会话查看消息流转：")
print(f"   http://127.0.0.1:8001 → 消息 → 会话 {conv_id}")
print(f"\n如果 executor_v2.py 正在运行，你会在 3 秒内看到：")
print(f"   1. 你发的用户消息")
print(f"   2. 指挥官的 [TASK]: 消息")
print(f"   3. 执行者的 [STEP_DONE]: 消息")
print(f"   4. 指挥官的 [SUMMARY]: 消息")
