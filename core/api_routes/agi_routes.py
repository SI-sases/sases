# core/api_routes/agi_routes.py
import json
import os
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import agi_service

router = APIRouter(prefix="/agi", tags=["agi"])
security = HTTPBearer()


class AGIRequest(BaseModel):
    task_type: str
    content: str
    media_data: Optional[str] = None


class AskRequest(BaseModel):
    text: str


class FrontendEventRequest(BaseModel):
    event: str
    error: str = ""
    page: str = ""
    url: str = ""
    extra: dict | None = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def _main_agi_token() -> str:
    token = os.environ.get("SASES_AGI_TOKEN", "").strip()
    if token:
        return token
    path = Path(os.environ.get("SASES_AGI_TOKEN_FILE", str(Path("data") / "agi.token")))
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


@router.post("/ask")
async def ask_main_agi(body: AskRequest, user_id: int = Depends(get_current_user)):
    """Proxy the chat window to the user's main AGI control plane."""
    base = os.environ.get("SASES_AGI_URL", "http://127.0.0.1:8099").rstrip("/")
    token = _main_agi_token()
    if not token:
        raise HTTPException(status_code=503, detail="main AGI token is not configured")
    req = urllib.request.Request(
        base + "/ask",
        data=json.dumps({"text": body.text}).encode(),
        headers={"Content-Type": "application/json", "X-SASES-AGI-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"main AGI unavailable: {exc}") from exc


@router.post("/frontend-event")
async def frontend_event(body: FrontendEventRequest, user_id: int = Depends(get_current_user)):
    """Forward a PII-free frontend error/event to the main AGI event store."""
    base = os.environ.get("SASES_AGI_URL", "http://127.0.0.1:8099").rstrip("/")
    token = _main_agi_token()
    if not token:
        return {"accepted": False, "reason": "main AGI token not configured"}
    message = {
        "type": "agi.event",
        "node_id": "frontend",
        "scope": "local",
        "kind": "client",
        "severity": "error" if body.event in {"frontend_error", "unhandled_rejection"} else "info",
        "payload": {"message": body.event + ": " + body.error, "page": body.page, "url": body.url,
                    "extra": body.extra or {}},
        "evidence": {"source": "frontend", "user_id": user_id},
    }
    req = urllib.request.Request(
        base + "/events",
        data=json.dumps(message).encode(),
        headers={"Content-Type": "application/json", "X-SASES-AGI-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"accepted": True, "main_agi": json.loads(resp.read().decode("utf-8") or "{}")}
    except Exception as exc:  # noqa: BLE001
        return {"accepted": False, "reason": f"main AGI unavailable: {exc}"}


@router.post("/execute")
async def execute_agi(body: AGIRequest, user_id: int = Depends(get_current_user)):
    try:
        result = await agi_service.execute_agi_task(body.task_type, body.content, body.media_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
