# core/services/run_control_service.py
# -*- coding: utf-8 -*-
"""会话级暂停/恢复：暂停后 agent_loop 在当前步后退出，不丢历史。

P1-1: 暂停标记同时落库（supervisor_runs.status='paused'），进程重启后仍可恢复。
P1-2: 恢复时优先复用同会话的 paused run，不新建 run。
P1-7: 恢复从最后一条消息继续（resume=True，不重复 append 用户消息）。
"""
import threading

_lock = threading.Lock()
_paused = set()
# conversation_id -> {"run_id": int, "goal": str}：暂停时记下待恢复的 run
_resume_target = {}


def pause(conversation_id, run_id=None, goal=None):
    """标记会话暂停；有 run_id 时记下待恢复目标。"""
    cid = int(conversation_id)
    with _lock:
        _paused.add(cid)
        if run_id:
            _resume_target[cid] = {"run_id": int(run_id), "goal": str(goal or "")}
    if run_id:
        try:
            from ..db import db_cursor
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE supervisor_runs SET status='paused' WHERE id=?", (int(run_id),))
        except Exception as e:
            print("[pause] 落库失败: " + str(e))


def resume(conversation_id):
    """清除暂停标记（不清理 resume 目标，供 take_resume_target 取用）。"""
    with _lock:
        _paused.discard(int(conversation_id))


def is_paused(conversation_id):
    with _lock:
        return int(conversation_id) in _paused


def set_resume_target(conversation_id, run_id, goal=""):
    with _lock:
        _resume_target[int(conversation_id)] = {"run_id": int(run_id), "goal": str(goal or "")}


def peek_resume_target(conversation_id):
    with _lock:
        t = _resume_target.get(int(conversation_id))
        return dict(t) if t else None


def take_resume_target(conversation_id):
    """取出并清除待恢复目标（一次性消费）。"""
    with _lock:
        return _resume_target.pop(int(conversation_id), None)


def find_paused_run(conversation_id):
    """P1-2: 查同会话最近一个 paused run（内存优先，其次数据库）。"""
    t = peek_resume_target(conversation_id)
    if t and t.get("run_id"):
        return t
    try:
        from ..db import db_cursor
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, goal FROM supervisor_runs WHERE conversation_id=? AND status='paused' "
                "ORDER BY id DESC LIMIT 1", (int(conversation_id),))
            row = cur.fetchone()
        if row:
            return {"run_id": int(row["id"]), "goal": str(row["goal"] or "")}
    except Exception as e:
        print("[resume] 查询 paused run 失败: " + str(e))
    return None
