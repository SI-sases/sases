import asyncio
# core/api_routes/supervisor_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..db import db_cursor
from ..services import supervisor_service
from ..services import approval_service
from ..services import checkpoint_service
from ..services import trace_service as _trace_service

router = APIRouter(prefix="/supervisor", tags=["supervisor"])
security = HTTPBearer()


class ConfirmBody(BaseModel):
    run_id: int


class ProposeBody(BaseModel):
    conversation_id: int
    supervisor_id: str
    goal: str


class ApproveBody(BaseModel):
    step_id: str
    decision: str = "allow"
    scope: str = "once"


class RevertBody(BaseModel):
    confirm: bool = False


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/runs/{run_id}/revert")
async def revert_run(run_id: int, body: RevertBody, user_id: int = Depends(get_current_user)):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm required")
    with db_cursor() as cur:
        cur.execute("SELECT user_id FROM supervisor_runs WHERE id=?", (run_id,))
        row = cur.fetchone()
    if not row or int(row["user_id"] if isinstance(row, dict) else row[0]) != int(user_id):
        raise HTTPException(status_code=404, detail="run not found")
    result = checkpoint_service.revert(run_id)
    return {"status": "ok", **result}


@router.get("/runs/{run_id}/artifacts")
def list_run_artifacts(run_id: int, user_id: int = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT user_id FROM supervisor_runs WHERE id=?", (run_id,))
        row = cur.fetchone()
    if not row or int(row["user_id"] if isinstance(row, dict) else row[0]) != int(user_id):
        raise HTTPException(status_code=404, detail="run not found")
    from ..services.artifact_service import list_artifacts
    return {"artifacts": list_artifacts(run_id)}


@router.post("/runs/{run_id}/approve")
async def approve_run(run_id: int, body: ApproveBody, user_id: int = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT user_id FROM supervisor_runs WHERE id=?", (run_id,))
        row = cur.fetchone()
    if not row or int(row["user_id"] if isinstance(row, dict) else row[0]) != int(user_id):
        raise HTTPException(status_code=404, detail="run not found")
    approval_service.decide(run_id, body.step_id, body.decision, body.scope)
    if str(body.decision).lower() in ("allow", "once", "session", "approve"):
        try:
            from ..services import execution_gateway
            asyncio.create_task(execution_gateway.resume_after_approval(run_id))
        except Exception as _e_ap:
            print('[approval] 审批后继续失败: ' + str(_e_ap))
    return {"status": "ok", "decision": body.decision, "scope": body.scope}


@router.get("/runs")
def list_active_runs(user_id: int = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, conversation_id, goal, status, supervisor_id, created_at "
            "FROM supervisor_runs WHERE user_id=? AND status IN "
            "('running','paused','awaiting_approval','awaiting_user') "
            "ORDER BY id DESC LIMIT 30", (user_id,))
        rows = cur.fetchall()
    return {"runs": [dict(r) for r in rows]}


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: int, user_id: int = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT conversation_id FROM supervisor_runs WHERE id=? AND user_id=?",
                    (run_id, user_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="run not found")
        cur.execute("UPDATE supervisor_runs SET status='paused' WHERE id=? AND user_id=?",
                    (run_id, user_id))
    # 暂停信号必须真正下发到执行侧，否则只是改了状态文字
    try:
        from ..services import run_control_service
        run_control_service.pause(row["conversation_id"])
    except Exception as _e_pause:
        print('[pause] 下发暂停信号失败: ' + str(_e_pause))
    return {"ok": True, "run_id": run_id, "status": "paused"}


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: int, user_id: int = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT conversation_id FROM supervisor_runs WHERE id=? AND user_id=?",
                    (run_id, user_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="run not found")
        cur.execute("UPDATE supervisor_runs SET status='running' WHERE id=? AND user_id=?",
                    (run_id, user_id))
    try:
        from ..services import run_control_service
        run_control_service.resume(row["conversation_id"])
    except Exception as _e_res:
        print('[resume] 解除暂停信号失败: ' + str(_e_res))
    # 续跑失败不能吞掉：返回 resumed 标记，前端据此提示
    resumed = False
    try:
        from ..services import execution_gateway
        asyncio.create_task(execution_gateway.resume_run(run_id, "继续"))
        resumed = True
    except Exception as _e_run:
        print('[resume] 续跑调度失败: ' + str(_e_run))
    return {"ok": True, "run_id": run_id, "status": "running", "resumed": resumed}


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
            from ..services import execution_gateway
            asyncio.create_task(execution_gateway.run_a2a(body.run_id))
        except Exception as _e:
            print('[supervisor] confirm 派单失败: ' + str(_e))
    return {'run_id': body.run_id, 'status': 'running'}


@router.post("/reject")
async def reject(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.reject_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not proposed')
    try:
        from ..services.cross_account_delivery import notify_a2a_rejected
        asyncio.create_task(notify_a2a_rejected(body.run_id))
    except Exception as _e_rej:
        print('[a2a] 拒绝回执派发失败: ' + str(_e_rej))
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
