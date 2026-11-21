# -*- coding: utf-8 -*-
"""统一上下文构建器：chat / plan / intent 三模式共用"""
import os
from ..db import db_cursor

DEFAULT_BUDGET = int(os.getenv("SASES_CTX_BUDGET", "48000"))
_PROTOCOL_PREFIXES = ('[TASK]:', '[STEP_DONE]:', '[SUMMARY]:', '[RED_PACKET]', '[SUPERVISOR_PROGRESS]:')


def estimate_tokens(text):
    """粗估 token：中文 1.5 字/token，英文 4 字/token"""
    if not text:
        return 0
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - cn
    return int(cn / 1.5 + other / 4) + 1


def _load_history(conversation_id, max_count=30):
    """读最近 N 条消息完整原文，跳过协议消息"""
    if not conversation_id:
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT sender, content, msg_type FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                (conversation_id, max_count)
            )
            rows = list(cur.fetchall())
    except Exception as e:
        print('[CTX] load_history failed: ' + str(e))
        return []
    result = []
    for r in reversed(rows):
        if isinstance(r, dict):
            sender, content, mtype = r.get('sender'), r.get('content'), r.get('msg_type')
        else:
            sender, content, mtype = r[0], r[1], (r[2] if len(r) > 2 else None)
        t = str(content or '')
        if not t:
            continue
        if any(t.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        who = '用户' if sender == 'user' else 'AI'
        result.append({'who': who, 'content': t, 'is_doc': mtype == 'doc_paste'})
    return result


def _build_history_section(history, budget_remaining):
    """从新到旧分层拼装，返回 (text, used_tokens)"""
    n = len(history)
    if n == 0:
        return '', 0
    accepted = []
    used = 0
    for i in range(n - 1, -1, -1):  # 从最新往旧
        msg = history[i]
        from_end = n - i
        if msg.get('is_doc') and from_end <= 5:
            limit = None
        elif from_end <= 3:
            limit = None
        elif from_end <= 10:
            limit = 2000
        elif from_end <= 20:
            limit = 800
        else:
            limit = 300
        content = msg['content']
        if limit is not None and len(content) > limit:
            content = content[:limit]
        line = msg['who'] + ': ' + content
        t = estimate_tokens(line)
        if used + t > budget_remaining:
            print(f'[CTX] history truncated at #{from_end} (from tail), budget full')
            break
        accepted.append(line)
        used += t
    accepted.reverse()
    return '【会话历史】\n' + '\n\n'.join(accepted), used


def build_context(user_id, conversation_id, content, mode='chat'):
    """
    统一上下文构建
    mode: 'chat' / 'plan' / 'intent'
    返回: (prompt_text, stats_dict)
    """
    budget = DEFAULT_BUDGET
    stats = {'mode': mode, 'budget': budget, 'used': 0, 'sections': {}}
    history = _load_history(conversation_id, max_count=30)

    # 意图判定模式：只要最近历史，不做检索
    if mode == 'intent':
        hist_text, t_hist = _build_history_section(history, 8000)
        final = (hist_text + '\n\n用户最新: ' + content) if hist_text else content
        stats['sections']['history'] = t_hist
        stats['total'] = estimate_tokens(final)
        print(f"[CTX] mode=intent total={stats['total']}")
        return final, stats

    parts = []

    # 1. task_context（最高优先，永不截断）
    task_ctx_text = ''
    try:
        from .memory_service import recall_by_type
        for _tc in recall_by_type(user_id, 'task_context', top_k=3):
            task_ctx_text += str(_tc.get('content', '')) + '\n\n'
    except Exception as e:
        print('[CTX] task_context failed: ' + str(e))
    if task_ctx_text:
        t_tc = estimate_tokens(task_ctx_text)
        parts.append('【当前任务】\n' + task_ctx_text)
        stats['used'] += t_tc
        stats['sections']['task_ctx'] = t_tc

    # 2. 会话历史（占大块）
    hist_budget = max(8000, budget - stats['used'] - 12000)
    hist_text, t_hist = _build_history_section(history, hist_budget)
    if hist_text:
        parts.append(hist_text)
        stats['used'] += t_hist
        stats['sections']['history'] = t_hist

    # 3. 检索内容（仅 plan 模式，且预算允许）
    if mode == 'plan':
        # 成功经验
        try:
            from .memory_service import recall as _rec
            succ = ''
            for m in _rec(user_id=user_id, query=content, top_k=4, memory_type='task_result'):
                succ += str(m.get('content', ''))[:1000] + '\n\n'
            if succ:
                t = estimate_tokens(succ)
                if stats['used'] + t <= budget:
                    parts.append('【成功经验】\n' + succ)
                    stats['used'] += t
                    stats['sections']['success'] = t
        except Exception as e:
            print('[CTX] success recall failed: ' + str(e))

        # 失败教训
        try:
            from .memory_service import recall as _rec
            fail = ''
            for m in _rec(user_id=user_id, query=content, top_k=2, memory_type='failure_pattern'):
                fail += str(m.get('content', ''))[:800] + '\n\n'
            if fail:
                t = estimate_tokens(fail)
                if stats['used'] + t <= budget:
                    parts.append('【失败教训】\n' + fail)
                    stats['used'] += t
                    stats['sections']['failure'] = t
        except Exception as e:
            print('[CTX] failure recall failed: ' + str(e))

        # 项目库
        try:
            from .project_service import retrieve_project_chunks, format_chunks_for_prompt
            chunks = retrieve_project_chunks(content, top_k=3, user_id=user_id)
            proj = format_chunks_for_prompt(chunks, max_chars_per_chunk=1500)
            if proj:
                t = estimate_tokens(proj)
                if stats['used'] + t <= budget:
                    parts.append('【项目资料】\n' + proj)
                    stats['used'] += t
                    stats['sections']['project'] = t
        except Exception as e:
            print('[CTX] project recall failed: ' + str(e))

    # 4. 拼装最终
    body = '\n\n'.join(parts)
    final = (body + '\n\n【用户问】\n' + content) if body else content
    stats['total'] = estimate_tokens(final)
    print(f"[CTX] mode={mode} total={stats['total']}/{budget} sections={stats['sections']}")
    return final, stats
