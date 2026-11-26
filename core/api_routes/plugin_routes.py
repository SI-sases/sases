"""Plugin registry API (metadata MVP)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.auth_service import SECRET_KEY
from core.services import plugin_registry

router = APIRouter(prefix="/plugins", tags=["plugins"])
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
def plugins(_: int = Depends(_user)):
    return {"plugins": plugin_registry.list_plugins()}


@router.post("/{plugin_id}/enable")
def enable(plugin_id: str, _: int = Depends(_user)):
    try:
        return plugin_registry.set_enabled(plugin_id, True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{plugin_id}/disable")
def disable(plugin_id: str, _: int = Depends(_user)):
    try:
        return plugin_registry.set_enabled(plugin_id, False)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
