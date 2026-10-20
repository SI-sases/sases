# core/services/commander_service.py
import asyncio
import json
import re
import openai
from datetime import datetime
from typing import Optional, List, Dict, Any

from .. import config
from ..db import db_cursor
from . import work_service
from core.services import executor_service
from core.harness_runtime import harness_runtime

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=40,
    max_retries=2
)

MODEL = config.MODEL_NAME

# 允许的命令白名单提示
ALLOWED_COMMANDS_HINT = "dir, ls, type, cat, echo, pwd, whoami, hostname"


async def execute_commander_task(
    user_id: int,
    conversation_id: Optional[int],
    task_text: str,
    sender_agent_id: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """指挥官任务：将自然语言任务拆解为命令或 Harness 工具调用"""
    # 1. 查询可用的 Harness 工具
    available_tools = _get_available_tools()

    # 2. 调用模型生成执行计划
    plan = await _generate_plan(task_text, available_tools)

    if not plan:
        hint_msg = (
            f"⚠️ 无法将任务「{task_text}」拆解为可执行命令。\n\n"
            f"请尝试更具体的任务，例如：\n"
            f"· 任务：列出当前目录文件\n"
            f"· 任务：显示当前用户名\n"
            f"· 任务：查看系统主机名\n\n"
            f"当前允许的命令：{', '.join(executor_service.ALLOWED_COMMANDS)}"
        )
        if conversation_id:
            work_service.insert_assistant_message(conversation_id, hint_msg, work_service.SASES_ASSISTANT_AGENT_ID)
        return {
            "status": "no_commands",
            "message": hint_msg,
            "results": []
        }

    # 3. 按计划执行
    results = []
    for step in plan:
        if step["type"] == "harness":
            res = await _execute_harness_step(step)
        else:
            res = await work_service.execute_work_command(
                user_id=user_id,
                conversation_id=conversation_id,
                command=step["command"],
                sender_agent_id=sender_agent_id,
                timeout=timeout
            )
        results.append(res)
        if res.get("status") in ("blocked", "error"):
            break

    summary = {
        "task": task_text,
        "commands_executed": len(results),
        "success_count": sum(1 for r in results if r.get("status") in ("success", "harness_success")),
        "results": results
    }

    if conversation_id:
        summary_text = (
            f"📋 指挥官任务完成\n"
            f"任务: {task_text}\n"
            f"执行步骤: {len(results)} 条\n"
            f"成功: {summary['success_count']} 条"
        )
        work_service.insert_assistant_message(conversation_id, summary_text, work_service.SASES_ASSISTANT_AGENT_ID)

    return summary


def _get_available_tools() -> List[Dict[str, Any]]:
    """获取所有可用的 Harness 工具（仅安全权限）"""
    tools = []
    for tool in harness_runtime.list_tools():
        # 只返回没有危险权限的工具
        if any(p in harness_runtime.__class__.__dict__.get("DANGEROUS_PERMISSIONS", set()) for p in tool.permissions):
            continue
        tools.append({
            "module_id": tool.module_id,
            "name": tool.name,
            "description": tool.description,
            "capabilities": tool.capabilities
        })
    return tools


async def _generate_plan(task_text: str, available_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    调用模型生成执行计划。
    返回格式：
    [
        {"type": "command", "command": "dir"},
        {"type": "harness", "module_id": "auto_1_dir"},
        ...
    ]
    """
    tools_desc = "无可用工具"
    if available_tools:
        tools_lines = []
        for t in available_tools[:10]:  # 最多展示 10 个
            tools_lines.append(f"- {t['module_id']}: {t['name']} — {t['description'][:60]}")
        tools_desc = "\n".join(tools_lines)

    prompt = f"""你是一个 Windows CMD 系统指挥官。请将用户的自然语言任务拆解为可执行的步骤。

用户任务：
{task_text}

可用命令（只能使用这些）：
- dir：列出当前目录文件
- ls：同上（兼容 Unix）
- type <文件>：显示文件内容
- cat <文件>：同上
- echo <文本>：输出文本
- pwd：显示当前路径
- whoami：显示当前用户
- hostname：显示主机名

可用的 Harness 工具：
{tools_desc}

规则：
1. 每个步骤单独一行，格式为以下两种之一：
   - `CMD: <命令>` （使用 CMD 命令）
   - `HARNESS: <module_id>` （使用 Harness 工具）
2. 只能使用上述命令或工具。
3. 不要使用 && 、| 、> 、< 等组合符号。
4. 最多生成 5 个步骤。
5. 如果任务模糊无法拆解，返回空行。

例如：
任务：列出当前目录并显示当前用户
CMD: dir
CMD: whoami

任务：使用已有的 dir 工具列出文件
HARNESS: auto_1_dir

请输出步骤："""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)

        lines = [line.strip() for line in raw.split('\n') if line.strip()]

        plan = []
        for line in lines:
            if line.startswith("CMD:") or line.startswith("cmd:"):
                cmd = line.split(":", 1)[1].strip()
                # 校验命令是否在白名单
                parts = cmd.split()
                if parts and parts[0].lower() in work_service.ALLOWED_COMMANDS:
                    plan.append({"type": "command", "command": cmd})
            elif line.startswith("HARNESS:") or line.startswith("harness:"):
                module_id = line.split(":", 1)[1].strip()
                # 校验工具是否存在
                if harness_runtime.get_tool(module_id):
                    plan.append({"type": "harness", "module_id": module_id})

        return plan[:5]
    except Exception as e:
        print(f"生成执行计划失败: {e}")
        return []


async def _execute_harness_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """执行一个 Harness 工具步骤"""
    module_id = step["module_id"]
    try:
        response = await asyncio.to_thread(harness_runtime.invoke_tool, module_id, {})
        if response.success:
            result = response.result
            if isinstance(result, dict):
                output = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                output = str(result)
            return {
                "status": "harness_success",
                "module_id": module_id,
                "command": f"[Harness] {module_id}",
                "output": output[:2000],
                "duration_ms": 0
            }
        else:
            return {
                "status": "error",
                "module_id": module_id,
                "command": f"[Harness] {module_id}",
                "output": response.error or "工具执行失败",
                "duration_ms": 0
            }
    except Exception as e:
        return {
            "status": "error",
            "module_id": module_id,
            "command": f"[Harness] {module_id}",
            "output": f"工具调用异常: {str(e)}",
            "duration_ms": 0
        }
