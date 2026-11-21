# core/services/fast_agent.py
# -*- coding: utf-8 -*-
"""B1 fast 模式：单 Agent 原生 tool calling，最多 N 步。"""
import asyncio
import json

from core import tool_gateway
from core.services.swarm.llm_parser import client, MODEL
from core.services.swarm.prompts import COMMANDER_SYSTEM_PROMPT

_TYPE_MAP = {
    "int": "integer", "integer": "integer", "float": "number", "number": "number",
    "bool": "boolean", "boolean": "boolean", "string": "string",
    "array": "array", "object": "object",
}


def tool_schema(t) -> dict:
    props = {}
    for k, v in (getattr(t, "params", None) or {}).items():
        if not isinstance(v, dict):
            continue
        props[k] = {
            "type": _TYPE_MAP.get(str(v.get("type") or "string").lower(), "string"),
            "description": str(v.get("desc") or "")[:120],
        }
    return {
        "type": "function",
        "function": {
            "name": getattr(t, "module_id", "") or "",
            "description": (getattr(t, "description", "") or "")[:200],
            "parameters": {"type": "object", "properties": props},
        },
    }


async def run_fast(user_id: int, conversation_id: int, goal: str,
                   allowed_tool_ids=None, max_steps: int = 8) -> dict:
    from core.harness_runtime import harness_runtime
    tools = sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")
    if allowed_tool_ids:
        allow = set(str(x) for x in allowed_tool_ids)
        tools = [t for t in tools if getattr(t, "module_id", "") in allow]
    schemas = [tool_schema(t) for t in tools if getattr(t, "module_id", "")]

    system = (COMMANDER_SYSTEM_PROMPT
              + "\n\n【fast 模式】直接用工具完成任务；能一步完成就不要多步；"
                "写文件后必须 file_read 验证；完成后用中文给出结果，不要输出 JSON。")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": goal},
    ]
    history = []

    for step in range(1, max_steps + 1):
        try:
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=MODEL,
                messages=messages,
                tools=schemas or None,
                tool_choice="auto" if schemas else None,
                temperature=0.3,
                max_tokens=2000,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as e:
            return {"status": "error", "content": "LLM 调用失败: " + str(e), "steps": step, "history": history}

        msg = resp.choices[0].message
        try:
            from .llm_usage_service import record_from_response
            record_from_response(resp, user_id=user_id, conversation_id=conversation_id, purpose="fast")
        except Exception as _e_u:
            print("[usage] fast 记录失败: " + str(_e_u))
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            return {"status": "ok", "content": (msg.content or "").strip(), "steps": step, "history": history}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{
                "id": c.id, "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments},
            } for c in calls],
        })

        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                r = await tool_gateway.invoke_tool_async(name, args)
                text = str(r.result)[:4000] if getattr(r, "success", False) else ("ERROR: " + str(getattr(r, "error", "")))
            except Exception as e:
                text = "ERROR: " + str(e)
            history.append({"step": step, "tool": name, "args": args, "ok": not text.startswith("ERROR")})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": text})

    return {"status": "max_steps", "content": "达到步数上限，未完成任务。", "steps": max_steps, "history": history}
