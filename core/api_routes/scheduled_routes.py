# core/api_routes/scheduled_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import scheduled_task_service

router = APIRouter(prefix="/scheduled", tags=["scheduled"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


class CreateTaskRequest(BaseModel):
    name: str
    cron_expr: str
    task_template: str
    conversation_id: int
    supervisor_id: str
    timezone: Optional[str] = "Asia/Shanghai"


class ToggleTaskRequest(BaseModel):
    enabled: bool


@router.post("/create")
async def create_task(body: CreateTaskRequest, user_id: int = Depends(get_current_user)):
    try:
        task_id = scheduled_task_service.create_task(
            user_id=user_id,
            name=body.name,
            cron_expr=body.cron_expr,
            task_template=body.task_template,
            conversation_id=body.conversation_id,
            supervisor_id=body.supervisor_id,
            timezone=body.timezone or "Asia/Shanghai",
        )
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_tasks(user_id: int = Depends(get_current_user)):
    try:
        tasks = scheduled_task_service.list_tasks(user_id)
        return {"ok": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
async def get_task(task_id: str, user_id: int = Depends(get_current_user)):
    task = scheduled_task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"ok": True, "task": task}


@router.patch("/{task_id}/toggle")
async def toggle_task(task_id: str, body: ToggleTaskRequest, user_id: int = Depends(get_current_user)):
    ok = scheduled_task_service.toggle_task(task_id, user_id, body.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    return {"ok": True}


@router.delete("/{task_id}")
async def delete_task(task_id: str, user_id: int = Depends(get_current_user)):
    ok = scheduled_task_service.delete_task(task_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    return {"ok": True}