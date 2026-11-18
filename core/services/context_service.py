# core/services/context_service.py
from ..db import db_cursor
from . import memory_service

NL = chr(10)


def build_enriched_prompt(user_id, conversation_id, content, project_ctx):
    parts = []

    try:
        for _tc in memory_service.recall_by_type(user_id, 'task_context', top_k=3):
            parts.append('【当前任务（必读）】' + NL + str(_tc.get('content', '')))
    except Exception as _tc_e:
        print('[context] task_context recall failed: ' + str(_tc_e))

    hist_lines = []
    _hist_limit = 8 if parts else 20
    try:
        with db_cursor() as cur:
            cur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?', (conversation_id, _hist_limit))
            rows = list(cur.fetchall())
        for r in reversed(rows):
            t = str(r['content'] or '')
            if t.startswith(('[TASK]:', '[STEP_DONE]:', '[SUMMARY]:', '[RED_PACKET]')):
                continue
            who = '用户' if r['sender'] == 'user' else 'AI'
            hist_lines.append(who + ': ' + t[:300])
    except Exception as e:
        print('[context] history failed: ' + str(e))

    if hist_lines:
        parts.append('【会话历史】' + NL + NL.join(hist_lines))

    succ = ''
    try:
        for m in memory_service.recall(user_id=user_id, query=content, top_k=4, memory_type='task_result'):
            succ += str(m.get('content', ''))[:300] + NL
    except Exception as e:
        print('[context] success recall failed: ' + str(e))
    if succ:
        parts.append('【成功经验】' + NL + succ)

    fail = ''
    try:
        for m in memory_service.recall(user_id=user_id, query=content, top_k=2, memory_type='failure_pattern'):
            fail += str(m.get('content', ''))[:120] + NL
    except Exception as e:
        print('[context] failure recall failed: ' + str(e))
    if fail:
        parts.append('【失败教训】' + NL + fail)

    base = (project_ctx + ' 【用户问】 ' + content) if project_ctx else content
    if parts:
        return (NL + NL).join(parts) + (NL + NL) + base
    return base
