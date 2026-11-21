# core/services/agent_loop.py
# -*- coding: utf-8 -*-
"""A1: append-only agent loop（flag 控制，默认仍走 fast_agent 旧路径）。"""
import asyncio
import json

from core import tool_gateway
from core.services import agent_memory
from core.services.agent_policy import before_tool, after_tool
from core.services.swarm.llm_parser import client, MODEL
from core.services.swarm.prompts import BASE_SYSTEM, BASE_PREFIX_HASH


def _tool_schemas(allowed_tool_ids=None):
    from core.harness_runtime import harness_runtime
    from .fast_agent import tool_schema
    tools = sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")
    if allowed_tool_ids:
        allow = set(str(x) for x in allowed_tool_ids)
        tools = [t for t in tools if getattr(t, "module_id", "") in allow]
    return [tool_schema(t) for t in tools if getattr(t, "module_id", "")]


async def run(user_id, conversation_id, goal, allowed_tool_ids=None, max_steps=8, run_id=None):
    if not conversation_id:
        return {"status": "error", "content": "缺少会话", "steps": 0, "history": []}

    agent_memory.backfill(conversation_id)
    hist = agent_memory.history(conversation_id)
    if not hist or str(hist[-1].get("content") or "") != str(goal):
        agent_memory.append(conversation_id, "user", goal)
        hist = agent_memory.history(conversation_id)

    messages = [{"role": "system", "content": BASE_SYSTEM}] + hist
    schemas = _tool_schemas(allowed_tool_ids)
    used = []

    for step in range(1, max_steps + 1):
        try:
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=MODEL, messages=messages, tools=schemas or None,
                tool_choice="auto" if schemas else None,
                temperature=0.3, max_tokens=2000,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as e:
            return {"status": "error", "content": "LLM 调用失败: " + str(e), "steps": step, "history": used}

        try:
            from .llm_usage_service import record_from_response
            record_from_response(resp, user_id=user_id, conversation_id=conversation_id,
                                 purpose="loop", prefix_hash=BASE_PREFIX_HASH)
        except Exception:
            pass

        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        assistant_tool_calls = [{
            "id": c.id, "type": "function",
            "function": {"name": c.function.name, "arguments": c.function.arguments},
        } for c in calls]
        agent_memory.append(conversation_id, "assistant", msg.content or "",
                            tool_calls=assistant_tool_calls or None)
        messages.append({"role": "assistant", "content": msg.content or "",
                         **({"tool_calls": assistant_tool_calls} if assistant_tool_calls else {})})

        if not calls:
            return {"status": "ok", "content": (msg.content or "").strip(),
                    "steps": step, "history": used}

        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            await before_tool(user_id, conversation_id, run_id, step, name, args)
            try:
                r = await tool_gateway.invoke_tool_async(name, args)
                ok = bool(getattr(r, "success", False))
                text = str(getattr(r, "result", "") or getattr(r, "error", ""))[:4000]
            except Exception as e:
                ok, text = False, "ERROR: " + str(e)
            used.append({"step": step, "tool": name, "args": args, "ok": ok})
            agent_memory.append(conversation_id, "tool", text, tool_call_id=c.id)
            messages.append({"role": "tool", "tool_call_id": c.id, "content": text})
            await after_tool(user_id, conversation_id, run_id, step, name, args, ok, text)

    return {"status": "max_steps", "content": "达到步数上限，未完成任务。", "steps": max_steps, "history": used}
