# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

p = Path('core/services/supervisor/context.py')
s = p.read_text(encoding='utf-8')

if '_tc_chat' in s:
    print('ALREADY_DONE')
    exit(0)

# 在 chat 模式的记忆注入后，单独注入 task_context
old = '''    try:
        from .. import memory_service
        mems = memory_service.recall(user_id, query, 2)
        for m in (mems or []):
            mc = (m.get("content") or "")[:100] if isinstance(m, dict) else ""
            if mc:
                parts.append("记忆：" + mc)
    except Exception as e:
        print("[supervisor] build_context 记忆读取失败: " + str(e))'''

new = '''    try:
        from .. import memory_service
        _tc_chat = memory_service.recall_by_type(user_id, 'task_context', top_k=2)
        if _tc_chat:
            _tc_text = chr(10).join(str(m.get('content') or '') for m in _tc_chat)
            parts.append("【当前任务（必读）】" + chr(10) + _tc_text)
        else:
            parts.append("【当前任务（必读）】当前没有活跃任务。用户问“当前任务是什么”时，直接回答“当前没有活跃任务”，禁止从历史记忆或经验记录推断。")
        mems = memory_service.recall(user_id, query, 2)
        for m in (mems or []):
            if m.get('memory_type') == 'task_context':
                continue
            mc = (m.get("content") or "")[:100] if isinstance(m, dict) else ""
            if mc:
                parts.append("【历史记忆】" + mc)
    except Exception as e:
        print("[supervisor] build_context 记忆读取失败: " + str(e))'''

if old not in s:
    print('OLD_NOT_FOUND')
    exit(1)

s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('PATCHED')

try:
    py_compile.compile(str(p), doraise=True)
    print('SYNTAX_OK')
except Exception as e:
    print('SYNTAX_ERROR', e)
