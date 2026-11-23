"""Remote operations queue for client agents (allowlisted only)."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from core import client_ops
from core import node_identity as ni
from core.api_routes.node_routes import _manifest_node, _require_cap

router = APIRouter(prefix="/client/ops", tags=["client-ops"])


class EnqueueBody(BaseModel):
    node_id: str
    action: str
    payload: dict | None = None


class ClaimBody(BaseModel):
    node_id: str


class ResultBody(BaseModel):
    id: int
    status: str
    result: dict | None = None


@router.post("/enqueue")
def enqueue(
    body: EnqueueBody,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _payload, admin = _require_cap(x_sases_node_manifest, ni.CAP_MANAGE_NODES)
    try:
        return client_ops.enqueue(body.node_id, body.action, body.payload, int(admin["user_id"]))
    except client_ops.ClientOpsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list")
def list_ops(
    node_id: str | None = None,
    limit: int = 20,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _require_cap(x_sases_node_manifest, ni.CAP_MANAGE_NODES)
    return {"operations": client_ops.list_operations(node_id, limit)}


@router.post("/claim")
def claim(
    body: ClaimBody,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    payload, node = _manifest_node(x_sases_node_manifest)
    if body.node_id != payload.get("node_id") or body.node_id != node.get("node_id"):
        raise HTTPException(status_code=403, detail="node mismatch")
    return {"operation": client_ops.claim_next(body.node_id)}


@router.post("/result")
def result(
    body: ResultBody,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    payload, node = _manifest_node(x_sases_node_manifest)
    ops = [item for item in client_ops.list_operations(node.get("node_id"), 100) if item["id"] == body.id]
    if not ops:
        raise HTTPException(status_code=404, detail="operation not found")
    try:
        client_ops.complete(body.id, body.status, body.result)
    except client_ops.ClientOpsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
