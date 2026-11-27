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


def _main_request(method: str, path: str, body: dict | None = None) -> dict:
    base = os.environ.get("SASES_AGI_URL", "http://127.0.0.1:8099").rstrip("/")
    token = _main_agi_token()
    if not token:
        raise HTTPException(status_code=503, detail="main AGI token is not configured")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "X-SASES-AGI-Token": token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"main AGI unavailable: {exc}") from exc


@router.get("/approvals")
async def list_approvals(user_id: int = Depends(get_current_user)):
    return _main_request("GET", "/approvals")


@router.get("/agents")
async def list_agents(user_id: int = Depends(get_current_user)):
    return _main_request("GET", "/agents")


@router.get("/background-tasks")
async def background_tasks(user_id: int = Depends(get_current_user)):
    data = _main_request("GET", "/agents")
    agents = [a for a in data.get("agents", []) if a.get("kind") not in ("subagent", "")]
    return {"tasks": agents, "active": sum(1 for a in agents if a.get("status") == "active")}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user_id: int = Depends(get_current_user)):
    return _main_request("GET", f"/agents/{agent_id}")


@router.get("/agents/{agent_id}/messages")
async def agent_messages(agent_id: str, user_id: int = Depends(get_current_user)):
    return _main_request("GET", f"/agents/{agent_id}/messages")


@router.get("/agents/{agent_id}/wait")
async def agent_wait(agent_id: str, timeout: int = 20, user_id: int = Depends(get_current_user)):
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(_main_request, "GET",
                                   f"/agents/{agent_id}/wait?timeout={max(0, min(timeout, 60))}")


@router.get("/agents/{agent_id}/result")
async def agent_result(agent_id: str, user_id: int = Depends(get_current_user)):
    return _main_request("GET", f"/agents/{agent_id}/result")


@router.get("/context/{context_id}")
async def get_context(context_id: str, user_id: int = Depends(get_current_user)):
    return _main_request("GET", f"/context/{context_id}")


@router.get("/context/{context_id}/render")
async def render_context(context_id: str, budget: int = 4000,
                         user_id: int = Depends(get_current_user)):
    return _main_request("GET", f"/context/{context_id}/render?budget={max(500, min(budget, 16000))}")


@router.post("/agents/{agent_id}/message")
async def agent_message(agent_id: str, body: dict, user_id: int = Depends(get_current_user)):
    return _main_request("POST", f"/agents/{agent_id}/message", {
        "message": str(body.get("message") or ""),
    })


@router.post("/agents/{agent_id}/cancel")
async def agent_cancel(agent_id: str, user_id: int = Depends(get_current_user)):
    return _main_request("POST", f"/agents/{agent_id}/cancel", {})


@router.post("/worker/run")
async def worker_run(user_id: int = Depends(get_current_user)):
    from starlette.concurrency import run_in_threadpool
    # Keep the event loop free: the worker calls back into this app for /health.
    return await run_in_threadpool(_main_request, "POST", "/worker/run", {})


@router.get("/worker/status")
async def worker_status(user_id: int = Depends(get_current_user)):
    return _main_request("GET", "/worker/status")


@router.post("/approvals/decide")
async def decide_approval(body: dict, user_id: int = Depends(get_current_user)):
    return _main_request("POST", "/approvals/decide", {
        "id": int(body.get("id") or 0),
        "decision": str(body.get("decision") or ""),
        "decided_by": f"user:{user_id}",
    })


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
