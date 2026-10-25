import json
from datetime import datetime
from ...db import db_cursor
from .constants import USE_STRUCTURED_REVIEW
from .runs import get_run

def build_next_input(run_id):
    run = get_run(run_id)
    if not run:
        return None
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    if not history:
        return run['goal']
    lines = ['目标：' + run['goal'], '', '已完成：']
    for h in history[-5:]:
        _rev = h.get('review') or {}
        _ok = _rev.get('goal_achieved') if isinstance(_rev, dict) else None
        _mark = '✅' if _ok else ('⚠️' if _ok is False else '·')
        lines.append(f"第 {h['round']} 轮 {_mark}：{(h.get('plan') or '')[:100]}")
        lines.append(f"  结果：{(h.get('exec') or '')[:250]}")

    # v0.39.1: 明确标注失败轮次，避免重复犯错
    _failed = []
    for h in history:
        _rev = h.get('review') or {}
        if isinstance(_rev, dict) and _rev.get('goal_achieved') is False:
            _failed.append(h)
    if _failed:
        lines.append('')
        lines.append('【需要避免的失败模式】')
        for h in _failed[-3:]:
            lines.append(f"- 第 {h['round']} 轮失败：{(h.get('plan') or '')[:120]}")

    lines.append('')
    lines.append('请判断目标是否已完成。如果已完成，只输出 [DONE]。否则输出下一步要做的任务（一句话）。')
    return chr(10).join(lines)


async def task_summarizer(task):
    print('[supervisor] task_summarizer 被调用, task_id=' + str(task.get('task_id')))
    import openai
    import asyncio
    from ... import config
    user_text = task.get('user_text', '')
    _orig_run_id = task.get('supervisor_run_id')
    if _orig_run_id:
        try:
            _orig_run = get_run(_orig_run_id)
            if _orig_run and _orig_run.get('goal'):
                user_text = _orig_run['goal']
        except Exception:
            pass
    results = task.get('results', [])
    steps = []
    for r in results:
        step = r.get('step', '?')
        desc = (r.get('description') or '')[:50]
        status = r.get('status', '?')
        cmd = r.get('command') or r.get('module_id') or ''
        out = (r.get('output') or r.get('answer') or '')[:300]
        steps.append(str(step) + '.[' + str(status) + '] ' + desc + ' | ' + str(cmd)[:50] + ' | ' + out)
    import json as _js
    _all_text = _js.dumps(results, ensure_ascii=False)
    for _r in results:
        if _r.get('rolled_back') or _r.get('syntax_ok') is False:
            _all_text += 'rolled_back | '
            _all_text += 'rolled_back | '
    # v0.35.1: 合法"未找到"判定（优先于可疑词检测）
    try:
        import re as _re_nf
        _answer_text = ''
        for _r in results:
            _answer_text += str(_r.get('output') or '') + ' '
            _answer_text += str(_r.get('command') or '') + ' '
        _nf_patterns = [r'未找到', r'不存在', r'没有找到', r'文件中没有']
        _has_not_found = any(_re_nf.search(p, _answer_text) for p in _nf_patterns)
        _has_empty_grep = False
        _has_any_answer = False
        for _r in results:
            _cmd = str(_r.get('command') or _r.get('module_id') or '')
            _out = str(_r.get('output') or '')
            if _cmd == 'grep_code' and 'count' in _out and ('"count": 0' in _out or "'count': 0" in _out):
                _has_empty_grep = True
            if _cmd == 'answer' and _r.get('status') == 'success':
                _has_any_answer = True
        if _has_not_found and _has_empty_grep and _has_any_answer:
            print('[supervisor] task_summarizer 合法未找到判定: grep 空 + answer 报告未找到 → 判完成')
            return {'goal_achieved': True, 'goal_reason': '目标不存在，已向用户报告', 'missing': [], 'next_hint': ''}

        # v0.35.2: 扩展——grep 空 + 任务含改/删动词 → 判目标不存在
        import re as _re_v2
        _action_pat = _re_v2.search(r'(改成|改为|修改|删除|删掉|更新|替换)', user_text)
        _any_grep_empty = False
        for _r in results:
            _cmd = str(_r.get('command') or _r.get('module_id') or '')
            _out = str(_r.get('output') or '')
            if _cmd == 'grep_code' and '"count": 0' in _out:
                _any_grep_empty = True
                break
        _has_any_file_patch = any(
            str(_r.get('command') or _r.get('module_id') or '') == 'file_patch'
            for _r in results
        )
        if False and _action_pat and _any_grep_empty and not _has_any_file_patch:
            print('[supervisor] task_summarizer 目标不存在判定: grep 空 + 含改/删动词 + 无 file_patch → 判完成')
            return {
                'goal_achieved': True,
                'goal_reason': '目标不存在，无法执行改/删操作',
                'missing': [],
                'next_hint': '',
            }
    except Exception as _e_nf:
        print('[supervisor] 未找到判定异常: ' + str(_e_nf))

    # v0.36.0: file_patch 成功判定（优先于可疑词检测）
    # 场景：任务含"创建/写入/生成 xxx 文件"，且 file_patch 已成功
    # 不再因 answer 里出现"已完成"等词而误判未完成
    try:
        _has_file_patch_success = False
        _has_any_retry = False
        _has_final_answer = False
        for _r in results:
            _cmd = str(_r.get('command') or _r.get('module_id') or '')
            _status = _r.get('status', '')
            _mode = str(_r.get('mode') or '')
            if _cmd == 'file_patch' and _status == 'success':
                _has_file_patch_success = True
            if _status in ('failed', 'blocked', 'timeout', 'error'):
                _has_any_retry = True
            if _cmd == 'answer' and _status == 'success':
                _has_final_answer = True

        _create_words = ['创建', '写入', '生成', '写一个', '写个', '新建', '覆盖']
        _is_create_task = any(w in user_text for w in _create_words)

        if False and _is_create_task and _has_file_patch_success and not _has_any_retry:
            print('[supervisor] task_summarizer file_patch 成功判定 → 判完成')
            return {
                'goal_achieved': True,
                'goal_reason': '文件已成功创建/写入',
                'missing': [],
                'next_hint': '',
            }
    except Exception as _e_fp:
        print('[supervisor] file_patch 判定异常: ' + str(_e_fp))

    # v0.43.1: split_block / delete_block 成功判定
    try:
        _block_tools = ('split_block', 'delete_block')
        _has_block_success = False
        _has_any_fail = False
        for _r in results:
            _cmd = str(_r.get('command') or _r.get('module_id') or '')
            _status = _r.get('status', '')
            _out = str(_r.get('output') or '')
            if _cmd in _block_tools and _status == 'success' and '"success": true' in _out:
                _has_block_success = True
            if _status in ('failed', 'blocked', 'timeout', 'error'):
                _has_any_fail = True
        _is_complex_task = any(k in user_text for k in ['并', '然后', '接着', '加', '改', '修复', '替换'])
        if _has_block_success and not _has_any_fail and not _is_complex_task:
            print('[supervisor] task_summarizer block 工具成功判定 → 判完成')
            return {
                'goal_achieved': True,
                'goal_reason': '拆分/删除工具成功完成',
                'missing': [],
                'next_hint': '',
            }
    except Exception as _e_bt:
        print('[supervisor] block 工具判定异常: ' + str(_e_bt))

    # v0.47.0: answer 含明确完成信号 → 直接判完成（不依赖可疑词）
    try:
        _done_signals = ['已完成', '已迁移', '已拆分', '已删除', '语法通过', '语法检查通过', '已恢复', '迁移完成', '拆分完成']
        _has_done_answer = False
        _has_any_fail2 = False
        _has_success_tool = False
        for _r in results:
            _cmd2 = str(_r.get('command') or _r.get('module_id') or '')
            _st2 = _r.get('status', '')
            _out2 = str(_r.get('answer') or _r.get('output') or '')
            if _st2 in ('failed', 'blocked', 'timeout', 'error'):
                _has_any_fail2 = True
            if _st2 == 'success' and _cmd2 and _cmd2 != 'answer':
                _has_success_tool = True
            if _cmd2 == 'answer' and _st2 == 'success':
                if any(_sig in _out2 for _sig in _done_signals):
                    _has_done_answer = True
        _fake_words = ['test']
        _all_fake_txt = "".join(str(_r.get("answer") or _r.get("output") or "") for _r in results)
        _all_fake_txt = "".join(str(_r.get("answer") or _r.get("output") or "") for _r in results)
        _fake_words = ['test']
        _is_fake = any(w in _all_fake_txt.lower() for w in _fake_words)
        if _has_done_answer and _has_success_tool and not _has_any_fail2 and not _is_fake:
            print('[supervisor] task_summarizer answer 含完成信号 → 判完成')
            return {
                'goal_achieved': True,
                'goal_reason': '工具成功 + answer 含完成信号',
                'missing': [],
                'next_hint': '',
            }
    except Exception as _e_da:
        print('[supervisor] answer 完成信号判定异常: ' + str(_e_da))


    _suspicious_kws = ['剩余', '请继续', '请分批', '请再发', '未完成', '待完成',
                       'rolled_back', 'verify fail', '已回滚', '请回复',
                       '请确认', '请检查', '请用户', '需要用户', '请先', '请提供',
                       '发起第2轮', '发起第 2 轮', '发起第3轮', '发起第 3 轮', '下一轮', '请发起',
                       '第1轮完成', '第 1 轮完成', '本轮完成', '继续核对', '继续验证']
    _neg_contexts = ["未做修改", "未做改动", "不需要修改", "无需修改", "不影响", "未做变更"]
    _text_clean = _all_text
    for _neg in _neg_contexts:
        _text_clean = _text_clean.replace(_neg, "")
    _hit = [kw for kw in _suspicious_kws if kw in _text_clean]
    _force_continue = bool(_hit)
    if _hit:
        print('[supervisor] task_summarizer 代码规则命中: ' + ','.join(_hit) + ' —— 继续调 LLM 生成具体 hint')

    # v0.19: 终轮提示词——answer 里含 ≥3 条 file:line 格式视为完成
    if not _hit:
        import re as _re_final
        _ans_all = ''
        for _r in results:
            _ans_all += str(_r.get('answer') or _r.get('output') or '') + ' | '
        _fl_count = len(_re_final.findall(r'[\w/\.\-]+\.\w+:\d+|\b\d+行', _ans_all))
        _is_modify = any(k in user_text for k in ['改', '修', '加', '删', '替换', '写'])
        _has_patch = any(str(_r.get('command') or _r.get('module_id') or '') == 'file_patch' and _r.get('status') == 'success' for _r in results)
        if _fl_count >= 3 and (not _is_modify or _has_patch):
            print(f'[supervisor] task_summarizer 终轮提示词命中: {_fl_count} 条 file:line')
            return {'goal_achieved': True, 'goal_reason': f'报告含 {_fl_count} 条 file:line 具体结论', 'missing': [], 'next_hint': ''}

    # v0.38.0: 假完成拦截 —— 任务含修改动词但无 file_patch 成功
    try:
        _action_kws = ['改成', '改为', '修改', '删除', '删掉', '新增', '添加', '创建', '写入', '替换', '移动', '插入', '修复']
        _need_patch = any(k in user_text for k in _action_kws)
        _has_patch_ok = any(
            str(r.get('command') or r.get('module_id') or '') == 'file_patch' and r.get('status') == 'success'
            for r in results
        )
        if _need_patch and not _has_patch_ok:
            _any_not_found = any(
                ('未找到' in str(r.get('output') or '') or '不存在' in str(r.get('output') or ''))
                for r in results
            )
            if not _any_not_found:
                print('[supervisor] task_summarizer 假完成拦截: 任务含修改动词但无 file_patch 成功')
                return {'goal_achieved': False, 'goal_reason': '任务要求修改但无 file_patch / ssh_exec / run_python / run_forever 任何写操作成功凭证', 'missing': ['实际修改'], 'next_hint': '用 file_patch 实际执行修改，禁止只报告不修改'}
    except Exception as _e_fake:
        print('[supervisor] 假完成判定异常: ' + str(_e_fake))
    
    _sys_prompt = '你是任务完成度评估器。请只输出 JSON：{"goal_achieved": true 或 false, "goal_reason": "理由", "missing": ["未完成项"], "next_hint": "下一步具体命令"}。判断规则：第一，逐条列出原始目标里的每一个要求（编号1/2/3/4），逐一核对是否真的通过 file_patch/file_read/run_python 等工具执行过，没执行过的放入missing。第二，如果执行结果里出现"剩余""请继续""请分批""请再发""未完成"等字眼，强制 goal_achieved=false。第三，把用户目标拆成子任务逐一核对，不因某一子任务完成就判整体完成。第四，如果用户目标里显式写了"第 N 轮"、"步骤 N"、"1./2./3."等分步描述，必须逐条核对——前 N-1 步完成不算整体完成，必须最后一步（通常是"生成报告"/"输出结论"/"用 answer"/"写入文件"）也执行了才算 goal_achieved=true。第五，只读了数据但没有分析/报告/输出的任务，视为未完成。目标含总结/回答/分析/说明，必须有文字产出（answer 或写文件）。目标含改/加/实现/修复，必须有成功 file_patch。目标含读/查看/列出且没有分步描述时，有 file_read 或 dir 即可。第六，如果 answer 输出里已包含 ≥3 条 "文件:行号" 格式的具体结论（如 chat.css:105），且未出现"剩余/请再发/下一轮/未完成"等词，判 goal_achieved=true。next_hint 必须具体写清工具+文件路径+动作，不许写重新探测。'
    _user_prompt = '【用户目标】' + user_text + chr(10) + '【执行步骤】' + chr(10).join(steps)
    client = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=30)
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{'role': 'system', 'content': _sys_prompt}, {'role': 'user', 'content': _user_prompt}],
            temperature=0.2,
            max_tokens=3000
        )
        raw = resp.choices[0].message.content.strip()
        i = raw.find('{')
        i = raw.find('{')
        j = raw.rfind('}')
        if i >= 0 and j > i:
            try:
                _parsed = json.loads(raw[i:j+1])
            except Exception:
                _parsed = {'goal_achieved': False, 'goal_reason': 'json parse failed', 'missing': [], 'next_hint': '重新探测'}
            if _force_continue:
                _parsed['goal_achieved'] = False
                if not _parsed.get('missing'):
                    _parsed['missing'] = _hit
                _hint = _parsed.get('next_hint') or ''
                if not _hint or _hint in ('重新探测', '请继续完成剩余部分'):
                    _parsed['next_hint'] = '继续基于已读数据完成任务：先 verify_claim 核对关键行，再 answer 输出完整报告'
            return _parsed
    except Exception as e:
        print('[supervisor] task_summarizer 失败: ' + str(e))
        return {'goal_achieved': False, 'goal_reason': 'LLM failed', 'next_hint': '重新探测'}



async def decide_next_step(run_id):
    import openai
    import asyncio
    from ... import config
    run = get_run(run_id)
    if not run:
        return None
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    history_text = ''
    for h in history[-5:]:
        history_text += '第 ' + str(h.get('round', '?')) + ' 轮：' + (h.get('plan') or '')[:80] + chr(10)
        history_text += '  结果：' + (h.get('exec') or '')[:300] + chr(10)
    try:
        from ... import harness_runtime as _hr
        _tools = _hr.harness_runtime.list_tools()
        _names = ' / '.join([getattr(t, 'module_id', '') for t in _tools if getattr(t, 'module_id', '')])
        _tool_line = '可用工具：' + _names
    except Exception:
        _tool_line = '可用工具：file_read / file_patch'
    _sys_prompt = '你是 SASES 自主调度者。请判断下一步，只输出 JSON：{"action": "probe" 或 "build_harness" 或 "execute" 或 "done", "task": "一句话描述"}' + chr(10) + 'probe=先读代码；build_harness=缺工具先建；execute=可以改代码；done=目标达成' + chr(10) + '注意：如果最近的执行结果里有 blocked 或 retry，说明上一步失败，不能判定 done，应继续 probe 或 execute 修正。' + chr(10) + '另外：只有确认用户目标的所有子任务都完成，才能判定 done。只改了 1 处不代表全部完成时，应继续 execute 改其他地方。判断标准：回顾原始目标的每一个关键词，逐一确认是否已实现。' + chr(10) + '关键规则：如果用户目标包含实现/打通/改/加/建/修复等动作词，而 history 里从来没有出现过 file_patch 或 harness_reload，说明只做了探测没做实际修改，此时不能 done，必须输出 execute。' + chr(10) + '补充规则：如果 history 里已经读到目标文件的具体行号/代码片段/参数格式，说明探测够了，下一步必须输出 execute，不要再 probe。饱和判定：如果最近 2 轮的 exec 内容高度相似（同一路径、同一文件、同一结果），说明探测饱和，应输出 done。不要因为没总结就继续探测。'
    _user_prompt = '【目标】' + run['goal'] + chr(10) + chr(10) + '【已完成】' + chr(10) + (history_text or '(无)') + chr(10) + _tool_line
    client = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=30)
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{'role': 'system', 'content': _sys_prompt}, {'role': 'user', 'content': _user_prompt}],
            temperature=0.3,
            max_tokens=200
        )
        raw = resp.choices[0].message.content.strip()
        i = raw.find('{')
        j = raw.rfind('}')
        if i >= 0 and j > i:
            _result = json.loads(raw[i:j+1])
            _goal = run.get('goal', '')
            _action_words = ['实现', '打通', '改', '加', '建', '修复', '增加', '添加', '删除', '创建', '完成']
            _need_action = any(w in _goal for w in _action_words)
            _history_str = json.dumps(history, ensure_ascii=False)
            _has_patch = '[success] file_patch' in _history_str or '[success]harness_reload' in _history_str or '[success] harness_reload' in _history_str
            if _need_action and not _has_patch and _result.get('action') == 'done':
                print('[supervisor] 强制覆盖 done → execute（历史无 file_patch）')
                _result['action'] = 'execute'
                _result['task'] = '根据前面探测结果实际修改代码，完成目标：' + _goal[:100]
            return _result
        return {'action': 'done', 'task': 'parse failed'}
    except Exception as e:
        print('[supervisor] decide_next_step 失败: ' + str(e))
        return {'action': 'done', 'task': 'LLM failed'}



# (重复的 build_context 已删除，用第 12 行的版本)
