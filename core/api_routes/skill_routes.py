"""Skill registry API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.auth_service import SECRET_KEY
from core.services import skill_registry

router = APIRouter(prefix="/skills", tags=["skills"])
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
def list_skills(_: int = Depends(_user)):
    return {"skills": skill_registry.list_skills()}


@router.get("/{name}")
def load_skill(name: str, _: int = Depends(_user)):
    try:
        return skill_registry.load_skill(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
