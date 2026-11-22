# core/services/agent_loop.py
# -*- coding: utf-8 -*-
"""A1: append-only agent loop（flag 控制，默认仍走 fast_agent 旧路径）。"""
import asyncio
import json
import os

from core import tool_gateway
from core.services import agent_memory
from core.services import token_meter, tool_pruner
from core.services.agent_policy import before_tool, after_tool, WRITE_TOOLS, ApprovalRequired
from core.services.swarm.llm_parser import client, MODEL
from core.services.swarm.prompts import BASE_SYSTEM, BASE_PREFIX_HASH


def _tool_schemas(allowed_tool_ids=None):
    from core.harness_runtime import harness_runtime
    from .fast_agent import tool_schema
    from .tool_visibility import visible
    tools = sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")
    if allowed_tool_ids is not None:
        allow = set(str(x) for x in allowed_tool_ids)
        tools = [t for t in tools if getattr(t, "module_id", "") in allow]
    tools = visible(tools)
    return [tool_schema(t) for t in tools if getattr(t, "module_id", "")]
    return [tool_schema(t) for t in tools if getattr(t, "module_id", "")]


async def run(user_id, conversation_id, goal, allowed_tool_ids=None, max_steps=8, run_id=None, mode="fast", resume=False, supervisor_id=None, on_event=None):
    if not conversation_id:
        return {"status": "error", "content": "缺少会话", "steps": 0, "history": []}

    try:
        from .agent_compact import maybe_compact
        await maybe_compact(conversation_id, user_id)
    except Exception as _e_cp:
        print("[compact] 跳过: " + str(_e_cp))
    agent_memory.backfill(conversation_id)
    hist = agent_memory.history(conversation_id)
    if not resume:
        if not hist or str(hist[-1].get("content") or "") != str(goal):
            agent_memory.append(conversation_id, "user", goal)
            hist = agent_memory.history(conversation_id)

    messages = [{"role": "system", "content": BASE_SYSTEM}] + hist
    try:
        from .agent_context import build_runtime_context
        _runtime = build_runtime_context(user_id, conversation_id, goal, mode)
        if _runtime:
            if messages and messages[-1].get("role") == "user":
                messages = messages[:-1] + [{"role": "user", "content": _runtime}, messages[-1]]
            else:
                messages.append({"role": "user", "content": _runtime})
    except Exception as _e_rc:
        print("[context] runtime 注入失败: " + str(_e_rc))
    schemas = _tool_schemas(allowed_tool_ids)
    used = []
    _dirty_files = set()
    _verified_files = set()

    for step in range(1, max_steps + 1):
        if step > 1:
            try:
                if await maybe_compact(conversation_id, user_id):
                    messages = [{"role": "system", "content": BASE_SYSTEM}] + agent_memory.history(conversation_id)
                    print("[ctx] compacted mid-run, rebuilt messages")
            except Exception as _e_mid:
                print("[ctx] mid-run compact 失败: " + str(_e_mid))
        req_messages = messages
        pruned_count = 0
        if os.getenv("SASES_TOOL_PRUNER", "1") != "0":
            try:
                req_messages, pruned_count, freed = tool_pruner.prune_messages(messages)
                if pruned_count:
                    print("[ctx] pruned " + str(pruned_count) + " tool results, ~" + str(freed) + " tokens")
            except Exception as e:
                print("[ctx] pruner 失败: " + str(e))
        try:
            est = token_meter.measure(req_messages, tools=schemas)
            if est["total"] > 60000 or pruned_count:
                print("[ctx] estimated tokens=" + str(est["total"]) +
                      " messages=" + str(est["messages"]) + " tools=" + str(est["tools"]))
        except Exception:
            pass
        try:
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=MODEL, messages=req_messages, tools=schemas or None,
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

        if not calls:
            raw = (msg.content or "").strip()
            try:
                from .agent_question_service import parse as _ask_parse, create as _ask_create
                content, _question = _ask_parse(raw)
            except Exception:
                content, _question = raw, None
            content = content or raw
            agent_memory.append(conversation_id, "assistant", content)
            messages.append({"role": "assistant", "content": content})
            if _question:
                if not run_id:
                    try:
                        from core.db import db_cursor
                        with db_cursor(commit=True) as _c_q:
                            _c_q.execute(
                                "INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) "
                                "VALUES (?,?,?,?,'waiting_user',0,10,'[]','unknown')",
                                (user_id, conversation_id, supervisor_id or "sases_assistant", str(goal or "")),
                            )
                            run_id = _c_q.lastrowid
                    except Exception as _e_qr:
                        print("[ask_user] 创建 run 失败: " + str(_e_qr))
                qid = _ask_create(conversation_id, _question, run_id)
                try:
                    from ..api_routes.ws_routes import broadcast_to_user
                    await broadcast_to_user(user_id, {
                        "type": "sases_ask_user",
                        "question_id": qid,
                        "conversation_id": conversation_id,
                        "question": _question,
                    })
                except Exception as e:
                    print("[ask_user] 广播失败: " + str(e))
                return {"status": "awaiting_user", "content": content,
                        "question": _question, "question_id": qid, "run_id": run_id,
                        "steps": step, "history": used}
            # 最终门禁前重新读盘验证，不能只信任写入时的自检结果
            if mode == "strict" and _dirty_files:
                for _fp in list(_dirty_files):
                    try:
                        _vr2 = await tool_gateway.invoke_tool_async("verify_syntax", {"file_path": _fp})
                        if bool(getattr(_vr2, "success", False)):
                            _verified_files.add(_fp)
                        else:
                            _verified_files.discard(_fp)
                    except Exception:
                        _verified_files.discard(_fp)
            _unverified = _dirty_files - _verified_files
            if mode == "strict" and _unverified:
                _gate = ("[自检未通过] 以下文件已修改但没有通过 verify_syntax：\n- "
                         + "\n- ".join(sorted(_unverified))
                         + "\n请修复后重新运行 verify_syntax，修复前不要结束任务。")
                messages.append({"role": "user", "content": _gate})
                agent_memory.append(conversation_id, "user", _gate)
                if step < max_steps:
                    continue
                return {"status": "verification_failed", "content": _gate,
                        "steps": step, "history": used}
            review = ""
            _need_review = (mode == "strict"
                            and any(h.get("tool") in WRITE_TOOLS for h in used))
            if _need_review:
                try:
                    _rev_messages = tool_pruner.prune_messages(messages)[0]
                    if len(_rev_messages) > 21:
                        _rev_messages = [_rev_messages[0]] + _rev_messages[-20:]
                    _rev_messages = _rev_messages + [{"role": "user", "content":
                                     "请审核上面的执行结果。只回答 PASS，或列出具体问题（不超过 5 条）。"}]
                    rr = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=MODEL, messages=_rev_messages, temperature=0.2, max_tokens=800,
                        extra_body={"thinking": {"type": "disabled"}},
                    )
                    review = (rr.choices[0].message.content or "").strip()
                    agent_memory.append(conversation_id, "assistant", review)
                except Exception as e:
                    print("[strict] 审核失败: " + str(e))
            return {"status": "ok", "content": content, "steps": step,
                    "history": used, "review": review}

        agent_memory.append(conversation_id, "assistant", msg.content or "",
                            tool_calls=assistant_tool_calls or None)
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": assistant_tool_calls})

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
                    try:
                        from . import approval_service
                        approval_service.save_pending(run_id, _ar.step, c.id, name, args)
                        agent_memory.append(conversation_id, "tool", "等待审批", tool_call_id=c.id)
                    except Exception as _e_pend:
                        print("[approval] 保存待审批失败: " + str(_e_pend))
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
            if on_event:
                try:
                    await on_event({"tool": name, "ok": ok, "step": step})
                except Exception:
                    pass

            # A3: strict 写后确定性自检（Python / JS），结果必须回灌给模型
            if mode == "strict" and name in WRITE_TOOLS and isinstance(args, dict):
                _fp = str(args.get("file_path") or "")
                if _fp.lower().endswith((".py", ".js", ".mjs", ".cjs", ".jsx")):
                    _dirty_files.add(_fp)
                    try:
                        _vr = await tool_gateway.invoke_tool_async("verify_syntax", {"file_path": _fp})
                        _vok = bool(getattr(_vr, "success", False))
                        _vres = getattr(_vr, "result", None) or getattr(_vr, "error", "")
                        used.append({"step": step, "tool": "verify_syntax", "ok": _vok})
                        if _vok:
                            _verified_files.add(_fp)
                            _vmsg = "[自检] verify_syntax 通过: " + _fp
                        else:
                            _verified_files.discard(_fp)
                            _vmsg = "[自检] verify_syntax 失败: " + _fp + " -> " + str(_vres)[:800]
                        messages.append({"role": "user", "content": _vmsg})
                        agent_memory.append(conversation_id, "user", _vmsg)
                    except Exception as e:
                        _verified_files.discard(_fp)
                        print("[strict] verify_syntax 失败: " + str(e))

    return {"status": "max_steps", "content": "达到步数上限，未完成任务。", "steps": max_steps, "history": used}
