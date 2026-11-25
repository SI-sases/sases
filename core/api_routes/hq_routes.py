"""HQ campaign / approval / task queue API."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core import hq
from core.auth_service import SECRET_KEY

router = APIRouter(prefix="/hq", tags=["hq"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


def _executor(
    x_sases_link_token: str | None = Header(default=None, alias="X-SASES-Link-Token"),
    x_sases_executor: str | None = Header(default=None, alias="X-SASES-Executor"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    executor = x_sases_executor or os.environ.get("SASES_NODE_ID") or "local"
    expected = os.environ.get("SASES_LINK_TOKEN", "")
    if expected and x_sases_link_token and hmac.compare_digest(expected, x_sases_link_token):
        return executor
    if credentials is not None:
        try:
            jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
            return executor
        except (JWTError, ValueError):
            pass
    raise HTTPException(status_code=401, detail="Not authenticated")


class CampaignBody(BaseModel):
    name: str
    region: str
    platforms: list[str]
    content: dict


class ReceiptBody(BaseModel):
    status: str
    result: dict | None = None
    error: str | None = None


@router.get("/campaigns")
def campaigns(limit: int = 50, _: int = Depends(_user)):
    return {"campaigns": hq.list_campaigns(limit)}


@router.post("/campaigns")
def create_campaign(body: CampaignBody, _: int = Depends(_user)):
    if not body.platforms:
        raise HTTPException(status_code=400, detail="platforms is empty")
    return hq.create_campaign(body.name, body.region, body.platforms, body.content)


@router.post("/campaigns/{campaign_id}/approve")
def approve(campaign_id: int, _: int = Depends(_user)):
    try:
        return hq.approve_campaign(campaign_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="campaign not found")


@router.get("/tasks")
def tasks(status: str | None = None, limit: int = 100, _: str = Depends(_executor)):
    return {"tasks": hq.list_tasks(status, limit)}


@router.post("/tasks/claim")
def claim(platform: str | None = None, executor: str = Depends(_executor)):
    task = hq.claim_task(executor, platform)
    if not task:
        return {"task": None}
    return {"task": task, "executor": executor}


@router.post("/tasks/{task_id}/receipt")
def receipt(task_id: int, body: ReceiptBody, _: str = Depends(_executor)):
    try:
        return hq.complete_task(task_id, body.status, body.result, body.error)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
