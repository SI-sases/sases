import asyncio, json, time
from datetime import datetime
from typing import Optional, Dict, Any, List
from ... import config
from ...db import db_cursor
from .. import memory_service
from .. import feedback_service
from .prompts import COMMANDER_SYSTEM_PROMPT, REPLAN_SYSTEM_PROMPT
from .reviewer import UNRECOVERABLE_KEYWORDS
from .memory_cache import _pending
from .persistence import (_save_pending, _delete_pending_from_db, _load_pending, _has_active_task_in_conversation, _ensure_feedback_table)
from .helpers import _insert_message, _get_conversation_history, pick_swarm_agents
from .llm_parser import _call_llm, _parse_plan, _normalize_steps, _validate_steps_format, _precheck_steps
from .task_state import _load_task_state

async def plan_task(
    user_id: int,
    conversation_id: int,
    user_input: str,
    commander_id: str = None,
    executor_id: str = None,
    timeout: int = 30,
    require_confirmation: bool = False,
    supervisor_id: str = None,
    supervisor_run_id: int = None,
    max_steps: int = None
) -> Dict[str, Any]:
    if conversation_id and _has_active_task_in_conversation(conversation_id):
        err_msg = "[SUMMARY]:当前会话有正在执行的任务，请等待完成或取消后再提交新任务。"
        _insert_message(conversation_id, err_msg, sender_agent_id=None)
        print(f"[swarm] 会话 {conversation_id} 已有活跃任务，拒绝新任务")
        return {"status": "busy", "message": "会话已有运行中的任务"}

    if not commander_id or not executor_id:
        auto_cmd, auto_exec = pick_swarm_agents(user_id)
        commander_id = commander_id or auto_cmd
        executor_id = executor_id or auto_exec

    if not commander_id:
        err_msg = "[SUMMARY]:未找到可用智能体，请先在模型管理中创建智能体。"
        _insert_message(conversation_id, err_msg, sender_agent_id=None)
        return {"status": "no_agent", "message": "用户没有可用智能体"}

    history_text = _get_conversation_history(conversation_id, limit=10)

    success_text = ""
    failure_text = ""
    try:
        success_memories = memory_service.recall(
            user_id=user_id, query=user_input, top_k=2, memory_type="task_result"
        )[:2]
        if success_memories:
            lines = []
            for m in success_memories:
                content = (m.get("content") or "").replace("\n", " ")[:120]
                lines.append(f"- {content}")
            success_text = "\n".join(lines)
            print(f"[swarm] 检索到 {len(success_memories)} 条成功经验")
        else:
            print(f"[swarm] 检索到 0 条成功经验")
    except Exception as e:
        print(f"[swarm] 成功记忆检索失败: {e}")

    try:
        failure_memories = memory_service.recall(
            user_id=user_id, query=user_input, top_k=2, memory_type="failure_pattern"
        )[:2]
        if failure_memories:
            lines = []
            for m in failure_memories:
                content = (m.get("content") or "").replace("\n", " ")[:120]
                lines.append(f"- {content}")
            failure_text = "\n".join(lines)
            print(f"[swarm] 检索到 {len(failure_memories)} 条失败教训")
        else:
            print(f"[swarm] 检索到 0 条失败教训")
    except Exception as e:
        print(f"[swarm] 失败记忆检索失败: {e}")

    _insert_message(conversation_id, user_input, sender_agent_id=None)

    # 项目库检索（v0.17.0）
    project_text = ""
    try:
        from .. import project_service
        chunks = project_service.retrieve_project_chunks(user_input, top_k=3, user_id=user_id)
        if chunks:
            project_text = project_service.format_chunks_for_prompt(chunks)
            print(f"[swarm] 检索到 {len(chunks)} 条项目资料")
        else:
            print(f"[swarm] 项目库无匹配")
    except Exception as e:
        print(f"[swarm] 项目库检索失败: {e}")


    pattern_text = ''
    try:
        import random as _rnd
        if _rnd.random() < 0.5:
            from .. import pattern_service
            _pats = pattern_service.retrieve_patterns(user_input, domain='dev', top_k=3)
            if _pats:
                pattern_text = pattern_service.format_patterns_for_prompt(_pats)
                print(f'[swarm] 注入 {len(_pats)} 条 pattern (A组)')
            else:
                print('[swarm] 无相关 pattern (A组)')
        else:
            print('[swarm] 跳过 pattern 注入 (B组)')
    except Exception as e:
        print(f'[swarm] pattern 检索失败: {e}')


    # 工具手册检索（v0.22.1 规则匹配）
    manual_text = ""
    try:
        _MAP = [
            (['读', '查看', '内容'], 'file_read'),
            (['改', '替换', '插入', '添加', '删除', '写入'], 'file_patch'),
            (['运行', '执行代码', '脚本', 'Python'], 'run_python'),
            (['搜索', '查找', '定位'], 'grep_code'),
            (['目录', '文件列表', '列出'], 'dir_tree'),
            (['语法', '检查'], 'verify_syntax'),
            (['提交', '推送', 'git'], 'git_ops'),
            (['请求', '调用', 'API', 'HTTP'], 'api_call'),
            (['抓', '网页', 'URL'], 'web_fetch'),
            (['锚点'], '锚点'),
            (['换行', 'CRLF'], '换行'),
        ]
        _hits = []
        for _kws, _tool in _MAP:
            for _kw in _kws:
                if _kw in user_input:
                    _hits.append(_tool)
                    break
        _hits = list(dict.fromkeys(_hits))[:3]
        if _hits:
            with db_cursor() as _cur_m:
                _or_parts = []
                _params = []
                for _t in _hits:
                    _or_parts.append("title LIKE ?")
                    _params.append(f'%{_t}%')
                _sql = f"SELECT title, content FROM knowledge_docs WHERE scope='manual' AND ({' OR '.join(_or_parts)}) LIMIT 3"
                _cur_m.execute(_sql, _params)
                _manuals = _cur_m.fetchall()
            if _manuals:
                manual_text = "\n".join([f"【{m['title']}】\n{m['content'][:300]}" for m in _manuals])
                print(f"[swarm] 检索到 {len(_manuals)} 条工具手册: {_hits}")
            else:
                print(f"[swarm] 手册无匹配 (命中关键词: {_hits})")
        else:
            print("[swarm] 手册无匹配 (无关键词命中)")
    except Exception as e:
        print(f"[swarm] 手册检索失败: {e}")

    prompt_parts = []
    if manual_text:
        prompt_parts.append(f"【工具手册参考】\n{manual_text}")
    if pattern_text:
        prompt_parts.append(pattern_text)


    if project_text:
        prompt_parts.append(project_text)


    if success_text:
        prompt_parts.append(f"【可参考的成功经验】\n{success_text}")
    if failure_text:
        prompt_parts.append(f"【需要避免的失败教训】\n{failure_text}")
    if history_text:
        prompt_parts.append(f"【最近的会话历史】\n{history_text}")
    # v0.19: 注入任务状态快照
    if supervisor_run_id:
        try:
            _prev_state = _load_task_state(f"run_{supervisor_run_id}", user_id)
            if _prev_state:
                _state_lines = []
                if _prev_state.get('facts'):
                    _state_lines.append("⚠️ 以下数据已在上轮获得，本轮直接使用，禁止重复 grep/read：")
                    for _f in _prev_state['facts'][-10:]:
                        _state_lines.append(f"  - {_f.get('file', '?')}:{_f.get('line', '?')} = {_f.get('text', '')[:80]}")
                if _prev_state.get('pending'):
                    _state_lines.append("待完成：" + " | ".join(_prev_state['pending'][:5]))
                if _prev_state.get('decisions'):
                    _state_lines.append("已决策：" + " | ".join(_prev_state['decisions'][:5]))
                if _state_lines:
                    prompt_parts.append("【上一轮任务状态（已有数据，禁止重复读取）】\n" + chr(10).join(_state_lines))
        except Exception as _se:
            print(f'[state] inject failed: {_se}')
    try:
        from ... import harness_runtime as _hr
        _tools = _hr.harness_runtime.list_tools()
        if _tools:
            _tl = ['【当前可用 Harness 工具】']
            for _t in _tools:
                _mid = getattr(_t, 'module_id', '') or ''
                _name = getattr(_t, 'name', '') or ''
                _desc = (getattr(_t, 'description', '') or '')[:80]
                _aliases = getattr(_t, 'aliases', []) or []
                _params = getattr(_t, 'params', {}) or {}
                if not _mid:
                    continue
                _alias_str = (' (别名: ' + ', '.join(_aliases) + ')') if _aliases else ''
                _line = '- ' + _mid + _alias_str + '：' + _name + ' —— ' + _desc
                _tl.append(_line)
                _required = [k for k, v in _params.items() if v.get('desc') == '必填']
                if _required:
                    _tl.append('    必填：' + ', '.join(_required))
            if len(_tl) > 1:
                prompt_parts.append(chr(10).join(_tl))
    except Exception as _te:
        print('[swarm] 注入工具清单失败: ' + str(_te))


    prompt_parts.append(f"【用户当前任务】\n{user_input}")
    prompt_parts.append(
        "请拆解为命令序列。\n"
        "必须只输出 JSON 数组，格式：[{\"step\":1,\"description\":\"...\",\"command\":\"...\"}]\n"
        "不要输出任何其他文字，不要用 markdown 代码块。"
    )
    full_prompt = "\n\n".join(prompt_parts)

    raw = ""
    last_err = None
    for attempt in range(2):
        try:
            raw = await _call_llm(full_prompt, COMMANDER_SYSTEM_PROMPT)
            if raw and raw.strip():
                print(f"[swarm-debug] 第 {attempt+1} 次成功，raw 长度={len(raw)}")
                break
            print(f"[swarm] LLM 返回空，重试第 {attempt+1} 次")
        except Exception as e:
            last_err = e
            print(f"[swarm] LLM 调用异常: {e}")

    if not raw or not raw.strip():
        err_msg = f"[SUMMARY]:任务拆解失败（LLM 返回空，请查看服务端日志）"
        _insert_message(conversation_id, err_msg, sender_agent_id=commander_id)
        return {"status": "error", "message": "LLM empty response"}

    steps = _parse_plan(raw, max_steps=max_steps)
    if steps:
        steps = _normalize_steps(steps)
        steps, _fmt_errors = _validate_steps_format(steps)
        if steps:
            _pre_warns, _pre_blocks = _precheck_steps(steps)
            if _pre_warns:
                print(f"[precheck] warnings: {_pre_warns}")
            if _pre_blocks:
                print(f"[precheck] blocked: {_pre_blocks}")
                return None
        if _fmt_errors:
            print(f"[swarm] step 格式错误: {_fmt_errors}")
            return None
    if not steps:
        if raw.strip() == "[DONE]":
            print("[swarm] 指挥官判定任务完成")
            return {"status": "done", "message": "任务完成", "task_id": None}


        print(f"[swarm] 拆解失败，LLM 原始返回: {raw[:500]!r}")
        task_id = f"noplan_{int(time.time() * 1000)}"
        task = {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_text": user_input,
            "steps": [],
            "results": [],
            "done": set(),
            "commander_id": commander_id,
            "executor_id": executor_id,
            "created_at": datetime.now().isoformat(),
            "cancelled": True,
            "no_plan": True,
            "retry_count": 0,
            "is_draft": False,
        }
        _pending[task_id] = task
        _save_pending(task)
        return {"status": "no_plan", "message": "无法拆解任务", "task_id": task_id}

    print("[DIAG] 即将构建 task")
    task_id = f"t_{int(time.time() * 1000)}"

    is_draft = bool(require_confirmation)
    task = {
        "task_id": task_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "user_text": user_input,
        "steps": steps,
        "results": [],
        "done": set(),
        "commander_id": commander_id,
        "executor_id": executor_id,
        "created_at": datetime.now().isoformat(),
        "cancelled": False,
        "no_plan": False,
        "retry_count": 0,
        "is_draft": is_draft,
        "supervisor_id": supervisor_id or commander_id,
        "supervisor_run_id": supervisor_run_id,
    }
    _pending[task_id] = task
    print("[DIAG] 即将调用 _save_pending")
    _save_pending(task)
    print("[DIAG] _save_pending 调用完成")

    if is_draft:
        draft_payload = {"task_id": task_id, "steps": steps}
        draft_msg = "[TASK_DRAFT]:" + json.dumps(draft_payload, ensure_ascii=False)
        _insert_message(conversation_id, draft_msg, sender_agent_id=commander_id)
        print(f"[swarm] 草稿模式：任务 {task_id} 已生成草稿，等待用户确认")
        return {
            "status": "draft",
            "task_id": task_id,
            "steps": steps,
            "conversation_id": conversation_id,
            "commander_id": commander_id,
            "executor_id": executor_id
        }

    task_payload = {"task_id": task_id, "steps": steps}
    task_msg = "[TASK]:" + json.dumps(task_payload, ensure_ascii=False)
    _insert_message(conversation_id, task_msg, sender_agent_id=commander_id)

    return {
        "status": "planned",
        "task_id": task_id,
        "steps": steps,
        "conversation_id": conversation_id,
        "commander_id": commander_id,
        "executor_id": executor_id
    }


def confirm_task(
    task_id: str,
    user_id: int,
    edited_steps: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found", "message": "任务不存在"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden", "message": "无权确认该任务"}

    if not task.get("is_draft"):
        return {"status": "not_draft", "message": "该任务不是草稿"}

    if edited_steps:
        task["steps"] = edited_steps[:config.MAX_STEPS]
        print(f"[swarm] 用户已编辑草稿 {task_id}，新步骤数: {len(edited_steps)}")

    task["is_draft"] = False
    _save_pending(task)

    task_payload = {"task_id": task_id, "steps": task["steps"]}
    task_msg = "[TASK]:" + json.dumps(task_payload, ensure_ascii=False)
    _insert_message(task["conversation_id"], task_msg, sender_agent_id=task["commander_id"])

    print(f"[swarm] 草稿 {task_id} 已确认，下发执行")
    return {
        "status": "confirmed",
        "task_id": task_id,
        "steps": task["steps"]
    }


def reject_task(task_id: str, user_id: int) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden"}

    _insert_message(task["conversation_id"], "[SUMMARY]:任务草稿已被用户取消。", sender_agent_id=task["commander_id"])
    del _pending[task_id]
    _delete_pending_from_db(task_id)
    return {"status": "rejected", "task_id": task_id}


def _record_cancel_feedback(user_id, task_id):
    """记录用户主动取消的隐式反馈"""
    try:
        feedback_service.record_implicit(
            user_id=user_id,
            task_id=task_id,
            rating="down",
            signal="user_cancelled",
            task_source="swarm",
        )
    except Exception as e:
        print(f"[feedback] 记录取消反馈失败: {e}")


def cancel_task(task_id: str, user_id: int) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found", "message": "任务不存在或已完成"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden", "message": "无权取消该任务"}

    if task.get("no_plan"):
        del _pending[task_id]
        _delete_pending_from_db(task_id)
        _record_cancel_feedback(user_id, task_id)
        return {"status": "cancelled", "task_id": task_id}

    task["cancelled"] = True
    _save_pending(task)
    _insert_message(task["conversation_id"], "[SUMMARY]:任务已取消。", sender_agent_id=task["commander_id"])
    _record_cancel_feedback(user_id, task_id)
    return {"status": "cancelled", "task_id": task_id}


def submit_feedback(
    user_id: int,
    task_id: str = None,
    original_input: str = "",
    feedback_type: str = "false_positive",
    note: str = ""
) -> Dict[str, Any]:
    _ensure_feedback_table()

    if (not original_input) and task_id and task_id in _pending:
        original_input = _pending[task_id].get("user_text", "")

    if task_id and task_id in _pending and _pending[task_id]["user_id"] == user_id:
        task = _pending[task_id]
        task["cancelled"] = True
        if not task.get("no_plan") and not task.get("is_draft"):
            _insert_message(task["conversation_id"], "[SUMMARY]:已取消，并记录为误判。", sender_agent_id=task["commander_id"])
        del _pending[task_id]
        _delete_pending_from_db(task_id)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO intent_feedback (user_id, task_id, original_input, feedback_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, task_id or "", original_input, feedback_type, note, datetime.now().isoformat())
        )

    return {
        "status": "recorded",
        "task_id": task_id,
        "feedback_type": feedback_type,
        "original_input": original_input
    }


async def replan_failed_steps(task: Dict[str, Any], max_steps: int = None) -> Optional[List[Dict[str, Any]]]:
    failed_info = []
    for r in task["results"]:
        if r.get("review") == "retry":
            failed_info.append({
                "step": r["step"],
                "description": r.get("description", ""),
                "original_command": r.get("command", ""),
                "failure_reason": r.get("reason", ""),
                "output_preview": (r.get("output") or "")[:200],
            })

    if not failed_info:
        return None

    all_unrecoverable = True
    for f in failed_info:
        output = (f.get("output_preview") or "") + (f.get("failure_reason") or "")
        if not any(kw in output for kw in UNRECOVERABLE_KEYWORDS):
            all_unrecoverable = False
            break

    if all_unrecoverable:
        print(f"[swarm] 所有失败均为不可恢复错误，跳过重拆")
        return None

    prompt = f"""原任务：{task['user_text']}

已完成的步骤及结果：
{json.dumps(task['results'], ensure_ascii=False, indent=2)}

失败的步骤（需要你重新拆解）：
{json.dumps(failed_info, ensure_ascii=False, indent=2)}

请针对上述失败步骤重新拆解命令。要求：
1. 必须输出 JSON 数组，不要任何解释文字
2. 格式：[{{"step":1,"description":"...","command":"..."}}]
3. 只允许命令：dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc
4. 禁止 copy / move / del / powershell / for / if / 重定向
5. 如果是"old_snippet 未找到"：先用 findstr 精确确认原文再 patch
6. 用 {{{{stepN}}}} 引用前序步骤的输出
7. 如果失败原因是"检测到工具别名 xxx 被误用作 shell 命令"，下次必须改用type=harness + module_id=该别名 的形式（例如 module_id="file_write"），不要再写成 command 字段。

只输出 JSON 数组，现在开始："""

    try:
        raw = await _call_llm(prompt, REPLAN_SYSTEM_PROMPT, max_tokens=config.REPLAN_MAX_TOKENS)
        print(f"[swarm] 重拆 LLM 返回长度: {len(raw)}, 前 300 字: {raw[:300]!r}")
    except Exception as e:
        print(f"[swarm] 重拆 LLM 异常: {e}")
        return None

    if not raw or not raw.strip():
        print(f"[swarm] 重拆 LLM 返回空，放弃重拆")
        return None

    steps = _parse_plan(raw, max_steps=max_steps)
    if steps:
        steps = _normalize_steps(steps)
        steps, _fmt_errors = _validate_steps_format(steps)
        if steps:
            _pre_warns, _pre_blocks = _precheck_steps(steps)
            if _pre_warns:
                print(f"[precheck] warnings: {_pre_warns}")
            if _pre_blocks:
                print(f"[precheck] blocked: {_pre_blocks}")
                return None
        if _fmt_errors:
            print(f"[swarm] step 格式错误: {_fmt_errors}")
            return None
    if not steps:
        print(f"[swarm] 重拆 JSON 解析失败，原始输出: {raw[:500]!r}")
        return None

    for i, s in enumerate(steps):
        s["step"] = i + 1
    print(f"[swarm] 重拆成功，新步骤数: {len(steps)}")
    return steps
