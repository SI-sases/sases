"""Peer-to-peer SASES Link API."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.auth_service import SECRET_KEY
from core.sases_link import store

router = APIRouter(prefix="/link", tags=["sases-link"])
security = HTTPBearer(auto_error=False)


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


def _peer(
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
    x_sases_link_token: str | None = Header(default=None, alias="X-SASES-Link-Token"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    expected = os.environ.get("SASES_LINK_TOKEN", "")
    if expected and x_sases_link_token and hmac.compare_digest(expected, x_sases_link_token):
        return _local_node()
    if x_sases_node_manifest:
        from core.api_routes.node_routes import _manifest_node
        payload, _node = _manifest_node(x_sases_node_manifest)
        return str(payload.get("node_id"))
    if credentials is not None:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
            int(payload.get("sub"))
            return _local_node()
        except (JWTError, ValueError):
            pass
    raise HTTPException(status_code=401, detail="Not authenticated")


def _local_node() -> str:
    return os.environ.get("SASES_NODE_ID") or "local"


class HelloBody(BaseModel):
    peer_id: str
    node_id: str
    base_url: str = ""
    capabilities: list[str] = []


class SendBody(BaseModel):
    to: str
    action: str
    payload: dict | None = None
    idempotency_key: str | None = None
    timeout_sec: int = 300


class AckBody(BaseModel):
    msg_id: str
    status: str
    result: dict | None = None
    error: str | None = None


@router.post("/hello")
def hello(body: HelloBody, _: str = Depends(_peer)):
    return store.hello(body.peer_id, body.node_id, body.base_url, body.capabilities)


@router.get("/peers")
def peers(_: str = Depends(_peer)):
    return {"peers": store.list_peers()}


@router.post("/send")
def send(body: SendBody, sender: str = Depends(_peer)):
    try:
        return store.enqueue(sender, body.to, body.action, body.payload,
                             body.idempotency_key, body.timeout_sec)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/inbox")
def inbox(receiver: str | None = None, limit: int = 50, me: str = Depends(_peer)):
    return {"messages": store.inbox(receiver or me, limit)}


@router.get("/audit")
def audit(limit: int = 100, _: str = Depends(_peer)):
    return {"audit": store.list_audit(limit)}


@router.get("/messages")
def messages(peer_id: str | None = None, limit: int = 50, _: str = Depends(_peer)):
    return {"messages": store.list_messages(peer_id, limit)}


@router.post("/ack")
def ack(body: AckBody, _: str = Depends(_peer)):
    try:
        return store.ack(body.msg_id, body.status, body.result, body.error, actor=_ )
    except KeyError:
        raise HTTPException(status_code=404, detail="message not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
