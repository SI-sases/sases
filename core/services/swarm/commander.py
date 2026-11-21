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

_READONLY_TOOLS = ("grep_code", "file_read", "dir_tree", "verify_claim", "answer")


def _count_readonly_rounds(user_id, conversation_id, limit=3):
    """统计最近连续多少轮只有侦察、没有写入（数据源：safety_memory.task_summary）。"""
    if not user_id or not conversation_id:
        return 0
    try:
        with db_cursor() as _cur_ro:
            _cur_ro.execute(
                "SELECT content FROM safety_memory "
                "WHERE user_id=? AND memory_type='task_summary' "
                "ORDER BY id DESC LIMIT 12",
                (user_id,),
            )
            _rows_ro = _cur_ro.fetchall()
    except Exception as _e_ro:
        print("[C2] 读取历史轮次失败: " + str(_e_ro))
        return 0
    _seq = []
    for _row_ro in _rows_ro:
        _txt_ro = (_row_ro["content"] if isinstance(_row_ro, dict) else _row_ro[0]) or ""
        try:
            _aud_ro = json.loads(_txt_ro)
        except Exception:
            continue
        if str(_aud_ro.get("conversation_id")) != str(conversation_id):
            continue
        _tools_ro = [str(t.get("tool") or "").lower() for t in (_aud_ro.get("tools_used") or []) if t.get("tool")]
        if _tools_ro:
            _seq.append(_tools_ro)
        if len(_seq) >= limit:
            break
    _n_ro = 0
    for _tools_ro in _seq:
        if all(t in _READONLY_TOOLS for t in _tools_ro):
            _n_ro += 1
        else:
            break
    return _n_ro


async def generate_script_for_task(user_id, conversation_id, user_input, failed_results):
    """常规拆解失败时，让 LLM 直接生成 Python 脚本。返回脚本代码或 None。"""
    try:
        from .prompts import SCRIPT_FALLBACK_PROMPT
    except Exception as _e_imp:
        print("[script_fallback] import SCRIPT_FALLBACK_PROMPT 失败: " + str(_e_imp))
        return None
    failures_lines = []
    for r in failed_results[:5]:
        _cmd = str(r.get('command') or r.get('module_id') or '')[:80]
        _reason = str(r.get('reason') or r.get('output') or '')[:150]
        failures_lines.append("- " + _cmd + " => " + _reason)
    failures_text = chr(10).join(failures_lines) if failures_lines else "(无)"
    import re as _re
    import os as _os
    _file_ctx = ""
    _m = _re.search(r'([a-zA-Z0-9_\-/]+\.(?:js|py|html|css|json))', str(user_input))
    if _m:
        _fp = _m.group(1)
        _found_path = None
        for _sp in ["", "static/modules/", "static/", "core/", "core/services/", "scripts/"]:
            _test = _os.path.join(_sp, _fp) if _sp else _fp
            if _os.path.exists(_test):
                _found_path = _test
                break
        if _found_path:
            try:
                with open(_found_path, "r", encoding="utf-8") as _f:
                    _content = "".join(_f.readlines()[:150])
                    _file_ctx = f"【目标文件 {_found_path} 的真实前150行内容】：\n{_content}\n"
            except Exception:
                pass

    prompt = SCRIPT_FALLBACK_PROMPT.replace("{file_context}", _file_ctx).replace("{goal}", str(user_input)[:500]).replace("{failures}", failures_text)
    try:
        raw = await _call_llm(prompt, max_tokens=4000)
    except Exception as e:
        print("[script_fallback] LLM 调用失败: " + str(e))
        return None
    if not raw or '#CANNOT_SCRIPT' in raw:
        print("[script_fallback] LLM 判定无法用脚本完成")
        return None
    text = raw.strip()
    if text.startswith('```'):
        _lines = text.split(chr(10))
        _lines = _lines[1:] if _lines[0].startswith('```') else _lines
        if _lines and _lines[-1].strip() == '```':
            _lines = _lines[:-1]
        text = chr(10).join(_lines)
    text = text.strip()
    if len(text) > 50000:
        print("[script_fallback] 脚本过长: " + str(len(text)))
        return None
    if not text:
        return None
    print("[script_fallback] 生成脚本 " + str(len(text)) + " 字符")
    return text



def _format_enabled_apis(user_id, enabled_api_ids):
    """把用户勾选的外部 API 格式化成 planner 可见的清单（不暴露 auth）。"""
    try:
        if not enabled_api_ids:
            return ""
        ids = []
        for x in enabled_api_ids:
            s = str(x).strip()
            if s.startswith("ext_api_"):
                s = s[len("ext_api_"):]
            if s.isdigit():
                ids.append(int(s))
        if not ids:
            return ""
        marks = ",".join("?" for _ in ids)
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, api_name, api_desc, endpoint, method FROM user_api_configs "
                "WHERE user_id=? AND id IN (" + marks + ") ORDER BY id",
                (user_id,) + tuple(ids),
            )
            rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            return ""
        lines = ["【本次已勾选的外部 API（只允许调用这些）】"]
        for r in rows:
            desc = str(r.get("api_desc") or "")[:80]
            lines.append(
                "- ext_api_" + str(r["id"]) + "：" + str(r.get("api_name") or "")
                + "（" + str(r.get("method") or "GET") + " " + str(r.get("endpoint") or "") + "）"
                + (("｜" + desc) if desc else "")
                + "；调用格式 {\"type\":\"harness\",\"module_id\":\"ext_api_" + str(r["id"]) + "\",\"params\":{...}}"
            )
        return chr(10).join(lines)
    except Exception as e:
        print("[swarm] 格式化外部 API 失败: " + str(e))
        return ""


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
    max_steps: int = None,
    enabled_api_ids: list = None,
    enabled_tool_ids: list = None,
    enabled_skill_ids: list = None
) -> Dict[str, Any]:
    # A2: 接近上下文预算时先压缩旧历史（失败不影响主流程）
    try:
        from core.services.unified_context import maybe_compact as _maybe_compact
        await _maybe_compact(conversation_id, user_id)
    except Exception as _e_compact:
        print("[plan_task] compact failed: " + str(_e_compact))

    # [CTX-UPGRADE-v1] 有 doc_paste 时注入完整方案
    try:
        from core.services.unified_context import enrich_plan_input as _epi
        user_input = _epi(user_id, conversation_id, user_input)
    except Exception as _e_epi:
        print("[plan_task] enrich failed: " + str(_e_epi))

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
        _tools = sorted(_hr.harness_runtime.list_tools(), key=lambda t: getattr(t, 'module_id', '') or '')
        if enabled_tool_ids:
            _allow_tools = set(str(x) for x in enabled_tool_ids)
            _tools = [t for t in _tools if getattr(t, 'module_id', '') in _allow_tools]
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

    # 用户勾选的外部 API 注入（仅列已勾选项）
    _api_text = _format_enabled_apis(user_id, enabled_api_ids)
    if _api_text:
        prompt_parts.append(_api_text)
        print("[swarm] 注入外部 API 清单，数量=" + str(_api_text.count("ext_api_")))


    # [C2] 连续两轮只侦察不写入 -> 本轮强制写入
    try:
        _ro_rounds = _count_readonly_rounds(user_id, conversation_id)
        if _ro_rounds >= 2:
            print("[C2] 连续 " + str(_ro_rounds) + " 轮只读，注入强制写入铁律")
            prompt_parts.append(
                "【强制写入铁律（本轮必须遵守）】\n"
                "前 " + str(_ro_rounds) + " 轮只有侦察、没有写入。本轮 plan 必须至少包含 1 个写操作：\n"
                "- smart_edit / file_write / file_replace_range / run_python（含写入）\n"
                "禁止本轮全是 grep_code / file_read / dir_tree。\n"
                "如果确实不能写，在【分析】里说明卡在哪一条 file:line，并让用户确认。"
            )
    except Exception as _e_c2:
        print("[C2] 注入失败: " + str(_e_c2))

    # [C2-snapshot] 注入上一轮失败切片（来自 active_task_snapshot）
    try:
        from .. import task_state_service as _tss_snap
        _snap_inj = _tss_snap.get_snapshot(conversation_id)
        if _snap_inj:
            _fs_inj = _snap_inj.get("failed_summary") or []
            _ts_inj = _snap_inj.get("tried_strategies") or []
            if _fs_inj or _ts_inj:
                _snap_lines = ["【上次执行失败信息（禁止重复）】"]
                for _f_inj in _fs_inj[-3:]:
                    _snap_lines.append(
                        "- 步骤 " + str(_f_inj.get("step", "")) + " 用 " + str(_f_inj.get("tool", ""))
                        + " 失败：" + str(_f_inj.get("reason", ""))[:100]
                    )
                if _ts_inj:
                    _snap_lines.append("- 已试过方案：" + "、".join(str(x) for x in _ts_inj[:5]))
                prompt_parts.append(chr(10).join(_snap_lines))
    except Exception as _e_snap_inj:
        print("[C2-snapshot] 注入失败: " + str(_e_snap_inj))

    # [AUDIT-2] 注入上一轮任务总结（跨轮学习）
    try:
        _last_audits = memory_service.recall_by_type(user_id, "task_summary", top_k=1)
        if _last_audits:
            _aud = json.loads(_last_audits[0].get("content") or "{}")
            if _aud:
                _aud_lines = ["【上一轮任务总结】"]
                _tu = _aud.get("tools_used") or []
                if _tu:
                    _aud_lines.append("- 用过的工具：" + ", ".join(
                        str(t.get("tool")) + "x" + str(t.get("count")) for t in _tu[:6]))
                if _aud.get("successful_strategies"):
                    _aud_lines.append("- 成功策略：" + ", ".join(map(str, _aud["successful_strategies"][:5])))
                if _aud.get("failed_strategies"):
                    _aud_lines.append("- 失败策略（避免重复）：" + " | ".join(
                        str(x)[:80] for x in _aud["failed_strategies"][:3]))
                prompt_parts.append(chr(10).join(_aud_lines))
    except Exception as _e_aud2:
        print("[AUDIT] 注入上一轮总结失败: " + str(_e_aud2))

    prompt_parts.append(f"【用户当前任务】\n{user_input}")
    prompt_parts.append(
        "请先输出三段式（【分析】【方案】【建议】），再输出一行 ---STEPS---，最后输出 JSON 数组。\n"
        "格式：三段式\n---STEPS---\n[{\"step\":1,\"description\":\"...\",\"command\":\"...\"}]\n"
        "---STEPS--- 之后不要有任何解释文字，不要用 markdown 代码块。"
    )
    full_prompt = "\n\n".join(prompt_parts)

    raw = ""
    last_err = None
    for attempt in range(2):
        try:
            raw = await _call_llm(full_prompt, COMMANDER_SYSTEM_PROMPT,
                                  purpose="plan", user_id=user_id, conversation_id=conversation_id)
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

    _human_summary, _steps_raw = "", raw
    try:
        from .llm_parser import _split_plan_output as _spo
        _human_summary, _steps_raw = _spo(raw)
        if _human_summary:
            print("[C1] plan human_summary len=" + str(len(_human_summary)))
    except Exception as _e_sp:
        print("[C1] split plan output failed: " + str(_e_sp))
    steps = _parse_plan(_steps_raw)

    if steps:
        steps = _normalize_steps(steps)
        steps, _fmt_errors = _validate_steps_format(steps)
        if steps:
            _pre_warns, _pre_blocks = _precheck_steps(steps)
            if _pre_warns:
                print(f"[precheck] warnings: {_pre_warns}")
            if _pre_blocks:
                print(f"[precheck] blocked: {_pre_blocks}")
                # return {"status": "no_plan", "reason": "precheck blocked: " + str(_pre_blocks)}
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
        return {"status": "no_plan", "message": "无法拆解任务", "task_id": task_id, "human_summary": _human_summary}

    print("[DIAG] 即将构建 task")
    task_id = f"t_{int(time.time() * 1000)}"

    is_draft = bool(require_confirmation)
    task = {
        "task_id": task_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "user_text": user_input,
        "human_summary": _human_summary,
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
            "human_summary": _human_summary,
            "conversation_id": conversation_id,
            "commander_id": commander_id,
            "executor_id": executor_id
        }

    # run_trace: 任务启动（L1 里程碑）
    try:
        from .. import trace_service as _trace_svc
        _trace_svc.emit(
            task.get("supervisor_run_id"), conversation_id, 1, "task_start",
            content="任务已拆解为 " + str(len(steps)) + " 步",
            status="running",
        )
    except Exception as _e_tr:
        print("[trace] task_start 写入失败: " + str(_e_tr))

    task_payload = {"task_id": task_id, "steps": steps}
    task_msg = "[TASK]:" + json.dumps(task_payload, ensure_ascii=False)
    _insert_message(conversation_id, task_msg, sender_agent_id=commander_id)

    return {
        "status": "planned",
        "task_id": task_id,
        "steps": steps,
        "human_summary": _human_summary,
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

    _failure_lines = []
    for _f in failed_info:
        _why = str(_f.get("failure_reason") or "")[:150]
        if _why:
            _failure_lines.append("- " + _why)
    try:
        with db_cursor() as _cur_c3:
            _cur_c3.execute(
                "SELECT content FROM safety_memory "
                "WHERE task_id=? AND memory_type='failure_pattern' "
                "ORDER BY id DESC LIMIT 3",
                (task.get("task_id"),),
            )
            for _mrow in _cur_c3.fetchall():
                _mtxt = (_mrow["content"] if isinstance(_mrow, dict) else _mrow[0]) or ""
                if _mtxt and _mtxt[:60] not in "\n".join(_failure_lines):
                    _failure_lines.append("- " + _mtxt[:150])
    except Exception as _e_c3:
        print("[C3] 读取失败记忆异常: " + str(_e_c3))
    failure_context = ""
    if _failure_lines:
        failure_context = "\n【已失败的方案（禁止重复）】\n" + "\n".join(_failure_lines[:6]) + "\n"

    strategy_context = ""
    _retry = int(task.get("retry_count") or 0)
    if _retry >= 2:
        _hints = []
        _all_fail = "\n".join(_failure_lines)
        if any(k in _all_fail for k in ("path 不合法", "路径", "文件不存在", "找不到文件")):
            _hints.append("禁止用绝对路径，改用相对路径（如 static/modules/xxx.js）；不确定就先 dir_tree")
        if any(k in _all_fail for k in ("grep", "熔断", "搜索失败")):
            _hints.append("禁止再用 grep_code，改用 run_python 手动扫描")
        if any(k in _all_fail for k in ("锚点", "old_snippet", "未找到原文", "anchor")):
            _hints.append("禁止再用 smart_edit，改用 file_replace_range（行号替换）或 file_write（整文件覆写）")
        if any(k in _all_fail for k in ("命令不在白名单", "禁止字符")):
            _hints.append("禁止用 shell 命令，改用 harness 工具")
        if _hints:
            strategy_context = ("\n【换策略铁律（第 " + str(_retry) + " 次重拆，必须换）】\n"
                                + "\n".join("- " + _h for _h in _hints) + "\n")

    prompt = f"""原任务：{task['user_text']}

已完成的步骤及结果：
{json.dumps(task['results'], ensure_ascii=False, indent=2)}

失败的步骤（需要你重新拆解）：
{json.dumps(failed_info, ensure_ascii=False, indent=2)}
{failure_context}{strategy_context}

请针对上述失败步骤重新拆解。要求：
1. 必须输出 JSON 数组，不要任何解释文字，不要 markdown 代码块
2. 每步格式二选一：
   - harness 调用：{{"step":1,"description":"...","type":"harness","module_id":"工具ID","params":{{...}}}}
   - shell 命令：{{"step":1,"description":"...","command":"dir core"}}
3. 【工具优先级】优先用 harness 工具，只有以下情况才用 command：
   - 运行 python / git / npm / pip
   - 执行系统脚本
   - 查看进程、端口、环境变量
   以下场景必须用 harness（禁止用 shell 命令代替）：
   - 读文件 → file_read（禁 type / cat / more / less / head / tail）
   - 搜代码 → grep_code（禁 findstr / find）
   - 列目录 → dir_tree（禁 dir /s）
   - 改文件 → file_patch
   - 检查语法 → verify_syntax
4. 【file_patch 参数铁律】必须提供以下三组之一，缺一不可：
   A. 精确片段：old_snippet + new_snippet + expected_count
   B. 锚点插入：anchor_pattern + position(before/after/replace_line) + new_content
   C. 整文件写：file_path + new_content（配合 create_if_missing 或 overwrite）
   禁止只传 file_path 而不传内容参数。
5. 【禁止的命令】copy / move / del / powershell / for / if / 重定向
6. 【占位符】用 {{{{stepN}}}} 引用前序步骤的输出（只引用成功的步骤）
7. 【别名纠正】如果失败原因是"检测到工具别名 xxx 被误用作 shell 命令"，必须改用：
   {{"type":"harness","module_id":"xxx","params":{{...}}}}
   不要把别名写成 command 字段。
8. 【precheck blocked 修正】如果失败原因是 "step N: file_patch 缺 new_content/old_snippet/anchor_pattern"，
   说明上一步 file_patch 参数不全，本轮必须补齐第 4 条要求的三组之一。
9. 【old_snippet 未找到】先用 file_read 读取目标文件对应行区间，从输出中逐字复制 old_snippet，
   禁止凭记忆写。然后用 file_patch 重试。
10. 【失败重试策略】
    - 文件不存在 → 用 dir_tree 确认路径，或改用 create_if_missing
    - 路径错误 → 先用 dir_tree 确认目录结构
    - 语法错误 → 换一种写法
    - 任务本身不可完成 → 输出 [{{"step":1,"description":"无法完成","command":"echo 任务无法完成，请用户确认"}}]

只输出 JSON 数组，现在开始："""

    try:
        raw = await _call_llm(prompt, REPLAN_SYSTEM_PROMPT, max_tokens=config.REPLAN_MAX_TOKENS,
                              purpose="replan", user_id=task.get("user_id"),
                              conversation_id=task.get("conversation_id"))
        print(f"[swarm] 重拆 LLM 返回长度: {len(raw)}, 前 300 字: {raw[:300]!r}")
    except Exception as e:
        print(f"[swarm] 重拆 LLM 异常: {e}")
        return None

    if not raw or not raw.strip():
        print(f"[swarm] 重拆 LLM 返回空，放弃重拆")
        return None

    steps = _parse_plan(raw)
    if steps:
        steps = _normalize_steps(steps)
        steps, _fmt_errors = _validate_steps_format(steps)
        if steps:
            _pre_warns, _pre_blocks = _precheck_steps(steps)
            if _pre_warns:
                print(f"[precheck] warnings: {_pre_warns}")
            if _pre_blocks:
                print(f"[precheck] blocked: {_pre_blocks}")
                # return {"status": "no_plan", "reason": "precheck blocked: " + str(_pre_blocks)}
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
