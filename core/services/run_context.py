# core/services/run_context.py
# -*- coding: utf-8 -*-
"""当前执行上下文，供工具读取父 run。"""
import contextvars

_CURRENT = contextvars.ContextVar("sases_run_context", default={})


def set_current(user_id=None, conversation_id=None, run_id=None, parent_run_id=None):
    _CURRENT.set({
        "user_id": int(user_id) if user_id else None,
        "conversation_id": int(conversation_id) if conversation_id else None,
        "run_id": int(run_id) if run_id else None,
        "parent_run_id": int(parent_run_id) if parent_run_id else None,
    })


def get_current():
    return dict(_CURRENT.get() or {})
