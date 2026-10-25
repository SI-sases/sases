# -*- coding: utf-8 -*-
import requests, json, time

BASE_URL = "http://127.0.0.1:8001"
USERNAME = "666666"
PASSWORD = "123456"
CONV_ID = 25
COMMANDER_ID = "sases_api_w6t6g2zl"

# 登录
resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
token = resp.json()["access_token"]
print(f"✅ 登录成功")

# 构造危险任务
dangerous_cmd = "copy README.md test_backup.txt"
print(f"⚠️ 准备发送危险命令: {dangerous_cmd}")

# 模拟指挥官发 [TASK]:
task = {
    "task_id": f"test_{int(time.time())}",
    "steps": [
        {"step": 1, "description": "测试白名单", "command": dangerous_cmd}
    ]
}
task_msg = "[TASK]:" + json.dumps(task, ensure_ascii=False)

resp = requests.post(f"{BASE_URL}/messages/send",
    json={"conversation_id": CONV_ID, "content": task_msg, "sender_agent_id": COMMANDER_ID},
    headers={"Authorization": f"Bearer {token}"})
print(f"✅ 已发送测试任务，状态码: {resp.status_code}")
print(f"   等待 executor 处理...")
print(f"   请观察 executor 窗口，应该看到 '命令被安全策略拒绝: 命令不在白名单: copy'")
