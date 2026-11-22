# core/services/run_control_service.py
# -*- coding: utf-8 -*-
"""会话级暂停/恢复：暂停后 agent_loop 在当前步后退出，不丢历史。"""
import threading

_lock = threading.Lock()
_paused = set()


def pause(conversation_id):
    with _lock:
        _paused.add(int(conversation_id))


def resume(conversation_id):
    with _lock:
        _paused.discard(int(conversation_id))


def is_paused(conversation_id):
    with _lock:
        return int(conversation_id) in _paused
