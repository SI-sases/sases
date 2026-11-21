# -*- coding: utf-8 -*-
"""P3-C1: trace API — 四角色按 run_id 读取快照切片（只读）"""
from fastapi import APIRouter, Depends, HTTPException

from core.db import db_cursor
from core.api_routes.auth_routes import get_current_user
from core.services.task_state_service import get_snapshot_fresh

router = APIRouter(prefix="/trace", tags=["trace"])

# 四角色各自关心的字段白名单
_SLICES = {
    "supervisor": ["task_id", "goal", "status", "progress", "current_step_desc",
                   "last_user_intent", "last_user_message", "finished_at"],
    "commander": ["task_id", "goal", "status", "failed_summary", "tried_strategies",
                  "progress", "current_step_desc"],
    "executor": ["task_id", "status", "progress", "current_step_desc", "evidence"],
    "reviewer": ["task_id", "goal", "status", "failed_summary", "evidence", "finished_at"],
}


def _conv_of_run(task_id: int, user_id: int):
    with db_cursor() as cur:
        cur.execute(
            "SELECT conversation_id FROM supervisor_runs WHERE id=? AND user_id=?",
            (task_id, user_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return row["conversation_id"] if isinstance(row, dict) else row[0]


@router.get("/{task_id}/state")
async def get_trace_state(task_id: int, role: str, user: dict = Depends(get_current_user)):
    """按角色返回快照切片。role: supervisor/commander/executor/reviewer"""
    if role not in _SLICES:
        raise HTTPException(400, "role 必须是 " + "/".join(_SLICES.keys()))
    cid = _conv_of_run(task_id, user["id"])
    if cid is None:
        raise HTTPException(404, "任务不存在")
    snap = get_snapshot_fresh(cid) or {}
    if not snap:
        return {"task_id": task_id, "status": "no_snapshot"}
    out = {"task_id": task_id, "role": role}
    for key in _SLICES[role]:
        if key in snap:
            out[key] = snap[key]
    return out


@router.get("/{task_id}/messages")
async def get_trace_messages(task_id: int, level: int = 1, user: dict = Depends(get_current_user)):
    """返回该任务的里程碑/详细日志（level=1 里程碑，level>=2 详细）"""
    cid = _conv_of_run(task_id, user["id"])
    if cid is None:
        raise HTTPException(404, "任务不存在")
    limit = 30 if level <= 1 else 100
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, sender, content, msg_type, created_at FROM messages "
            "WHERE conversation_id=? AND content LIKE '[TRACE]%' ORDER BY id DESC LIMIT ?",
            (cid, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"task_id": task_id, "count": len(rows), "messages": rows}
