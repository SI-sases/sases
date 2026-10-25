# -*- coding: utf-8 -*-
import requests, time, json, sys, subprocess, datetime, re

BASE_URL = "http://127.0.0.1:8001"

# ========== 安全配置 ==========

ALLOWED_COMMANDS = {
    "dir", "ls", "tree",
    "type", "cat", "head", "tail",
    "findstr", "find", "grep", "where",
    "echo", "pwd", "cd", "whoami", "hostname",
    "wc",
}

DANGEROUS_CHARS = ['&', '<', '>', '^', '%', ';', '`', '$', '\n', '\r']

MAX_OUTPUT_LENGTH = 2000
DEFAULT_TIMEOUT = 30


def is_command_safe(cmd):
    if not cmd or not cmd.strip():
        return False, "命令为空"
    for ch in DANGEROUS_CHARS:
        if ch in cmd:
            return False, f"包含禁止字符: {repr(ch)}"
    parts = [p.strip() for p in cmd.split('|')]
    if any(not p for p in parts):
        return False, "存在空的管道段"
    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        base = tokens[0].lower()
        if '\\' in base or '/' in base:
            return False, f"命令含路径: {base}"
        if base.endswith('.exe') or base.endswith('.bat') or base.endswith('.cmd'):
            base = base.rsplit('.', 1)[0]
        if base not in ALLOWED_COMMANDS:
            return False, f"命令不在白名单: {base}"
    return True, ""


def smart_decode(raw_bytes):
    if not raw_bytes:
        return ""
    for enc in ["utf-8", "gbk", "latin-1"]:
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


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


def execute_command(cmd, timeout=DEFAULT_TIMEOUT):
    start = datetime.datetime.now()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout
        )
        output = smart_decode(result.stdout or b"") + smart_decode(result.stderr or b"")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output, status = f"命令执行超时（>{timeout}秒）", "timeout"
    except Exception as e:
        output, status = f"命令执行异常: {e}", "error"

    if len(output) > MAX_OUTPUT_LENGTH:
        output = output[:MAX_OUTPUT_LENGTH] + f"\n... (已截断，原长 {len(output)} 字符)"

    dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
    return output, status, dur


def call_harness(token, module_id, params):
    """调用后端 Harness 接口"""
    start = datetime.datetime.now()
    try:
        resp = requests.post(
            f"{BASE_URL}/harness/execute",
            json={"module_id": module_id, "params": params},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
        if resp.status_code != 200:
            return f"Harness 调用失败 ({resp.status_code}): {resp.text[:200]}", "failed", dur

        data = resp.json()
        result = data.get("result", {})
        if isinstance(result, dict):
            if result.get("success") is False:
                return f"Harness 失败: {result.get('error', '')}", "failed", dur
            output = result.get("text") or json.dumps(result, ensure_ascii=False)
            return output[:MAX_OUTPUT_LENGTH], "success", dur
        return str(result)[:MAX_OUTPUT_LENGTH], "success", dur
    except Exception as e:
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
        return f"Harness 调用异常: {e}", "error", dur


def substitute_placeholders(cmd, previous_outputs):
    if not previous_outputs:
        return cmd

    def replace_match(match):
        step_num = int(match.group(1))
        if step_num in previous_outputs:
            output = previous_outputs[step_num]
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.count("�") > 2:
                    continue
                if any(c in line for c in ["\\", "/", ":"]) and len(line) > 3:
                    return line
                return line
        return match.group(0)

    cmd = re.sub(r'\{\{step(\d+)\}\}', replace_match, cmd)
    cmd = re.sub(r'\{step(\d+)\}', replace_match, cmd)
    return cmd


def handle_task(token, conv_id, executor_id, task):
    task_id = task.get("task_id")
    steps = task.get("steps", [])
    print(f"\n[执行者] 收到任务 {task_id}，共 {len(steps)} 步")

    previous_outputs = {}

    for step in steps:
        step_id = step.get("step")
        desc = step.get("description", "")
        step_type = step.get("type", "command")

        if step_type == "harness":
            # ========== Harness 步骤 ==========
            module_id = step.get("module_id", "")
            params = step.get("params", {})
            print(f"  步骤 {step_id}: {desc}")
            print(f"    [Harness] {module_id}({params})")

            output, status, dur = call_harness(token, module_id, params)
            print(f"    结果: {status} ({dur}ms)")
            print(f"    输出: {output[:200]}")
        else:
            # ========== 命令步骤 ==========
            cmd_raw = step.get("command", "")
            cmd = substitute_placeholders(cmd_raw, previous_outputs)

            print(f"  步骤 {step_id}: {desc}")

            if "{{step" in cmd or "{step" in cmd:
                print(f"    ⚠️ 占位符未替换，依赖步骤失败，跳过本步")
                step_done = {
                    "task_id": task_id,
                    "step": step_id,
                    "description": desc,
                    "status": "skipped",
                    "output": "跳过：依赖的步骤失败（占位符未替换）",
                    "duration_ms": 0
                }
                send_message(token, conv_id,
                    "[STEP_DONE]:" + json.dumps(step_done, ensure_ascii=False),
                    executor_id)
                continue

            if cmd != cmd_raw:
                print(f"    原命令: {cmd_raw}")
                print(f"    替换后: {cmd}")

            is_safe, reason = is_command_safe(cmd)
            if not is_safe:
                print(f"    ⛔ 命令被拒绝: {reason}")
                output = f"命令被安全策略拒绝: {reason}"
                status = "blocked"
                dur = 0
            else:
                print(f"    命令: {cmd}")
                output, status, dur = execute_command(cmd)
                print(f"    结果: {status} ({dur}ms)")
                print(f"    输出: {output[:200]}")

            if status == "success":
                previous_outputs[step_id] = output

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

    print(f"[执行者] 任务 {task_id} 全部步骤完成")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python executor_v2.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    conv_id = int(sys.argv[3])
    commander_id, executor_id = sys.argv[4], sys.argv[5]

    token = login(username, password)
    print("执行者已登录，等待任务...")
    print(f"安全策略: 白名单 {len(ALLOWED_COMMANDS)} 条命令，禁止字符 {len(DANGEROUS_CHARS)} 个")
    print(f"支持步骤类型: command / harness")

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

            if content.startswith("[TASK]:"):
                try:
                    task = json.loads(content[len("[TASK]:"):])
                except json.JSONDecodeError:
                    print("任务格式解析失败，跳过")
                    continue
                handle_task(token, conv_id, executor_id, task)

            elif content.startswith("[RETRY_TASK]:"):
                try:
                    task = json.loads(content[len("[RETRY_TASK]:"):])
                except json.JSONDecodeError:
                    print("重试任务格式解析失败，跳过")
                    continue
                print("\n[执行者] 收到重试任务")
                handle_task(token, conv_id, executor_id, task)

        time.sleep(3)
