# core/api_routes/commander_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import commander_service

router = APIRouter(prefix="/commander", tags=["commander"])
security = HTTPBearer()


class CommanderTaskRequest(BaseModel):
    conversation_id: Optional[int] = None
    task: str
    sender_agent_id: Optional[str] = None
    timeout: int = 30


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/execute")
async def execute_task(body: CommanderTaskRequest, user_id: int = Depends(get_current_user)):
    if not body.task.strip():
        raise HTTPException(status_code=400, detail="任务不能为空")
    result = await commander_service.execute_commander_task(
        user_id=user_id,
        conversation_id=body.conversation_id,
        task_text=body.task.strip(),
        sender_agent_id=body.sender_agent_id,
        timeout=body.timeout
    )
    return result
