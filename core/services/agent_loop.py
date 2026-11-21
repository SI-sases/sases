# core/services/agent_loop.py
# -*- coding: utf-8 -*-
"""A1: append-only agent loop（flag 控制，默认仍走 fast_agent 旧路径）。"""
import asyncio
import json

from core import tool_gateway
from core.services import agent_memory
from core.services.agent_policy import before_tool, after_tool, WRITE_TOOLS, ApprovalRequired
from core.services.swarm.llm_parser import client, MODEL
from core.services.swarm.prompts import BASE_SYSTEM, BASE_PREFIX_HASH


def _tool_schemas(allowed_tool_ids=None):
    from core.harness_runtime import harness_runtime
    from .fast_agent import tool_schema
    tools = sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")
    if allowed_tool_ids is not None:
        allow = set(str(x) for x in allowed_tool_ids)
        tools = [t for t in tools if getattr(t, "module_id", "") in allow]
    return [tool_schema(t) for t in tools if getattr(t, "module_id", "")]


async def run(user_id, conversation_id, goal, allowed_tool_ids=None, max_steps=8, run_id=None, mode="fast"):
    if not conversation_id:
        return {"status": "error", "content": "缺少会话", "steps": 0, "history": []}

    try:
        from .agent_compact import maybe_compact
        await maybe_compact(conversation_id, user_id)
    except Exception as _e_cp:
        print("[compact] 跳过: " + str(_e_cp))
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
            content = (msg.content or "").strip()
            review = ""
            _need_review = (mode == "strict"
                            and any(h.get("tool") in WRITE_TOOLS for h in used))
            if _need_review:
                try:
                    messages.append({"role": "user", "content":
                                     "请审核上面的执行结果。只回答 PASS，或列出具体问题（不超过 5 条）。"})
                    rr = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=MODEL, messages=messages, temperature=0.2, max_tokens=800,
                        extra_body={"thinking": {"type": "disabled"}},
                    )
                    review = (rr.choices[0].message.content or "").strip()
                    agent_memory.append(conversation_id, "assistant", review)
                except Exception as e:
                    print("[strict] 审核失败: " + str(e))
            return {"status": "ok", "content": content, "steps": step,
                    "history": used, "review": review}

        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                await before_tool(user_id, conversation_id, run_id, step, name, args)
            except ApprovalRequired as _ar:
                if run_id:
                    try:
                        from core.db import db_cursor
                        with db_cursor(commit=True) as _c_ap:
                            _c_ap.execute("UPDATE supervisor_runs SET status='awaiting_approval' WHERE id=?", (run_id,))
                    except Exception:
                        pass
                return {"status": "awaiting_approval", "content": "等待审批：" + str(_ar.tool),
                        "step": _ar.step, "tool": _ar.tool, "steps": step, "history": used}
            try:
                r = await tool_gateway.invoke_tool_async(name, args)
                ok = bool(getattr(r, "success", False))
                text = str(getattr(r, "result", "") or getattr(r, "error", ""))[:4000]
            except Exception as e:
                ok, text = False, "ERROR: " + str(e)
            used.append({"step": step, "tool": name, "args": args, "ok": ok})
            try:
                from . import tool_usage_service
                tool_usage_service.record(user_id, name, ok)
            except Exception:
                pass
            agent_memory.append(conversation_id, "tool", text, tool_call_id=c.id)
            messages.append({"role": "tool", "tool_call_id": c.id, "content": text})
            await after_tool(user_id, conversation_id, run_id, step, name, args, ok, text)

            # A3: strict 写后确定性校验（不另起 prompt）
            if mode == "strict" and name in WRITE_TOOLS and isinstance(args, dict):
                _fp = str(args.get("file_path") or "")
                if _fp.endswith(".py"):
                    try:
                        _vr = await tool_gateway.invoke_tool_async("verify_syntax", {"file_path": _fp})
                        used.append({"step": step, "tool": "verify_syntax", "ok": bool(getattr(_vr, "success", False))})
                    except Exception as e:
                        print("[strict] verify_syntax 失败: " + str(e))

    return {"status": "max_steps", "content": "达到步数上限，未完成任务。", "steps": max_steps, "history": used}
