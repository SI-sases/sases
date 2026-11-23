# core/api_routes/node_routes.py
"""Node identity, manifests, and creator-grant endpoints.

These endpoints never infer privilege from a private IP.  The manifest is the
authority; creator-only actions additionally require an active grant.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from core import node_identity as ni
from core.api_routes.auth_routes import get_current_user

router = APIRouter(prefix="/node", tags=["node"])


class NodeRegisterBody(BaseModel):
    ed25519_pubkey: str = Field(min_length=16)
    profile: str = "edge"
    wg_pubkey: str | None = None
    device_fingerprint: str | None = None
    node_id: str | None = None


class CreatorApplyBody(BaseModel):
    node_id: str
    scopes: list[str] | None = None
    note: str = ""
    portfolio_url: str = ""


class CreatorGrantBody(BaseModel):
    node_id: str
    scopes: list[str] | None = None
    expires_at: str | None = None


class RevokeBody(BaseModel):
    node_id: str
    reason: str = ""


def _manifest_node(token: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not token:
        raise HTTPException(status_code=401, detail="node manifest required")
    try:
        payload = ni.decode_manifest(token)
    except ni.ManifestError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    node = ni.get_node(payload.get("node_id", ""))
    if not node:
        raise HTTPException(status_code=403, detail="node not found")
    if node.get("status") != "active":
        raise HTTPException(status_code=403, detail="node revoked")
    if int(payload.get("user_id", -1)) != int(node["user_id"]):
        raise HTTPException(status_code=403, detail="manifest user mismatch")
    if payload.get("profile") != node.get("profile"):
        raise HTTPException(status_code=403, detail="manifest profile mismatch")
    return payload, node


def _require_cap(token: str | None, capability: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, node = _manifest_node(token)
    if capability not in set(payload.get("capabilities") or []):
        ni.audit_event(
            action="manifest.deny",
            node_id=node.get("node_id"),
            user_id=node.get("user_id"),
            profile=node.get("profile"),
            capability=capability,
            result="denied",
        )
        raise HTTPException(status_code=403, detail=f"capability required: {capability}")
    return payload, node


@router.post("/register")
def register_node(body: NodeRegisterBody, user: dict = Depends(get_current_user)):
    profile = (body.profile or "edge").strip().lower()
    if profile != ni.PROFILE_EDGE:
        raise HTTPException(status_code=403, detail="creator/official nodes are provisioned by admin")
    try:
        node = ni.create_node(
            user_id=user["id"],
            profile=profile,
            ed25519_pubkey=body.ed25519_pubkey,
            wg_pubkey=body.wg_pubkey,
            device_fingerprint=body.device_fingerprint,
            node_id=body.node_id,
        )
    except Exception as exc:  # noqa: BLE001 - return a stable client error
        raise HTTPException(status_code=409, detail=f"node registration failed: {exc}") from exc
    return {
        "node_id": node.get("node_id"),
        "profile": node.get("profile"),
        "issuer_public_key": ni.issuer_public_key(),
    }


@router.get("/manifest")
def get_manifest(node_id: str, user: dict = Depends(get_current_user)):
    node = ni.get_node(node_id)
    if not node or int(node["user_id"]) != int(user["id"]):
        raise HTTPException(status_code=404, detail="node not found")
    if node.get("status") != "active":
        raise HTTPException(status_code=403, detail="node revoked")
    token = ni.issue_manifest(node_id)
    payload = ni.decode_manifest(token)
    return {"manifest": token, "manifest_payload": payload, "issuer_public_key": ni.issuer_public_key()}


@router.get("/whoami")
def whoami(x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest")):
    payload, node = _manifest_node(x_sases_node_manifest)
    return {
        "node_id": node.get("node_id"),
        "user_id": node.get("user_id"),
        "profile": node.get("profile"),
        "capabilities": sorted(ni.effective_capabilities(node)),
        "manifest_capabilities": payload.get("capabilities") or [],
        "grant": ni.get_active_grant(node.get("node_id")) or None,
    }


@router.post("/creator/apply")
def creator_apply(body: CreatorApplyBody, user: dict = Depends(get_current_user)):
    try:
        result = ni.apply_creator_grant(user["id"], body.node_id, body.scopes, body.note, body.portfolio_url)
    except ni.NodeIdentityError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return result


@router.get("/admin/creator/applications")
def admin_creator_applications(
    status: str = "pending",
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _require_cap(x_sases_node_manifest, ni.CAP_APPROVE_CREATOR)
    return {"applications": ni.list_creator_applications(status)}


@router.post("/admin/creator/approve")
def admin_creator_approve(
    body: dict,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _payload, admin = _require_cap(x_sases_node_manifest, ni.CAP_APPROVE_CREATOR)
    try:
        grant = ni.approve_creator_application(
            str(body.get("grant_id", "")),
            int(admin["user_id"]),
            str(body.get("review_note", "")),
        )
    except ni.NodeIdentityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return grant


@router.post("/admin/creator/reject")
def admin_creator_reject(
    body: dict,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _payload, admin = _require_cap(x_sases_node_manifest, ni.CAP_APPROVE_CREATOR)
    try:
        ni.reject_creator_application(
            str(body.get("grant_id", "")),
            int(admin["user_id"]),
            str(body.get("reason", "")),
        )
    except ni.NodeIdentityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/creator/check")
def creator_check(
    capability: str = "publish_tool",
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    payload, node = _manifest_node(x_sases_node_manifest)
    if capability not in set(payload.get("capabilities") or []):
        raise HTTPException(status_code=403, detail=f"capability required: {capability}")
    grant = ni.get_active_grant(node.get("node_id"))
    if not grant:
        raise HTTPException(status_code=403, detail="creator grant required")
    if capability not in set(grant.get("scopes") or []):
        raise HTTPException(status_code=403, detail=f"creator scope required: {capability}")
    return {"ok": True, "grant_id": grant.get("grant_id"), "scopes": grant.get("scopes")}


@router.post("/admin/creator/grant")
def admin_grant_creator(
    body: CreatorGrantBody,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _payload, admin_node = _require_cap(x_sases_node_manifest, ni.CAP_APPROVE_CREATOR)
    try:
        grant = ni.grant_creator(
            user_id=int((ni.get_node(body.node_id) or {}).get("user_id") or 0),
            node_id=body.node_id,
            scopes=body.scopes,
            approved_by=int(admin_node["user_id"]),
            expires_at=body.expires_at,
        )
    except ni.NodeIdentityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ni.audit_event(
        action="admin.creator.grant",
        node_id=body.node_id,
        user_id=int(admin_node["user_id"]),
        profile=admin_node.get("profile"),
        grant_id=grant.get("grant_id"),
        capability=ni.CAP_APPROVE_CREATOR,
        result="ok",
    )
    return grant


@router.post("/admin/node/revoke")
def admin_revoke_node(
    body: RevokeBody,
    x_sases_node_manifest: str | None = Header(default=None, alias="X-SASES-Node-Manifest"),
):
    _payload, admin_node = _require_cap(x_sases_node_manifest, ni.CAP_MANAGE_NODES)
    changed = ni.revoke_node(body.node_id, reason=body.reason)
    if not changed:
        raise HTTPException(status_code=404, detail="node not found")
    ni.audit_event(
        action="admin.node.revoke",
        node_id=body.node_id,
        user_id=int(admin_node["user_id"]),
        profile=admin_node.get("profile"),
        capability=ni.CAP_MANAGE_NODES,
        result="ok",
        detail=body.reason,
    )
    return {"ok": True}
