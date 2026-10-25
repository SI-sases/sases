import time as _ctx_time
from ...db import db_cursor
from .constants import _CTX_CACHE, _CTX_TTL, _CTX_MAX

def _ctx_key(user_id, conversation_id, mode, supervisor_id, query):
    return (user_id, conversation_id, mode, supervisor_id, (query or '')[:50])


def build_context(user_id, conversation_id, query, mode='execute', supervisor_id=None):
    _ck = _ctx_key(user_id, conversation_id, mode, supervisor_id, query)
    _ct = _ctx_time.time()
    if _ck in _CTX_CACHE:
        _cts, _cval = _CTX_CACHE[_ck]
        if _ct - _cts < _CTX_TTL:
            print('[supervisor] build_context 缓存命中')
            return _cval
        else:
            del _CTX_CACHE[_ck]
    parts = []
    try:
        _hard_skip = ('[TASK]:', '[TASK_DRAFT]:', '[RETRY_TASK]:', '[RED_PACKET]:', '[IMAGE]:')
        with db_cursor() as cur:
            cur.execute(
                "SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 80",
                (conversation_id,),
            )
            rows = cur.fetchall()
        _chat_lines = []
        _summary_line = None
        _step_lines = []
        for row in reversed(rows):
            sender = row["sender"] if "sender" in row.keys() else "?"
            content = row["content"] or ""
            if any(content.startswith(p) for p in _hard_skip):
                continue
            if content.startswith('[SUMMARY]:'):
                _summary_line = "任务总结：" + content[10:][:150]
                continue
            if content.startswith('[STEP_DONE]:'):
                try:
                    import json as _json
                    d = _json.loads(content[12:])
                    desc = (d.get('description') or '')[:40]
                    status = d.get('status', '?')
                    out = (d.get('output') or '')[:80]
                    _step_lines.append(str(d.get('step', '?')) + '.[' + status + '] ' + desc + ' → ' + out)
                except Exception:
                    pass
                continue
            if not content.strip():
                continue
            _chat_lines.append(sender + "：" + content[:100])
        for line in _chat_lines[-20:]:
            parts.append(line)
        if _step_lines:
            parts.append("执行步骤：" + " | ".join(_step_lines[-3:]))
        if _summary_line:
            parts.append(_summary_line)
    except Exception as e:
        print("[supervisor] build_context 历史读取失败: " + str(e))
    try:
        from .. import memory_service
        mems = memory_service.recall(user_id, query, 2)
        for m in (mems or []):
            mc = (m.get("content") or "")[:100] if isinstance(m, dict) else ""
            if mc:
                parts.append("记忆：" + mc)
    except Exception as e:
        print("[supervisor] build_context 记忆读取失败: " + str(e))
    if mode == 'chat':
        _allow_project = bool(supervisor_id) and supervisor_id.startswith('sases_assistant')
        if _allow_project:
            try:
                from .. import project_service
                _chunks = project_service.retrieve_project_chunks(query, top_k=3, user_id=user_id)
                if _chunks:
                    _pctx = project_service.format_chunks_for_prompt(_chunks)
                    if _pctx:
                        parts.append(_pctx[:1000])
            except Exception as _e:
                print('[supervisor] chat mode 项目库失败: ' + str(_e))
        try:
            with db_cursor() as _cur:
                _cur.execute('SELECT user_input, summary FROM execution_notes WHERE user_id=? ORDER BY id DESC LIMIT 5', (user_id,))
                _rows = _cur.fetchall()
            if _rows:
                _lines = []
                for _r in _rows[:3]:
                    _ui = (_r['user_input'] if 'user_input' in _r.keys() else '') or ''
                    _sm = (_r['summary'] if 'summary' in _r.keys() else '') or ''
                    if _ui:
                        _lines.append('- ' + _ui[:60] + ' → ' + _sm[:60])
                if _lines:
                    parts.append('【历史任务】' + chr(10) + chr(10).join(_lines))
        except Exception as _e:
            print('[supervisor] chat mode 执行笔记失败: ' + str(_e))
        try:
            from .. import pattern_service
            _pats = pattern_service.retrieve_patterns(query, domain='dev', top_k=3)
            if _pats:
                _plines = []
                for _p in _pats:
                    _ev = (_p.get('evidence') or '')[:80] if isinstance(_p, dict) else ''
                    if _ev:
                        _plines.append('- ' + _ev)
                if _plines:
                    parts.append('【相关经验】' + chr(10) + chr(10).join(_plines))
        except Exception as _e:
            print('[supervisor] chat mode 经验库失败: ' + str(_e))


    _result = "\n".join(parts)
    _CTX_CACHE[_ck] = (_ct, _result)
    if len(_CTX_CACHE) > _CTX_MAX:
        _sorted_keys = sorted(_CTX_CACHE.items(), key=lambda x: x[1][0])[:50]
        for _k, _ in _sorted_keys:
            _CTX_CACHE.pop(_k, None)
    return _result


# (旧版 build_context 已删除，见上方新版本)



# (旧版 build_context 已删除)



def _dict(row):
    return dict(row) if row else None
