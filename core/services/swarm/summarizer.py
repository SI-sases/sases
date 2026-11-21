from .prompts import SUMMARY_SYSTEM_PROMPT
from typing import List, Dict, Any
from ... import config
from .llm_parser import _call_llm

def _summary_sender(task):
    """优先用 supervisor_id，回退 commander_id"""
    return task.get("supervisor_id") or task.get("commander_id")



def _infer_domain(results):
    for r in results:
        if isinstance(r, dict) and r.get('module_id') == 'file_patch' and r.get('status') == 'success':
            return 'dev_edit'
    return 'dev_probe'



def _prepend_changes(summary, results):
    """在 summary 前强制拼上 file_patch 成功的文件清单"""
    try:
        _files = []
        for _r in (results or []):
            _cmd = str(_r.get('command') or _r.get('module_id') or '')
            if _cmd != 'file_patch':
                continue
            if _r.get('status') != 'success':
                continue
            _fp = None
            _params = _r.get('params')
            if isinstance(_params, dict):
                _fp = _params.get('file_path')
            if not _fp:
                import re as _re_fp
                _out = str(_r.get('output') or '')
                _m = _re_fp.search(r'"file_path"\s*:\s*"([^"]+)"', _out)
                if _m:
                    _fp = _m.group(1)
            if _fp and _fp not in _files:
                _files.append(_fp)
        if _files:
            return '【改动】' + ' | '.join(_files) + chr(10) + summary
    except Exception as _e:
        print('[swarm] _prepend_changes 失败: ' + str(_e))
    return summary



async def _summarize(user_text: str, results: List[Dict[str, Any]], user_id: int = None, task_id: str = None, conversation_id: int = None) -> str:
    # [AUDIT-1] 结构化任务总结：供 C2 统计、下一轮 plan 读取（v0.45.0）
    try:
        if user_id and task_id and results:
            import json as _json_audit
            _tool_stats = {}
            _files_changed = []
            for _r in results:
                _tool = str(_r.get("module_id") or _r.get("command") or "").strip()
                _tool = _tool.split()[0].lower() if _tool else ""
                if _tool:
                    _st = _tool_stats.setdefault(_tool, {"count": 0, "failed": 0})
                    _st["count"] += 1
                    if _r.get("status") != "success":
                        _st["failed"] += 1
                if _tool in ("smart_edit", "file_write", "file_replace_range"):
                    _params = _r.get("params")
                    _fp = _params.get("file_path") if isinstance(_params, dict) else None
                    if _fp and _fp not in _files_changed:
                        _files_changed.append(_fp)
            _failed_strategies = [str(_r.get("reason") or "")[:120] for _r in results if _r.get("review") == "retry"]
            _audit = {
                "task_id": str(task_id),
                "conversation_id": conversation_id,
                "goal": str(user_text or "")[:300],
                "outcome": "success" if not _failed_strategies else "partial_success",
                "files_changed": _files_changed,
                "tools_used": [{"tool": k, "count": v["count"], "failed": v["failed"]} for k, v in _tool_stats.items()],
                "failed_strategies": _failed_strategies[:5],
                "successful_strategies": [k for k, v in _tool_stats.items() if v["failed"] == 0],
            }
            from .. import memory_service as _ms_audit
            _ms_audit.remember(
                user_id=user_id,
                memory_type="task_summary",
                content=_json_audit.dumps(_audit, ensure_ascii=False),
                task_id=str(task_id),
                importance=0.7,
                enable_dedup=False,
            )
            print("[AUDIT] task_summary written: " + str(task_id))
    except Exception as _e_audit:
        print("[AUDIT] task_summary 写入失败: " + str(_e_audit))

    # P0：记录经验 pattern（静默失败，不阻塞主流程）
    try:
        if user_id and task_id and results:
            from .. import pattern_service
            n = pattern_service.record_pattern(user_id, task_id, _infer_domain(results), results)
            if n:
                print(f"[swarm] 已记录 {n} 条 pattern")
    except Exception as e:
        print(f"[swarm] pattern 记录失败（已忽略）: {e}")

    # 自动快照（方案 C：仅当任务包含 file_patch 成功步骤时）
    try:
        _has_patch = any(
            r.get("command") == "file_patch" and r.get("status") == "success"
            for r in results
        )
        if _has_patch and task_id:
            import subprocess as _sp
            import os as _os
            _repo = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            _msg = f"auto: {task_id}"
            _sp.run("git add -A", shell=True, cwd=_repo, capture_output=True, encoding="utf-8", errors="replace")
            _r = _sp.run(f'git commit -m "{_msg}"', shell=True, cwd=_repo, capture_output=True, encoding="utf-8", errors="replace")
            if _r.returncode == 0:
                print(f"[swarm] 已自动快照: {_msg}")
            else:
                print(f"[swarm] 自动快照跳过")
    except Exception as _e:
        print(f"[swarm] 自动快照失败: {_e}")


    # 写入执行笔记（v0.17.0）
    # 隔离：任务执行产生的笔记不写入个人项目库（避免污染用户知识库检索）
    _ISOLATE_EXECUTION_NOTE = True
    try:
        if user_id and task_id and results and not _ISOLATE_EXECUTION_NOTE:
            from .. import project_service
            _digest = ' | '.join([str(r.get('step')) + '.' + str(r.get('status', '?')) for r in results[:5]])
            _outcome = 'success' if all(r.get('review') != 'retry' for r in results) else 'partial'
            _preview = ' | '.join([str(r.get('description', ''))[:30] for r in results[:3]])
            project_service.import_execution_note(
                task_id=task_id, user_id=user_id,
                user_input=user_text, summary=_preview,
                steps_digest=_digest, outcome=_outcome
            )
    except Exception as e:
        print(f"[swarm] 执行笔记写入失败: {e}")


    result_lines = []
    for r in results:
        _line = f"步骤{r['step']}({r['description']}): {r['status']} [审核:{r.get('review','?')}]"
        _out = (r.get('output') or '').strip()
        if _out:
            _out = _out.replace(chr(10), chr(10) + '    ')[:12000]
            _line += chr(10) + '  工具输出:' + chr(10) + '    ' + _out
        result_lines.append(_line)
    result_text = chr(10).join(result_lines)
    prompt = f"【背景】用户请求：{user_text}\n\n【执行过程】\n{result_text}\n\n【输出格式】固定三段，简洁：\n1. 做了什么：一句话概括\n2. 结果：具体结果（文件/数据/答案原样呈现）\n3. 下一步：建议或可选的后续操作\n不要重复用户请求，不要输出 JSON，不要标题以外的格式说明。"
    try:
        _raw_sum = await _call_llm(prompt, SUMMARY_SYSTEM_PROMPT, max_tokens=config.SUMMARY_MAX_TOKENS,
                                   purpose="summary", user_id=user_id, conversation_id=conversation_id)
        return _prepend_changes(_raw_sum, results)
    except Exception:
        return _prepend_changes("任务执行完成。", results)
