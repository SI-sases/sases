from .prompts import SUMMARY_SYSTEM_PROMPT
from typing import List, Dict, Any
from ... import config
from .llm_parser import _call_llm

def _summary_sender(task):
    """优先用 supervisor_id，回退 commander_id"""
    return task.get("supervisor_id") or task.get("commander_id")



def _infer_domain(results):
    probe_tools = ("file_read", "dir_tree", "grep_code")
    has_edit = False
    all_probe = True
    for r in results:
        mid = r.get("module_id") if isinstance(r, dict) else None
        st = r.get("status") if isinstance(r, dict) else None
        if mid == "file_patch" and st == "success":
            has_edit = True
        if mid not in probe_tools:
            all_probe = False
    if has_edit:
        return "dev_edit"
    if all_probe:
        return "dev_probe"
    return "dev"


async def _summarize(user_text: str, results: List[Dict[str, Any]], user_id: int = None, task_id: str = None) -> str:
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
    prompt = f"【背景】用户请求：{user_text}\n\n【执行过程】\n{result_text}\n\n【要求】请直接输出最终结果，用于展示给用户。\n- 绝对不要重复用户请求的内容。\n- 如果工具返回了具体内容（文件内容、数据、答案），直接原样呈现。\n- 如果任务只是完成某个操作（如改代码、发消息），用一句话说明完成情况。\n- 直接输出结果本身，不要任何前缀、标题、格式说明。"
    try:
        return await _call_llm(prompt, SUMMARY_SYSTEM_PROMPT, max_tokens=config.SUMMARY_MAX_TOKENS)
    except Exception:
        return "任务执行完成。"
