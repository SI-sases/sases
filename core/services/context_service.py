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

    # head anchor: earliest user messages once the conversation outgrows the recent window
    try:
        _head_lines = []
        with db_cursor() as cur:
            cur.execute('SELECT id FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?', (conversation_id, _hist_limit))
            _win = [x['id'] for x in cur.fetchall()]
            if len(_win) >= _hist_limit:
                cur.execute('SELECT id, content FROM messages WHERE conversation_id=? AND sender=? AND id<? ORDER BY id ASC LIMIT 6', (conversation_id, 'user', min(_win)))
                for x in cur.fetchall():
                    _ht = str(x['content'] or '').strip()
                    if not _ht or _ht.startswith(('*0', '[TASK]:', '[STEP_DONE]:', '[SUMMARY]:', '[RED_PACKET]')):
                        continue
                    _head_lines.append('用户: ' + _ht[:600])
                    if len(_head_lines) >= 2:
                        break
        if _head_lines:
            parts.append('【会话开头（更早的内容，供参考）】' + NL + NL.join(_head_lines))
    except Exception as _he:
        print('[context] head anchor skipped: ' + str(_he))

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

    # P2-3: 注入活跃任务快照（区别于 task_context，这是运行时状态）
    try:
        from core.services import task_state_service as _ts_p23
        _snap_p23 = getattr(_ts_p23, 'get_snapshot_fresh', _ts_p23.get_snapshot)(conversation_id) if conversation_id else {}
        if _snap_p23 and _snap_p23.get("goal") and _snap_p23.get("status") in ("running", "paused", "failed"):
            _prog_p23 = _snap_p23.get("progress", {})
            _task_hdr = (
                "【当前运行任务状态】" + NL
                + "目标：" + str(_snap_p23.get("goal", "")) + NL
                + "状态：" + str(_snap_p23.get("status", ""))
                + "  进度：" + str(_prog_p23.get("completed", 0)) + "/" + str(_prog_p23.get("total", 0)) + NL
            )
            if _snap_p23.get("current_step_desc"):
                _task_hdr += "当前步骤：" + str(_snap_p23.get("current_step_desc")) + NL
            _fs_p23 = _snap_p23.get("failed_summary") or []
            if _fs_p23:
                _last_p23 = _fs_p23[-1]
                _task_hdr += "最近失败：步骤" + str(_last_p23.get("step", "")) + " · " + str(_last_p23.get("reason", ""))[:80] + NL
            parts.append(_task_hdr)
    except Exception as _e_p23:
        print("[P2-3] 注入任务快照失败: " + str(_e_p23))

    base = (project_ctx + ' 【用户问】 ' + content) if project_ctx else content
    if parts:
        return (NL + NL).join(parts) + (NL + NL) + base
    return base
