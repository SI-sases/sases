import requests, time, json, sys, subprocess, datetime

BASE_URL = "http://127.0.0.1:8001"

def login(username, password):
    resp = requests.post(f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_new_messages(token, conv_id, after_id):
    resp = requests.get(f"{BASE_URL}/messages/conversations/{conv_id}/messages",
        params={"after_id": after_id},
        headers={"Authorization": f"Bearer {token}"})
    return resp.json().get("messages", []) if resp.status_code == 200 else []

def send_message(token, conv_id, content, agent_id):
    requests.post(f"{BASE_URL}/messages/send",
        json={"conversation_id": conv_id, "content": content, "sender_agent_id": agent_id},
        headers={"Authorization": f"Bearer {token}"})

def report_work(token, conv_id, command, output, status, duration_ms, agent_id):
    requests.post(f"{BASE_URL}/work/report",
        json={"conversation_id": conv_id, "command": command, "output": output,
              "status": status, "duration_ms": duration_ms, "sender_agent_id": agent_id},
        headers={"Authorization": f"Bearer {token}"})

def execute_command(cmd, timeout=30):
    start = datetime.datetime.now()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        output = (result.stdout or "") + (result.stderr or "")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output, status = "命令执行超时", "timeout"
    except Exception as e:
        output, status = f"命令执行异常: {e}", "error"
    dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
    return output, status, dur

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python executor_v2.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    conv_id = int(sys.argv[3])
    commander_id, executor_id = sys.argv[4], sys.argv[5]

    token = login(username, password)
    print("执行者已登录，等待任务...")

    last_id = 0
    msgs = get_new_messages(token, conv_id, 0)
    if msgs:
        last_id = max(m["id"] for m in msgs)
    print(f"当前最新消息ID: {last_id}")

    while True:
        new_msgs = get_new_messages(token, conv_id, last_id)
        for msg in new_msgs:
            last_id = max(last_id, msg["id"])
            content = msg.get("content", "")
            if msg.get("sender_agent_id") != commander_id:
                continue
            if not content.startswith("[TASK]:"):
                continue

            try:
                task = json.loads(content[len("[TASK]:"):])
            except json.JSONDecodeError:
                print("任务格式解析失败，跳过")
                continue

            task_id = task.get("task_id")
            steps = task.get("steps", [])
            print(f"\n[执行者] 收到任务 {task_id}，共 {len(steps)} 步")

            for step in steps:
                step_id = step.get("step")
                desc = step.get("description", "")
                cmd = step.get("command", "")
                print(f"  步骤 {step_id}: {desc}")
                print(f"    命令: {cmd}")

                output, status, dur = execute_command(cmd)
                print(f"    结果: {status} ({dur}ms)")
                print(f"    输出: {output[:200]}")

                # 汇报步骤完成
                step_done = {
                    "task_id": task_id,
                    "step": step_id,
                    "description": desc,
                    "status": status,
                    "output": output[:500],
                    "duration_ms": dur
                }
                send_message(token, conv_id,
                    "[STEP_DONE]:" + json.dumps(step_done, ensure_ascii=False),
                    executor_id)

                # 记录到工作日志
                report_work(token, conv_id, cmd, output, status, dur, executor_id)

            print(f"[执行者] 任务 {task_id} 全部步骤完成")

        time.sleep(3)
