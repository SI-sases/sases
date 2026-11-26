"""MCP client API for SASES (stdio MVP, disabled by default)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.auth_service import SECRET_KEY
from core.services import mcp_client

router = APIRouter(prefix="/mcp", tags=["mcp"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


def _require_enabled() -> None:
    if os.environ.get("SASES_MCP_ALLOW", "0") not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="MCP client disabled; set SASES_MCP_ALLOW=1")


class ServerBody(BaseModel):
    name: str
    command: str
    args: list[str] = []
    env: dict = {}


class CallBody(BaseModel):
    server_id: int
    tool: str
    arguments: dict = {}


@router.get("/servers")
def servers(_: int = Depends(_user)):
    _require_enabled()
    return {"servers": mcp_client.list_servers()}


@router.post("/servers")
def add_server(body: ServerBody, _: int = Depends(_user)):
    _require_enabled()
    try:
        return mcp_client.add_server(body.name, body.command, body.args, body.env)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/servers/{server_id}")
def delete_server(server_id: int, _: int = Depends(_user)):
    _require_enabled()
    mcp_client.remove_server(server_id)
    return {"ok": True}


@router.post("/servers/{server_id}/test")
def test_server(server_id: int, _: int = Depends(_user)):
    _require_enabled()
    try:
        return mcp_client.test_server(server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/servers/{server_id}/tools")
def tools(server_id: int, _: int = Depends(_user)):
    _require_enabled()
    try:
        return {"tools": mcp_client.list_tools(server_id)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/call")
def call(body: CallBody, _: int = Depends(_user)):
    _require_enabled()
    try:
        return mcp_client.call_tool(body.server_id, body.tool, body.arguments)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
