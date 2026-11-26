"""Workflow API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.auth_service import SECRET_KEY
from core.services import workflow_registry, workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


class RunBody(BaseModel):
    params: dict = {}
    approve: bool = False


@router.get("")
def list_workflows(_: int = Depends(_user)):
    return {"workflows": workflow_registry.list_workflows()}


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, _: int = Depends(_user)):
    try:
        return workflow_registry.get_workflow(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{workflow_id}/run")
def run(workflow_id: str, body: RunBody, user_id: int = Depends(_user)):
    try:
        return workflow_service.run(user_id, workflow_id, body.params, body.approve)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
