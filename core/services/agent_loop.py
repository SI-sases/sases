# core/services/agent_loop.py
# -*- coding: utf-8 -*-
"""A1: append-only agent loop（flag 控制，默认仍走 fast_agent 旧路径）。"""
import asyncio
import json
import os
import shutil

from core import tool_gateway
from core.services import agent_memory
from core.services import token_meter, tool_pruner
from core.services import todo_service
from core.services import run_control_service
from core.services.agent_policy import before_tool, after_tool, WRITE_TOOLS, ApprovalRequired
from core.services.swarm.llm_parser import client, MODEL
from core.services.swarm.prompts import BASE_SYSTEM, BASE_PREFIX_HASH


def _direct_syntax_error(path):
    """独立于 verify_syntax 的语法回读校验（Python compile + tree-sitter JS）。"""
    try:
        from .syntax_service import check
        r = check(path)
        if r.get("ok"):
            return None
        return str(r.get("error") or "syntax error")
    except Exception as e:
        return "syntax checker unavailable: " + str(e)



def _needs_plan(goal, mode):
    if mode != "strict":
        return False
    text = str(goal or "")
    if len(text) >= 120:
        return True
    markers = ("然后", "之后", "最后", "同时", "步骤", "汇总", "批量",
               "依次", "再读回", "写入后", "修复并", "并且")
    return any(m in text for m in markers)


READ_PARALLEL_TOOLS = {"file_read", "grep_code", "dir_tree", "web_fetch",
                       "read_user_doc", "search_tools"}


def _is_investigation(goal):
    text = str(goal or "")
    markers = ("看看", "看下", "看一下", "是什么", "为什么", "问题", "检查",
               "分析", "怎么样", "是否", "排查", "诊断")
    write = ("改", "修复", "创建", "写入", "删除", "重命名", "重构",
             "实现", "添加", "部署", "安装")
    return any(m in text for m in markers) and not any(w in text for w in write)


def _is_write_task(goal):
    text = str(goal or "")
    return any(w in text for w in ("改", "修复", "创建", "写入", "删除", "重命名",
                                   "重构", "实现", "添加", "部署", "安装", "执行"))


def _tool_schemas(allowed_tool_ids=None, mode="fast"):
    from core.harness_runtime import harness_runtime
    from .fast_agent import tool_schema
    from .tool_visibility import visible
    tools = sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")
    if allowed_tool_ids is not None:
        allow = set(str(x) for x in allowed_tool_ids)
        tools = [t for t in tools if getattr(t, "module_id", "") in allow]
    tools = visible(tools)
    if str(mode or "") != "strict":
        tools = [t for t in tools if getattr(t, "module_id", "") != "todo_write"]
    return [tool_schema(t) for t in tools if getattr(t, "module_id", "")]


async def _run(user_id, conversation_id, goal, allowed_tool_ids=None, max_steps=8, run_id=None, mode="fast", resume=False, supervisor_id=None, on_event=None, skill_ids=None, permissions=None, agent_id=None, subagent_agent_id=None, multi_agent=False, budget_tokens=0):
    if not conversation_id:
        return {"status": "error", "content": "缺少会话", "steps": 0, "history": []}

    try:
        from .agent_compact import maybe_compact
        await maybe_compact(conversation_id, user_id)
    except Exception as _e_cp:
        print("[compact] 跳过: " + str(_e_cp))
    agent_memory.backfill(conversation_id)
    _client, _model = client, MODEL
    _agent_name = "default"
    if agent_id:
        try:
            from .model_runtime import resolve as _resolve_model
            _mr = _resolve_model(user_id, agent_id)
            if _mr:
                _client, _model = _mr["client"], _mr["model"]
                _agent_name = _mr.get("name") or agent_id
                print("[model] child agent=" + str(agent_id) + " model=" + _model)
        except Exception as _e_mr:
            print("[model] 子智能体模型解析失败: " + str(_e_mr))
    hist = agent_memory.history(conversation_id, run_id=(run_id if resume else None))
    try:
        from .run_context import set_current, get_current
        set_current(user_id, conversation_id, run_id, (get_current() or {}).get("run_id"), subagent_agent_id)
    except Exception as _e_ctx:
        print("[run] context 设置失败: " + str(_e_ctx))

    def _mem_append(role, content, **kw):
        kw.setdefault("run_id", run_id)
        return agent_memory.append(conversation_id, role, content, **kw)

    if not resume:
        if not hist or str(hist[-1].get("content") or "") != str(goal):
            _mem_append("user", goal)
            hist = agent_memory.history(conversation_id, run_id=(run_id if resume else None))
    else:
        # P1-7: 恢复时沿用已有 history；不要把“继续”指令再写成新目标
        pass
    messages = [{"role": "system", "content": BASE_SYSTEM}] + hist
    try:
        from . import skill_service
        _sp = skill_service.prompt_for(skill_ids)
        if _sp:
            messages[0]["content"] += "\n\n" + _sp
    except Exception as _e_sk:
        print("[skill] 注入失败: " + str(_e_sk))
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
    schemas = _tool_schemas(allowed_tool_ids, mode=mode)
    if _is_investigation(goal) and int(max_steps) < 16:
        max_steps = 16
    used = []
    _plan_required = _needs_plan(goal, mode)
    _dirty_files = set()
    _verified_files = set()
    _ui_dirty = set()
    _ui_ok = True
    _audit_steps = 0
    _ask_suppressed = False
    _force_final = False
    _audit_nudged = False
    _action_nudged = False
    _all_schemas = schemas

    def _audit_tick(batch_calls):
        nonlocal _audit_steps, schemas, _force_final, _audit_nudged
        if batch_calls and all(c.function.name in READ_PARALLEL_TOOLS for c in batch_calls):
            _audit_steps += 1
        else:
            _audit_steps = 0
            schemas = _all_schemas
        if (_is_investigation(goal) or _is_write_task(goal)) and _audit_steps >= 3 and schemas and not _audit_nudged:
            _audit_nudged = True
            # 调查够了：撤掉只读工具，只留写/验证工具，迫使模型落地修复
            schemas = [s for s in _all_schemas
                       if (s.get("function") or {}).get("name") not in READ_PARALLEL_TOOLS]
            _gate = ("[调查够了] 已经查看 3 轮。现在开始按低风险默认修复并验证，"
                     "只读工具已收起；不要继续读文件，也不要问用户是否需要修改。")
            messages.append({"role": "user", "content": _gate})
            _mem_append("user", _gate)
        if (_is_investigation(goal) or _is_write_task(goal)) and _audit_steps >= 5 and schemas:
            _gate = ("[调查截止] 已经查看 5 轮，不要再读文件。现在只允许写文件/验证，"
                     "直接执行修复。")
            messages.append({"role": "user", "content": _gate})
            _mem_append("user", _gate)
    try:
        _plan_ctx = todo_service.format_for_prompt(conversation_id, run_id)
        if not _plan_ctx and "继续执行上一条" in str(goal):
            _plan_ctx = todo_service.format_items(todo_service.latest(conversation_id))
        if _plan_ctx and messages and messages[-1].get("role") == "user":
            messages.insert(len(messages) - 1, {"role": "user", "content": _plan_ctx})
        elif _plan_required:
            messages.append({"role": "user", "content":
                "【计划要求】这是多步骤任务。先调用 todo_write 列出步骤和验收条件，"
                "再开始执行；每完成一步更新 todo；缺少依赖就标记 blocked。"})
    except Exception as _e_plan:
        print("[todo] 注入计划失败: " + str(_e_plan))

    if multi_agent:
        _multi_gate = ("[多子智能体] 这是父任务。只要目标能拆成 2 个以上独立调查，"
                       "必须先调用 subagent 并行处理（最多 3 个），不要自己逐个读文件；"
                       "收齐子结果后统一汇总、再写文件；子任务只读，写由父任务串行完成。"
                       "最终回答必须包含“## 子任务汇总”表：子 run / 目标 / 结论 / 失败原因。")
        messages.append({"role": "user", "content": _multi_gate})
        agent_memory.append(conversation_id, "user", _multi_gate, run_id=run_id)

    _budget = int(budget_tokens or 0)
    _subagent_calls = 0
    _agg_nudged = False
    if not _budget and run_id:
        try:
            from core.db import db_cursor as _dc_budget
            with _dc_budget() as _cb:
                _cb.execute("SELECT budget_tokens FROM supervisor_runs WHERE id=?", (int(run_id),))
                _r = _cb.fetchone()
            if _r:
                _budget = int(_r["budget_tokens"] or 0)
        except Exception:
            pass
    _used_tokens = 0
    _deadline = None
    if run_id:
        try:
            from core.db import db_cursor as _dc_dl
            with _dc_dl() as _cd:
                _cd.execute("SELECT deadline_at FROM supervisor_runs WHERE id=?", (int(run_id),))
                _dr = _cd.fetchone()
            if _dr and _dr["deadline_at"]:
                _deadline = str(_dr["deadline_at"])
        except Exception:
            pass

    for step in range(1, max_steps + 1):
        if _deadline:
            try:
                from datetime import datetime as _dt
                if _dt.now() > _dt.fromisoformat(_deadline.replace("Z", "")):
                    return {"status": "timeout", "content": "任务超时，已停止。",
                            "steps": step - 1, "history": used}
            except Exception:
                pass
        if run_id:
            try:
                from core.db import db_cursor as _dc_hb
                with _dc_hb(commit=True) as _chb:
                    _chb.execute(
                        "UPDATE supervisor_runs SET status='running', "
                        "heartbeat_at=datetime('now'), lease_until=datetime('now','+2 minutes') "
                        "WHERE id=? AND status IN ('running','interrupted','paused','running_resumed')",
                        (int(run_id),))
            except Exception as _e_hb:
                print("[run] heartbeat failed: " + str(_e_hb))
        if run_control_service.is_cancelled(conversation_id):
            return {"status": "cancelled", "content": "任务已取消。", "steps": step - 1, "history": used}
        if run_control_service.is_paused(conversation_id):
            # P1-1: 在当前步退出，agent_messages / todo / used 全部保留
            # P1-2: 记下待恢复的 run，供“继续”复用同一个 run
            try:
                run_control_service.set_resume_target(conversation_id, run_id, goal)
            except Exception as _e_rt:
                print("[pause] 记录恢复目标失败: " + str(_e_rt))
            try:
                from . import trace_service
                trace_service.emit(run_id, conversation_id, step, "paused",
                                   content="第 " + str(step - 1) + " 步后暂停，等待继续",
                                   status="paused")
            except Exception:
                pass
            return {"status": "paused",
                    "content": "已暂停。发送“继续”可从当前进度恢复。",
                    "steps": step - 1, "history": used}
        if _force_final:
            try:
                _fm = messages + [{"role": "user", "content":
                                   "现在只用自然语言给出结论/修复结果，不要输出任何工具调用标记。"}]
                _fr = await asyncio.to_thread(
                    _client.chat.completions.create,
                    model=_model, messages=_fm, temperature=0.3, max_tokens=1200,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                _txt = (_fr.choices[0].message.content or "").strip()
                _mem_append("assistant", _txt)
                return {"status": "ok", "content": _txt, "steps": step, "history": used}
            except Exception as _e_ff:
                return {"status": "error", "content": "总结失败: " + str(_e_ff),
                        "steps": step, "history": used}
        if step > 1:
            try:
                if await maybe_compact(conversation_id, user_id):
                    messages = [{"role": "system", "content": BASE_SYSTEM}] + agent_memory.history(
                        conversation_id, run_id=(run_id if resume else None))
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
            if _budget and _used_tokens + int(est.get("total") or 0) > _budget:
                return {"status": "budget_exceeded",
                        "content": "Token 预算已用完（" + str(_budget) + "）",
                        "steps": step - 1, "history": used}
            _used_tokens += int(est.get("total") or 0)
            if est["total"] > 60000 or pruned_count:
                print("[ctx] estimated tokens=" + str(est["total"]) +
                      " messages=" + str(est["messages"]) + " tools=" + str(est["tools"]))
        except Exception:
            pass
        try:
            resp = await asyncio.to_thread(
                _client.chat.completions.create,
                model=_model, messages=req_messages, tools=schemas or None,
                tool_choice=({"type": "function", "function": {"name": "subagent"}}
                             if (multi_agent and _subagent_calls < 2 and step <= 2 and schemas)
                             else ("auto" if schemas else None)),
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
            _mem_append("assistant", content)
            messages.append({"role": "assistant", "content": content})
            if _question:
                if _is_investigation(goal) and not _ask_suppressed:
                    _ask_suppressed = True
                    _noask = ("[不要提问] 用户只给了现象。按低风险默认值继续定位/修复，"
                              "产品偏好按现有设计保留；不要要求用户选文件、选方案或确认低风险修改。")
                    messages.append({"role": "user", "content": _noask})
                    _mem_append("user", _noask)
                    if step < max_steps:
                        continue
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
                    _direct_err = _direct_syntax_error(_fp)
                    if _direct_err:
                        _verified_files.discard(_fp)
                        continue
                    try:
                        _vr2 = await tool_gateway.invoke_tool_async("verify_syntax", {"file_path": _fp})
                        if bool(getattr(_vr2, "success", False)):
                            _verified_files.add(_fp)
                        else:
                            _verified_files.discard(_fp)
                    except Exception:
                        _verified_files.discard(_fp)
            # 前端改动：本机有 Chrome 时做一次真实页面 smoke
            _ui_required = False
            if _ui_dirty and os.getenv("SASES_UI_GATE", "1") == "1":
                try:
                    from .tool_visibility import _chrome_available
                    _ui_required = bool(_chrome_available())
                except Exception:
                    _ui_required = False
            if _ui_required:
                try:
                    _uir = await tool_gateway.invoke_tool_async(
                        "verify_ui", {"action": "screenshot", "filename": "agent_selfcheck.png",
                                      "url": "http://127.0.0.1:8001/"})
                    _ui_ok = bool(getattr(_uir, "success", False))
                    _uimsg = "[自检] verify_ui 截图" + ("通过" if _ui_ok else "失败") + ": " + ", ".join(sorted(_ui_dirty))
                    messages.append({"role": "user", "content": _uimsg})
                    _mem_append("user", _uimsg)
                except Exception as _e_ui:
                    _ui_ok = False
                    print("[ui] verify_ui 失败: " + str(_e_ui))
            # 调查完但没落盘：强制进入“执行”，不要只给方案
            if (_is_investigation(goal) and _audit_nudged and not _dirty_files
                    and not _action_nudged and step < max_steps):
                _action_nudged = True
                _act = ("[不要总结] 你已经定位到问题。现在直接修改低风险文件并验证，"
                        "不要问用户是否需要修改，也不要继续只给方案。")
                messages.append({"role": "user", "content": _act})
                _mem_append("user", _act)
                continue
            # 计划门禁：多步骤任务必须有 todo；todo 还有未完成项不允许结束
            try:
                _all_todos = todo_service.get(conversation_id, run_id)
                _pending_todos = [t for t in _all_todos if t.get("status") != "completed"]
            except Exception:
                _all_todos, _pending_todos = [], []
            if mode == "strict" and _plan_required and not _all_todos:
                _pgate = ("[计划缺失] 这个任务需要 todo_write。先列出步骤并标 in_progress，"
                          "再继续执行；不能没有计划就结束。")
                messages.append({"role": "user", "content": _pgate})
                _mem_append("user", _pgate)
                if step < max_steps:
                    continue
                return {"status": "plan_required", "content": _pgate,
                        "steps": step, "history": used}
            if mode == "strict" and _pending_todos:
                _plines = "\n".join("- " + t.get("content", "") for t in _pending_todos)
                _pgate = ("[计划未完成] 还有未完成 todo：\n" + _plines
                          + "\n请继续执行并更新 todo，完成前不要结束。")
                messages.append({"role": "user", "content": _pgate})
                _mem_append("user", _pgate)
                if step < max_steps:
                    continue
                return {"status": "plan_incomplete", "content": _pgate,
                        "steps": step, "history": used}
            _unverified = _dirty_files - _verified_files
            if mode == "strict" and (_unverified or (_ui_required and not _ui_ok)):
                _lines = sorted(_unverified)
                if _ui_required and not _ui_ok:
                    _lines.append("前端 UI 截图未通过")
                _gate = ("[自检未通过] 以下检查未通过：\n- " + "\n- ".join(_lines)
                         + "\n请修复并重新验证，修复前不要结束任务。")
                messages.append({"role": "user", "content": _gate})
                _mem_append("user", _gate)
                if step < max_steps:
                    continue
                return {"status": "verification_failed", "content": _gate,
                        "steps": step, "history": used}
            review = ""
            _need_review = (mode == "strict"
                            and any(h.get("tool") in WRITE_TOOLS for h in used)
                            and os.getenv("SASES_STRICT_REVIEW", "0") == "1")
            if _need_review:
                try:
                    _rev_messages = tool_pruner.prune_messages(messages)[0]
                    if len(_rev_messages) > 21:
                        _rev_messages = [_rev_messages[0]] + _rev_messages[-20:]
                    _rev_messages = _rev_messages + [{"role": "user", "content":
                                     "请审核上面的执行结果。只回答 PASS，或列出具体问题（不超过 5 条）。"}]
                    rr = await asyncio.to_thread(
                        _client.chat.completions.create,
                        model=_model, messages=_rev_messages, temperature=0.2, max_tokens=800,
                        extra_body={"thinking": {"type": "disabled"}},
                    )
                    review = (rr.choices[0].message.content or "").strip()
                    _mem_append("assistant", review)
                except Exception as e:
                    print("[strict] 审核失败: " + str(e))
            return {"status": "ok", "content": content, "steps": step,
                    "history": used, "review": review}

        _mem_append("assistant", msg.content or "",
                            tool_calls=assistant_tool_calls or None)
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": assistant_tool_calls})

        _READ_PARALLEL = READ_PARALLEL_TOOLS
        if len(calls) > 1 and all(c.function.name in _READ_PARALLEL for c in calls):
            _batch = []
            _can_batch = True
            for c in calls:
                try:
                    _args = json.loads(c.function.arguments or "{}")
                except Exception:
                    _args = {}
                try:
                    await before_tool(user_id, conversation_id, run_id, step, c.function.name, _args)
                except ApprovalRequired:
                    _can_batch = False
                    break
                except Exception:
                    _can_batch = False
                    break
                _batch.append((c, _args))
            if _can_batch:
                _results = await asyncio.gather(
                    *[tool_gateway.invoke_tool_async(c.function.name, a) for c, a in _batch],
                    return_exceptions=True,
                )
                for (c, _args), _r in zip(_batch, _results):
                    name = c.function.name
                    if isinstance(_r, Exception):
                        ok, text = False, "ERROR: " + str(_r)
                    else:
                        ok = bool(getattr(_r, "success", False))
                        text = str(getattr(_r, "result", "") or getattr(_r, "error", ""))[:4000]
                    used.append({"step": step, "tool": name, "args": _args, "ok": ok})
                    try:
                        from . import tool_usage_service
                        tool_usage_service.record(user_id, name, ok)
                    except Exception:
                        pass
                    _mem_append("tool", text, tool_call_id=c.id)
                    messages.append({"role": "tool", "tool_call_id": c.id, "content": text})
                    await after_tool(user_id, conversation_id, run_id, step, name, _args, ok, text)
                    if on_event:
                        try:
                            await on_event({"tool": name, "ok": ok, "step": step})
                        except Exception:
                            pass
                _audit_tick(calls)
                continue

        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            _deny = None
            if permissions is not None:
                if name in ("file_write", "file_replace_range", "smart_edit") and permissions.get("write") is False:
                    _deny = "当前会话已关闭写文件权限"
                elif name == "web_fetch" and permissions.get("web") is False:
                    _deny = "当前会话已关闭联网权限"
            if _deny:
                text = "DENIED: " + _deny
                _mem_append("tool", text, tool_call_id=c.id)
                messages.append({"role": "tool", "tool_call_id": c.id, "content": text})
                used.append({"step": step, "tool": name, "ok": False})
                continue
            if name == "todo_write":
                _tr = todo_service.write(user_id, conversation_id, run_id, args.get("todos"))
                ok = bool(_tr.get("success"))
                text = json.dumps(_tr, ensure_ascii=False)[:4000]
                used.append({"step": step, "tool": name, "args": args, "ok": ok})
                try:
                    from . import tool_usage_service
                    tool_usage_service.record(user_id, name, ok)
                except Exception:
                    pass
                _mem_append("tool", text, tool_call_id=c.id)
                messages.append({"role": "tool", "tool_call_id": c.id, "content": text})
                if on_event:
                    try:
                        await on_event({"tool": name, "ok": ok, "step": step})
                    except Exception:
                        pass
                continue
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
                        _mem_append("tool", "等待审批", tool_call_id=c.id)
                    except Exception as _e_pend:
                        print("[approval] 保存待审批失败: " + str(_e_pend))
                return {"status": "awaiting_approval", "content": "等待审批：" + str(_ar.tool),
                        "step": _ar.step, "tool": _ar.tool, "steps": step, "history": used}
            _bak = None
            if name in ("file_write", "file_replace_range", "smart_edit") and isinstance(args, dict):
                _bp = str(args.get("file_path") or "")
                if _bp and os.path.isfile(_bp):
                    try:
                        _bak = _bp + ".agentbak"
                        shutil.copy2(_bp, _bak)
                    except Exception:
                        _bak = None
            try:
                r = await tool_gateway.invoke_tool_async(name, args)
                ok = bool(getattr(r, "success", False))
                text = str(getattr(r, "result", "") or getattr(r, "error", ""))[:4000]
            except Exception as e:
                ok, text = False, "ERROR: " + str(e)
            if not ok and _bak:
                try:
                    shutil.copy2(_bak, _bp)
                except Exception:
                    pass
            used.append({"step": step, "tool": name, "args": args, "ok": ok})
            if name == "subagent":
                _subagent_calls += 1
            try:
                from . import tool_usage_service
                tool_usage_service.record(user_id, name, ok)
            except Exception:
                pass
            _mem_append("tool", text, tool_call_id=c.id)
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
                    if ("/static/" in _fp.replace("\\", "/") or _fp.replace("\\", "/").startswith("static/")) and _fp.lower().endswith((".js", ".html", ".css")):
                        _ui_dirty.add(_fp)
                        _ui_ok = False
                    try:
                        _vr = await tool_gateway.invoke_tool_async("verify_syntax", {"file_path": _fp})
                        _vok = bool(getattr(_vr, "success", False))
                        _vres = getattr(_vr, "result", None) or getattr(_vr, "error", "")
                        used.append({"step": step, "tool": "verify_syntax", "ok": _vok})
                        if _vok:
                            _verified_files.add(_fp)
                            _vmsg = "[自检] verify_syntax 通过: " + _fp
                            if _bak:
                                try:
                                    os.remove(_bak)
                                except Exception:
                                    pass
                        else:
                            _verified_files.discard(_fp)
                            _vmsg = "[自检] verify_syntax 失败: " + _fp + " -> " + str(_vres)[:800]
                            if _bak:
                                try:
                                    shutil.copy2(_bak, _fp)
                                    _vmsg += "（已回滚该文件）"
                                except Exception:
                                    pass
                        messages.append({"role": "user", "content": _vmsg})
                        _mem_append("user", _vmsg)
                    except Exception as e:
                        _verified_files.discard(_fp)
                        print("[strict] verify_syntax 失败: " + str(e))

        _audit_tick(calls)
        if (_is_investigation(goal) and step >= max_steps - 1 and _dirty_files):
            _force_final = True

    return {"status": "max_steps", "content": "达到步数上限，未完成任务。", "steps": max_steps, "history": used}


# 写任务串行：避免多个写 run 并发改同一批文件；只读/聊天仍可并行
_WRITE_LOCK = asyncio.Lock()


async def run(user_id, conversation_id, goal, allowed_tool_ids=None, max_steps=8,
              run_id=None, mode="fast", resume=False, supervisor_id=None,
              on_event=None, skill_ids=None, permissions=None, agent_id=None,
              subagent_agent_id=None, multi_agent=False, budget_tokens=0):
    if mode == "strict" and _is_write_task(goal):
        async with _WRITE_LOCK:
            return await _run(user_id, conversation_id, goal, allowed_tool_ids, max_steps,
                              run_id, mode, resume, supervisor_id, on_event, skill_ids, permissions, agent_id, subagent_agent_id, multi_agent, budget_tokens)
    return await _run(user_id, conversation_id, goal, allowed_tool_ids, max_steps,
                      run_id, mode, resume, supervisor_id, on_event, skill_ids, permissions, agent_id, subagent_agent_id, multi_agent, budget_tokens)
