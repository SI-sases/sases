# core/api_routes/memory_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])
security = HTTPBearer()


class RememberRequest(BaseModel):
    memory_type: str
    content: str
    agent_id: Optional[str] = None
    group_id: Optional[int] = None
    tags: Optional[str] = None
    importance: float = 0.5
    full_data: Optional[dict] = None
    expires_at: Optional[str] = None
    task_id: Optional[str] = None


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    memory_type: Optional[str] = None
    group_id: Optional[int] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/remember")
async def remember(body: RememberRequest, user_id: int = Depends(get_current_user)):
    memory_id = memory_service.remember(
        user_id=user_id,
        memory_type=body.memory_type,
        content=body.content,
        agent_id=body.agent_id,
        group_id=body.group_id,
        tags=body.tags,
        importance=body.importance,
        full_data=body.full_data,
        expires_at=body.expires_at,
        task_id=body.task_id
    )
    return {"memory_id": memory_id, "status": "remembered"}


@router.post("/recall")
async def recall(body: RecallRequest, user_id: int = Depends(get_current_user)):
    memories = memory_service.recall(
        user_id=user_id,
        query=body.query,
        top_k=body.top_k,
        memory_type=body.memory_type,
        group_id=body.group_id
    )
    return {"memories": memories}


@router.get("/type/{memory_type}")
async def recall_by_type(
    memory_type: str,
    top_k: int = 5,
    group_id: Optional[int] = None,
    user_id: int = Depends(get_current_user)
):
    memories = memory_service.recall_by_type(user_id, memory_type, top_k, group_id)
    return {"memories": memories}


@router.delete("/{memory_id}")
async def forget(memory_id: int, user_id: int = Depends(get_current_user)):
    success = memory_service.forget(user_id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"status": "forgotten"}
