"""Marketplace read API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.auth_service import SECRET_KEY
from core.services import marketplace_service

router = APIRouter(prefix="/marketplace", tags=["marketplace"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("")
def entries(
    q: str = Query(""),
    type: str = Query(""),
    _: int = Depends(_user),
):
    return {"entries": marketplace_service.list_entries(q, type)}


@router.get("/{entry_id}")
def entry(entry_id: str, _: int = Depends(_user)):
    try:
        return marketplace_service.get_entry(entry_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
