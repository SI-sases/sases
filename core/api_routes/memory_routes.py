"""Memory API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.auth_service import SECRET_KEY
from core.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


class MemoryBody(BaseModel):
    key: str
    value: str
    scope: str = "global"
    session_id: int | None = None


@router.get("")
def list_memory(
    scope: str = Query("global"),
    session_id: int | None = Query(None),
    user_id: int = Depends(_user),
):
    try:
        return {"entries": memory_service.list_memory(user_id, scope, session_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("")
def set_memory(body: MemoryBody, user_id: int = Depends(_user)):
    try:
        return memory_service.set_memory(user_id, body.key, body.value, body.scope, body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{memory_id}")
def delete_memory(memory_id: int, user_id: int = Depends(_user)):
    if not memory_service.delete_memory(user_id, memory_id):
        raise HTTPException(status_code=404, detail="memory not found")
    return {"ok": True}
