# core/services/message/ingest.py
# -*- coding: utf-8 -*-
"""D: 入站辅助（任务分类、兜底会话、命令解析）。"""
from ...db import db_cursor

_COMMAND_PREFIXES = {
    "#0": "unlock", "#1": "exec", "#2": "task",
    "#3": "draft", "#4": "auto", "#5": "schedule",
}


def classify_task_type(goal):
    _g = str(goal or '')
    if any(k in _g for k in ('探测', '列出', '统计', '看', '读')):
        return 'simple_probe'
    if any(k in _g for k in ('重构', '重写', '打通')):
        return 'refactor'
    if any(k in _g for k in ('加', '实现', '新增', '创建', '参考')):
        return 'feature_dev'
    if any(k in _g for k in ('改', '修')):
        return 'code_edit'
    return 'unknown'


def fallback_conversation_id():
    try:
        with db_cursor() as cur:
            cur.execute("SELECT conversation_id FROM messages WHERE sender='user' ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                try:
                    val = row['conversation_id']
                except Exception:
                    val = row[0]
                if val:
                    print('[supervisor] auto_run fallback conversation_id=' + str(val))
                    return val
    except Exception:
        pass
    return 0


def extract_command(content):
    """返回 {kind, body}；kind=chat 表示没有命令前缀。"""
    s = str(content or '').strip()
    for prefix, kind in _COMMAND_PREFIXES.items():
        if s.startswith(prefix + ':') or s.startswith(prefix + '：'):
            return {"kind": kind, "body": s[len(prefix) + 1:].strip()}
    return {"kind": "chat", "body": s}
