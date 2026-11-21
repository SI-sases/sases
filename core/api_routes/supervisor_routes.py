import asyncio
# core/api_routes/supervisor_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import supervisor_service
from ..services import trace_service as _trace_service

router = APIRouter(prefix="/supervisor", tags=["supervisor"])
security = HTTPBearer()


class ConfirmBody(BaseModel):
    run_id: int


class ProposeBody(BaseModel):
    conversation_id: int
    supervisor_id: str
    goal: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/propose")
async def propose(body: ProposeBody, user_id: int = Depends(get_current_user)):
    rid = supervisor_service.create_proposed_run(user_id, body.conversation_id, body.supervisor_id, body.goal)
    return {'run_id': rid, 'status': 'proposed'}


@router.post("/confirm")
async def confirm(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.confirm_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not proposed')
    _run = supervisor_service.get_run(body.run_id)
    if _run:
        try:
            from ..services import swarm_service
            asyncio.create_task(swarm_service.plan_task(
                user_id=user_id,
                conversation_id=_run['conversation_id'],
                user_input=_run['goal'],
                supervisor_id=_run.get('supervisor_id'),
                supervisor_run_id=body.run_id,
            ))
        except Exception as _e:
            print('[supervisor] confirm 派单失败: ' + str(_e))
    return {'run_id': body.run_id, 'status': 'running'}


@router.post("/reject")
async def reject(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.reject_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not proposed')
    return {'run_id': body.run_id, 'status': 'rejected'}


@router.post("/cancel")
async def cancel(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.cancel_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not cancellable')
    return {'run_id': body.run_id, 'status': 'cancelled'}



@router.get("/proposed")
async def get_proposed(conversation_id: int = None, user_id: int = Depends(get_current_user)):
    run = supervisor_service.get_proposed_run(user_id, conversation_id)
    return {'run': run}
# ===== P3-C1: trace API（并入 supervisor 路由，避免新增顶层路由文件）=====
from ..db import db_cursor as _db_cursor
from ..services.task_state_service import get_snapshot_fresh as _get_snapshot_fresh

trace_router = APIRouter(prefix="/trace", tags=["trace"])

_TRACE_SLICES = {
    "supervisor": ["task_id", "goal", "status", "progress", "current_step_desc",
                   "last_user_intent", "last_user_message", "finished_at"],
    "commander": ["task_id", "goal", "status", "failed_summary", "tried_strategies",
                  "progress", "current_step_desc"],
    "executor": ["task_id", "status", "progress", "current_step_desc", "evidence"],
    "reviewer": ["task_id", "goal", "status", "failed_summary", "evidence", "finished_at"],
}


def _trace_conv(task_id: int, user_id: int):
    with _db_cursor() as _cur_t:
        _cur_t.execute("SELECT conversation_id FROM supervisor_runs WHERE id=? AND user_id=?", (task_id, user_id))
        _row_t = _cur_t.fetchone()
    if not _row_t:
        return None
    return _row_t["conversation_id"] if isinstance(_row_t, dict) else _row_t[0]


@trace_router.get("/{task_id}/state")
async def get_trace_state(task_id: int, role: str, user_id: int = Depends(get_current_user)):
    if role not in _TRACE_SLICES:
        raise HTTPException(400, "role 必须是 " + "/".join(_TRACE_SLICES.keys()))
    cid = _trace_conv(task_id, user_id)
    if cid is None:
        raise HTTPException(404, "任务不存在")
    snap = _get_snapshot_fresh(cid) or {}
    if not snap:
        return {"task_id": task_id, "status": "no_snapshot"}
    out = {"task_id": task_id, "role": role}
    for key in _TRACE_SLICES[role]:
        if key in snap:
            out[key] = snap[key]
    return out


@trace_router.get("/{task_id}/messages")
async def get_trace_messages(task_id: int, level: int = 1, user_id: int = Depends(get_current_user)):
    cid = _trace_conv(task_id, user_id)
    if cid is None:
        raise HTTPException(404, "任务不存在")
    limit = 30 if level <= 1 else 100
    with _db_cursor() as _cur_m:
        _cur_m.execute(
            "SELECT id, sender, content, msg_type, created_at FROM messages "
            "WHERE conversation_id=? AND content LIKE '[TRACE]%' ORDER BY id DESC LIMIT ?",
            (cid, limit),
        )
        rows = [dict(r) for r in _cur_m.fetchall()]
    return {"task_id": task_id, "count": len(rows), "messages": rows}

# ===== run_trace: 活跃任务 / 最近任务 / 事件续传 =====
@router.get("/runs/active")
async def list_active_runs(conversation_id: int, user_id: int = Depends(get_current_user)):
    return {"runs": _trace_service.active_runs(conversation_id, user_id)}


@router.get("/runs/recent")
async def list_recent_runs(conversation_id: int, limit: int = 10, user_id: int = Depends(get_current_user)):
    return {"runs": _trace_service.recent_runs(conversation_id, user_id, limit)}


@trace_router.get("/{task_id}/events")
async def get_trace_events(task_id: int, after_seq: int = 0, limit: int = 500,
                           user_id: int = Depends(get_current_user)):
    cid = _trace_conv(task_id, user_id)
    if cid is None:
        raise HTTPException(404, "任务不存在")
    events = _trace_service.list_events(task_id, after_seq, limit)
    return {"run_id": task_id, "conversation_id": cid, "after_seq": after_seq,
            "count": len(events), "events": events}
