# core/services/work_service.py
# 指令模式（原工作模式）核心服务
import asyncio
import os
import json
import shlex
import subprocess
from datetime import datetime, date
from typing import Optional
from ..db import db_cursor
from . import memory_service, credit_service
from .. import safety_scan
from core.harness_runtime import harness_runtime

# 积分开关
WORK_MODE_CREDIT_ENABLED = True
WORK_MODE_CREDIT_PER_TASK = 2
FREE_DAILY_TASKS = 3

# 自动生成 Harness 开关（关闭）
AUTO_GENERATE_HARNESS = False

# SASES 助手默认 ID
SASES_ASSISTANT_AGENT_ID = "sases_assistant"

# Harness 模块输出目录
HARNESS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'harness_modules')

# 允许执行的只读命令白名单
ALLOWED_COMMANDS = {
    "dir", "ls", "type", "cat", "echo", "pwd", "whoami", "hostname"
}

FORBIDDEN_CHARS = set("&|;><`$\\\n\r\t")


def is_command_allowed(command: str) -> bool:
    if not command or not command.strip():
        return False, "命令不能为空"
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"命令解析失败: {e}"
    if not tokens:
        return False, "命令为空"
    if tokens[0].lower() not in ALLOWED_COMMANDS:
        return False, f"命令 '{tokens[0]}' 不在允许列表中"
    for token in tokens[1:]:
        if any(c in FORBIDDEN_CHARS for c in token):
            return False, f"参数包含危险字符: {token}"
    return True, ""


def execute_command(command: str, timeout: int = 30) -> dict:
    start = datetime.now()
    allowed, msg = is_command_allowed(command)
    if not allowed:
        return {
            "output": msg,
            "status": "blocked",
            "duration_ms": 0
        }

    try:
        tokens = shlex.split(command)
        if os.name == 'nt':
            result = subprocess.run(
                ["cmd.exe", "/d", "/c"] + tokens,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False
            )
        else:
            result = subprocess.run(
                tokens,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False
            )
        output = (result.stdout or "") + (result.stderr or "")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output = "命令执行超时"
        status = "timeout"
    except Exception as e:
        output = f"命令执行异常: {str(e)}"
        status = "error"

    duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    max_output = 5000
    if len(output) > max_output:
        output = output[:max_output] + "\n...[输出截断]"
    return {
        "output": output,
        "status": status,
        "duration_ms": duration_ms
    }


def write_work_log(user_id: int, command: str, output: str, status: str, duration_ms: int, agent_id: Optional[str] = None) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO work_logs (user_id, agent_id, command, output, status, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, agent_id, command, output, status, duration_ms))
        return cur.lastrowid


def get_today_work_count(user_id: int) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM work_logs
            WHERE user_id=? AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["cnt"] if row else 0


def insert_assistant_message(conversation_id: int, content: str, sender_agent_id: str = None):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO messages (conversation_id, sender, content, sender_agent_id)
            VALUES (?, 'assistant', ?, ?)
        """, (conversation_id, content, sender_agent_id))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), conversation_id))


def insert_user_message(conversation_id: int, content: str, sender_agent_id: str = None):
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("""
                INSERT INTO messages (conversation_id, sender, content, sender_agent_id)
                VALUES (?, 'user', ?, ?)
            """, (conversation_id, content, sender_agent_id))
        else:
            cur.execute("""
                INSERT INTO messages (conversation_id, sender, content)
                VALUES (?, 'user', ?)
            """, (conversation_id, content))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), conversation_id))


def create_conversation_if_needed(user_id: int, conversation_id: Optional[int]) -> int:
    if conversation_id is not None:
        return conversation_id
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                    (user_id, "指令模式会话"))
        return cur.lastrowid


def generate_harness_from_log(log_id: int, command: str, output: str, status: str) -> str:
    """根据日志生成一个 Harness 模块，保存到本地。返回模块目录名。"""
    safe_cmd = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in command)[:20]
    module_id = f"auto_{log_id}_{safe_cmd}"
    module_dir = os.path.join(HARNESS_DIR, module_id)

    if os.path.exists(module_dir):
        return module_id

    os.makedirs(module_dir, exist_ok=True)

    manifest = {
        "id": module_id,
        "name": f"Auto Harness - {command[:30]}",
        "description": f"自动生成的 Harness 模块，基于工作日志 #{log_id}。状态: {status}",
        "version": "1.0.0",
        "capabilities": ["command_result"],
        "permissions": [],
        "entrypoint": "main.py",
        "icon": None,
        "node_type": "harness"
    }
    with open(os.path.join(module_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    main_content = f'''# Auto-generated Harness module from work log #{log_id}
def run(params=None):
    """返回原始命令输出，供后续参考"""
    command = {json.dumps(command, ensure_ascii=False)}
    output = {json.dumps(output[:2000], ensure_ascii=False)}
    status = {json.dumps(status, ensure_ascii=False)}
    return {{
        "command": command,
        "status": status,
        "output": output
    }}
'''
    with open(os.path.join(module_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(main_content)

    return module_id


def try_reload_harness() -> dict:
    """尝试重新加载 Harness 模块，返回结果"""
    try:
        return harness_runtime.reload_modules()
    except Exception as e:
        return {"success": False, "message": str(e)}


async def execute_work_command(
    user_id: int,
    conversation_id: Optional[int],
    command: str,
    sender_agent_id: Optional[str] = None,
    timeout: int = 30
) -> dict:
    conversation_id = create_conversation_if_needed(user_id, conversation_id)
    insert_user_message(conversation_id, command, sender_agent_id)

    risk = safety_scan.analyze_risk(command)
    if risk["level"] == "high":
        result = {
            "output": risk["message"],
            "status": "blocked",
            "duration_ms": 0
        }
    else:
        result = await asyncio.to_thread(execute_command, command, timeout)

    log_id = write_work_log(
        user_id=user_id,
        command=command,
        output=result["output"],
        status=result["status"],
        duration_ms=result["duration_ms"],
        agent_id=sender_agent_id
    )

    memory_service.remember(
        user_id=user_id,
        memory_type="task_result",
        content=f"命令: {command}\n状态: {result['status']}\n输出摘要: {result['output'][:200]}",
        agent_id=sender_agent_id,
        tags="work_mode,command",
        importance=0.6,
        full_data={
            "log_id": log_id,
            "command": command,
            "status": result["status"],
            "duration_ms": result["duration_ms"]
        }
    )

    credit_deducted = False
    credit_remaining = None
    if WORK_MODE_CREDIT_ENABLED and result["status"] not in ("blocked", "timeout", "error"):
        today_count = get_today_work_count(user_id)
        if today_count > FREE_DAILY_TASKS:
            try:
                credit_service.add_credit(
                    user_id,
                    -WORK_MODE_CREDIT_PER_TASK,
                    "指令模式任务循环",
                    f"执行命令: {command}"
                )
                credit_deducted = True
                credit_remaining = credit_service.get_balance(user_id)
            except Exception:
                credit_deducted = False

    fee_msg = " (已扣除2积分)" if credit_deducted else ""
    log_content = (
        f"📋 工作日志 #{log_id}{fee_msg}\n"
        f"命令: {command}\n"
        f"状态: {result['status']}\n"
        f"耗时: {result['duration_ms']} ms\n"
        f"输出:\n{result['output'][:1000]}"
    )
    insert_assistant_message(conversation_id, log_content, SASES_ASSISTANT_AGENT_ID)

    # 生成 Harness 并自动重新加载（已关闭自动生成）
    harness_module_id = None
    if AUTO_GENERATE_HARNESS and result["status"] not in ("blocked", "timeout", "error"):
        try:
            harness_module_id = await asyncio.to_thread(
                generate_harness_from_log, log_id, command, result["output"], result["status"]
            )
            reload_result = await asyncio.to_thread(try_reload_harness)
            if reload_result.get("added_count", 0) > 0:
                print(f"[Harness] 新增模块: {reload_result['added']}")
        except Exception as e:
            print(f"[Harness] 生成或加载异常: {e}")

    return {
        "log_id": log_id,
        "conversation_id": conversation_id,
        "command": command,
        "output": result["output"],
        "status": result["status"],
        "duration_ms": result["duration_ms"],
        "credit_deducted": credit_deducted,
        "credit_remaining": credit_remaining,
        "harness_module_id": harness_module_id
    }


async def report_work_result(
    user_id: int,
    conversation_id: Optional[int],
    command: str,
    output: str,
    status: str,
    duration_ms: int,
    sender_agent_id: Optional[str] = None
) -> dict:
    conversation_id = create_conversation_if_needed(user_id, conversation_id)
    insert_user_message(conversation_id, command, sender_agent_id)

    log_id = write_work_log(
        user_id=user_id,
        command=command,
        output=output,
        status=status,
        duration_ms=duration_ms,
        agent_id=sender_agent_id
    )

    memory_service.remember(
        user_id=user_id,
        memory_type="task_result",
        content=f"命令: {command}\n状态: {status}\n输出摘要: {output[:200]}",
        agent_id=sender_agent_id,
        tags="work_mode,command",
        importance=0.6,
        full_data={
            "log_id": log_id,
            "command": command,
            "status": status,
            "duration_ms": duration_ms
        }
    )

    log_content = (
        f"📋 工作日志 #{log_id}\n"
        f"命令: {command}\n"
        f"状态: {status}\n"
        f"耗时: {duration_ms} ms\n"
        f"输出:\n{output[:1000]}"
    )
    insert_assistant_message(conversation_id, log_content, SASES_ASSISTANT_AGENT_ID)

    if AUTO_GENERATE_HARNESS:
        try:
            await asyncio.to_thread(generate_harness_from_log, log_id, command, output, status)
            await asyncio.to_thread(try_reload_harness)
        except Exception:
            pass

    return {
        "log_id": log_id,
        "conversation_id": conversation_id,
        "status": status,
        "message": "工作结果已记录并通知"
    }


def get_work_logs(user_id: int, limit: int = 50) -> list:
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM work_logs WHERE user_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]
