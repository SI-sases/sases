# core/api_routes/work_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import work_service, memory_service

router = APIRouter(prefix="/work", tags=["work"])
security = HTTPBearer()


class WorkExecuteRequest(BaseModel):
    conversation_id: Optional[int] = None  # 允许为空
    command: str
    sender_agent_id: Optional[str] = None
    timeout: int = 30


class WorkReportRequest(BaseModel):
    conversation_id: Optional[int] = None
    command: str
    output: str
    status: str
    duration_ms: int
    sender_agent_id: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/execute")
async def execute_work(body: WorkExecuteRequest, user_id: int = Depends(get_current_user)):
    if not body.command.strip():
        raise HTTPException(status_code=400, detail="命令不能为空")
    try:
        result = await work_service.execute_work_command(
            user_id=user_id,
            conversation_id=body.conversation_id,
            command=body.command.strip(),
            sender_agent_id=body.sender_agent_id,
            timeout=body.timeout
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report")
async def report_work_result(body: WorkReportRequest, user_id: int = Depends(get_current_user)):
    try:
        result = await work_service.report_work_result(
            user_id=user_id,
            conversation_id=body.conversation_id,
            command=body.command,
            output=body.output,
            status=body.status,
            duration_ms=body.duration_ms,
            sender_agent_id=body.sender_agent_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logs")
async def get_logs(limit: int = 50, user_id: int = Depends(get_current_user)):
    logs = work_service.get_work_logs(user_id, limit)
    return {"logs": logs}


@router.post("/credit/enable")
async def enable_credit(user_id: int = Depends(get_current_user)):
    return {"status": "not_implemented", "message": "积分扣费暂未启用"}


@router.post("/summarize")
async def summarize_work_logs(hours: int = 24, user_id: int = Depends(get_current_user)):
    memory_id = memory_service.summarize_work_logs(user_id, hours)
    if memory_id == 0:
        return {"status": "no_logs", "message": "该时间段内没有日志"}
    return {"status": "summarized", "memory_id": memory_id}
