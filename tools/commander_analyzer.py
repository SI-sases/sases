import requests, time, json, sys

BASE_URL = "http://127.0.0.1:8001"

COMMANDER_SYSTEM_PROMPT = """
你是 SASES 指挥官。用户会给你一个任务，你需要拆解为可执行的 Windows CMD 命令序列。

规则：
1. 每个命令必须是单行的 Windows CMD 命令
2. 最多 5 步
3. 只输出 JSON 数组，格式：[{"step":1,"description":"...","command":"..."},...]
4. 不要输出任何其他文字，不要用 markdown 代码块
5. 禁止 uvicorn 等服务器启停命令
6. 如果任务模糊，输出：[{"step":1,"description":"任务模糊","command":"echo 请提供更具体的任务说明"}]
"""

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

def plan_task(token, user_text):
    """调 LLM 把用户任务拆解为步骤列表"""
    full_prompt = COMMANDER_SYSTEM_PROMPT + "\n\n用户任务：" + user_text
    resp = requests.post(f"{BASE_URL}/agent/chat",
        json={"query": full_prompt},
        headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        return None
    raw = resp.json().get("response", "").strip()
    # 清理 markdown
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    # 提取 JSON 数组
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        steps = json.loads(raw[start:end+1])
        if not isinstance(steps, list) or not steps:
            return None
        return steps
    except json.JSONDecodeError:
        return None

def summarize(token, user_text, results):
    """汇总执行结果"""
    result_text = "\n".join([f"步骤{r['step']}({r['description']}): {r['status']}" for r in results])
    prompt = f"用户任务：{user_text}\n\n执行结果：\n{result_text}\n\n请用一句话总结这次任务的结果。"
    resp = requests.post(f"{BASE_URL}/agent/chat",
        json={"query": prompt},
        headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json().get("response", "").strip()
    return "任务执行完成。"

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python commander_v2.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    conv_id = int(sys.argv[3])
    commander_id, executor_id = sys.argv[4], sys.argv[5]

    token = login(username, password)
    print("指挥官已登录，等待用户任务...")

    # 初始化：记录最新消息 ID
    last_id = 0
    msgs = get_new_messages(token, conv_id, 0)
    if msgs:
        last_id = max(m["id"] for m in msgs)
    print(f"当前最新消息ID: {last_id}")

    # 待完成的任务状态：{task_id: {"user_text":..., "steps":[...], "results":[], "done":set()}}
    pending = {}

    while True:
        new_msgs = get_new_messages(token, conv_id, last_id)
        for msg in new_msgs:
            last_id = max(last_id, msg["id"])
            content = msg.get("content", "")
            sender_agent = msg.get("sender_agent_id")

            # 1) 用户消息 → 拆解任务
            if msg.get("sender") == "user" and not sender_agent:
                user_text = content.strip()
                if not user_text:
                    continue
                print(f"[用户] {user_text[:80]}")
                steps = plan_task(token, user_text)
                if not steps:
                    send_message(token, conv_id, "[SUMMARY]:任务拆解失败，请重试。", commander_id)
                    continue
                task_id = f"t_{int(time.time())}"
                pending[task_id] = {"user_text": user_text, "steps": steps, "results": [], "done": set()}
                task_msg = "[TASK]:" + json.dumps({"task_id": task_id, "steps": steps}, ensure_ascii=False)
                send_message(token, conv_id, task_msg, commander_id)
                print(f"[指挥官] 已下发任务 {task_id}，共 {len(steps)} 步")

            # 2) 执行者汇报步骤完成
            elif sender_agent == executor_id and content.startswith("[STEP_DONE]:"):
                try:
                    data = json.loads(content[len("[STEP_DONE]:"):])
                except json.JSONDecodeError:
                    continue
                task_id = data.get("task_id")
                step_id = data.get("step")
                if task_id not in pending:
                    continue
                task = pending[task_id]
                if step_id in task["done"]:
                    continue
                task["done"].add(step_id)
                task["results"].append({
                    "step": step_id,
                    "description": data.get("description", ""),
                    "status": data.get("status", "unknown")
                })
                print(f"[执行者] 步骤 {step_id} 完成 ({data.get('status')})")

                # 3) 全部完成 → 汇总
                if len(task["done"]) == len(task["steps"]):
                    summary = summarize(token, task["user_text"], task["results"])
                    send_message(token, conv_id, f"[SUMMARY]:{summary}", commander_id)
                    print(f"[指挥官] 任务 {task_id} 完成，已汇总")
                    del pending[task_id]

        time.sleep(3)
