# core/node_identity.py
"""SASES node identity and capability manifests.

Network location is never an authorization signal. A node proves its profile
with a server-signed manifest; creator-only actions additionally require an
active creator grant.
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from core.db import db_cursor

PROFILE_OFFICIAL = "official"
PROFILE_CREATOR = "creator"
PROFILE_EDGE = "edge"
PROFILES = (PROFILE_OFFICIAL, PROFILE_CREATOR, PROFILE_EDGE)

CAP_CALL_API = "call_api"
CAP_READ_SELF = "read_self"
CAP_PROVIDE_API = "provide_api"
CAP_PUBLISH_TOOL = "publish_tool"
CAP_PUBLISH_TEMPLATE = "publish_template"
CAP_PROPOSE_REGISTRY = "propose_registry"
CAP_INSTALL_TOOL = "install_tool"
CAP_WRITE_REGISTRY = "write_registry"
CAP_ISSUE_LICENSE = "issue_license"
CAP_MANAGE_NODES = "manage_nodes"
CAP_APPROVE_CREATOR = "approve_creator"
CAP_ADMIN_CONSOLE = "admin_console"

PROFILE_CAPABILITIES: dict[str, set[str]] = {
    PROFILE_OFFICIAL: {
        CAP_CALL_API,
        CAP_READ_SELF,
        CAP_PROVIDE_API,
        CAP_PUBLISH_TOOL,
        CAP_PUBLISH_TEMPLATE,
        CAP_PROPOSE_REGISTRY,
        CAP_INSTALL_TOOL,
        CAP_WRITE_REGISTRY,
        CAP_ISSUE_LICENSE,
        CAP_MANAGE_NODES,
        CAP_APPROVE_CREATOR,
        CAP_ADMIN_CONSOLE,
    },
    PROFILE_CREATOR: {
        CAP_CALL_API,
        CAP_READ_SELF,
        CAP_PROVIDE_API,
        CAP_PUBLISH_TOOL,
        CAP_PUBLISH_TEMPLATE,
        CAP_PROPOSE_REGISTRY,
    },
    PROFILE_EDGE: {
        CAP_CALL_API,
        CAP_READ_SELF,
    },
}

CREATOR_SCOPES = {
    "provide_api": CAP_PROVIDE_API,
    "publish_tool": CAP_PUBLISH_TOOL,
    "publish_template": CAP_PUBLISH_TEMPLATE,
    "propose_registry": CAP_PROPOSE_REGISTRY,
}

MANIFEST_VERSION = 1
DEFAULT_MANIFEST_TTL_MINUTES = int(os.getenv("SASES_NODE_MANIFEST_TTL_MINUTES", "1440"))


class NodeIdentityError(Exception):
    """Base error for node identity failures."""


class ManifestError(NodeIdentityError):
    """Manifest is malformed, expired, or has an invalid signature."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def generate_node_keypair() -> tuple[str, str]:
    """Return (private_key_b64, public_key_b64) for a client node."""
    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64e(private_raw), _b64e(public_raw)


def public_key_from_private(private_b64: str) -> str:
    private = Ed25519PrivateKey.from_private_bytes(_b64d(private_b64))
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64e(public_raw)


def _issuer_key_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "node_signing.key")


def _load_issuer_private() -> Ed25519PrivateKey:
    raw_env = os.getenv("SASES_NODE_SIGNING_KEY", "").strip()
    if raw_env:
        return Ed25519PrivateKey.from_private_bytes(_b64d(raw_env))

    path = _issuer_key_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as handle:
            raw = handle.read()
        return Ed25519PrivateKey.from_private_bytes(_b64d(raw.decode().strip()))

    private = Ed25519PrivateKey.generate()
    raw = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    encoded = _b64e(raw)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(encoded)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return private


def issuer_public_key() -> str:
    public_raw = _load_issuer_private().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64e(public_raw)


def sign_manifest(payload: dict[str, Any]) -> str:
    body = _b64e(_canonical(payload))
    signature = _load_issuer_private().sign(body.encode())
    return f"{body}.{_b64e(signature)}"


def decode_manifest(token: str, verify: bool = True) -> dict[str, Any]:
    try:
        body, signature = token.split(".", 1)
        raw_body = _b64d(body)
        if verify:
            public_raw = _load_issuer_private().public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            Ed25519PublicKey.from_public_bytes(public_raw).verify(_b64d(signature), body.encode())
        payload = json.loads(raw_body.decode())
    except ManifestError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize crypto/json errors
        raise ManifestError("invalid manifest") from exc

    if not isinstance(payload, dict):
        raise ManifestError("invalid manifest payload")
    if int(payload.get("v", 0)) != MANIFEST_VERSION:
        raise ManifestError("unsupported manifest version")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ManifestError("manifest expired")
    return payload


def normalize_profile(profile: str) -> str:
    value = (profile or "").strip().lower()
    if value not in PROFILES:
        raise NodeIdentityError(f"invalid profile: {profile}")
    return value


def create_node(
    user_id: int,
    profile: str = PROFILE_EDGE,
    ed25519_pubkey: str = "",
    wg_pubkey: str | None = None,
    device_fingerprint: str | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    profile = normalize_profile(profile)
    node_id = node_id or f"node_{secrets.token_hex(8)}"
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO identity_nodes(node_id, user_id, profile, ed25519_pubkey, wg_pubkey, "
            "device_fingerprint, status, manifest_version, created_at) "
            "VALUES (?,?,?,?,?,?, 'active', 1, ?)",
            (node_id, int(user_id), profile, ed25519_pubkey, wg_pubkey, device_fingerprint, now),
        )
    audit_event(node_id=node_id, user_id=user_id, profile=profile, action="node.create", result="ok")
    return get_node(node_id) or {}


def get_node(node_id: str) -> dict[str, Any] | None:
    with db_cursor() as cur:
        row = cur.execute("SELECT * FROM identity_nodes WHERE node_id=?", (node_id,)).fetchone()
    return dict(row) if row else None


def list_nodes(user_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM identity_nodes"
    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append("user_id=?")
        params.append(int(user_id))
    if status:
        clauses.append("status=?")
        params.append(status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"
    with db_cursor() as cur:
        rows = cur.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def revoke_node(node_id: str, reason: str = "") -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE identity_nodes SET status='revoked', revoked_at=? WHERE node_id=?",
            (_now(), node_id),
        )
        changed = cur.rowcount
    audit_event(node_id=node_id, action="node.revoke", result="ok" if changed else "missing", detail=reason)
    return bool(changed)


def get_node_by_pubkey(ed25519_pubkey: str) -> dict[str, Any] | None:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM identity_nodes WHERE ed25519_pubkey=?", (ed25519_pubkey,)
        ).fetchone()
    return dict(row) if row else None


def get_node_by_device(user_id: int, device_fingerprint: str) -> dict[str, Any] | None:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM identity_nodes WHERE user_id=? AND device_fingerprint=? "
            "ORDER BY created_at DESC LIMIT 1",
            (int(user_id), device_fingerprint),
        ).fetchone()
    return dict(row) if row else None


def update_node_pubkey(node_id: str, ed25519_pubkey: str) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE identity_nodes SET ed25519_pubkey=? WHERE node_id=?",
            (ed25519_pubkey, node_id),
        )
        changed = cur.rowcount
    audit_event(node_id=node_id, action="node.rotate_key", result="ok" if changed else "missing")
    return bool(changed)


def bind_node_wg(node_id: str, wg_pubkey: str, device_fingerprint: str | None = None) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE identity_nodes SET wg_pubkey=?, device_fingerprint=COALESCE(?, device_fingerprint) "
            "WHERE node_id=?",
            (wg_pubkey, device_fingerprint, node_id),
        )
        changed = cur.rowcount
    audit_event(node_id=node_id, action="node.bind_wg", result="ok" if changed else "missing", detail=wg_pubkey[:12])
    return bool(changed)


def grant_creator(
    user_id: int,
    node_id: str,
    scopes: Iterable[str] | None = None,
    approved_by: int | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    node = get_node(node_id)
    if not node:
        raise NodeIdentityError("node not found")
    if node["profile"] != PROFILE_CREATOR:
        raise NodeIdentityError("creator grant requires creator profile")
    selected = list(scopes or CREATOR_SCOPES.keys())
    for scope in selected:
        if scope not in CREATOR_SCOPES:
            raise NodeIdentityError(f"invalid creator scope: {scope}")
    grant_id = f"grant_{secrets.token_hex(8)}"
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE identity_creator_grants SET status='revoked', revoke_reason='superseded' "
            "WHERE node_id=? AND status='approved'",
            (node_id,),
        )
        cur.execute(
            "INSERT INTO identity_creator_grants(grant_id, user_id, node_id, status, scopes, "
            "approved_by, approved_at, expires_at, created_at) "
            "VALUES (?,?,?, 'approved', ?,?,?,?,?)",
            (grant_id, int(user_id), node_id, json.dumps(selected), approved_by, now, expires_at, now),
        )
    audit_event(
        node_id=node_id,
        user_id=user_id,
        profile=node["profile"],
        grant_id=grant_id,
        action="creator.grant",
        result="ok",
        detail=",".join(selected),
    )
    return get_active_grant(node_id) or {}


def revoke_creator_grant(node_id: str, reason: str = "") -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE identity_creator_grants SET status='revoked', revoke_reason=? "
            "WHERE node_id=? AND status='approved'",
            (reason, node_id),
        )
        changed = cur.rowcount
    audit_event(node_id=node_id, action="creator.revoke", result="ok" if changed else "missing", detail=reason)
    return bool(changed)


def apply_creator_grant(
    user_id: int,
    node_id: str,
    scopes: Iterable[str] | None = None,
    note: str = "",
    portfolio_url: str = "",
) -> dict[str, Any]:
    node = get_node(node_id)
    if not node or int(node.get("user_id") or 0) != int(user_id):
        raise NodeIdentityError("node not found")
    if node.get("profile") not in (PROFILE_CREATOR, PROFILE_EDGE):
        raise NodeIdentityError("only edge/creator nodes can apply")
    if node.get("status") != "active":
        raise NodeIdentityError("node not active")
    selected = list(scopes or CREATOR_SCOPES.keys())
    for scope in selected:
        if scope not in CREATOR_SCOPES:
            raise NodeIdentityError(f"invalid creator scope: {scope}")
    with db_cursor() as cur:
        existing = cur.execute(
            "SELECT grant_id FROM identity_creator_grants WHERE node_id=? AND status='pending' "
            "ORDER BY created_at DESC LIMIT 1",
            (node_id,),
        ).fetchone()
    if existing:
        return {"grant_id": existing["grant_id"], "status": "pending", "scopes": selected, "existing": True}
    grant_id = f"grant_{secrets.token_hex(8)}"
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO identity_creator_grants(grant_id, user_id, node_id, status, scopes, "
            "application_note, portfolio_url, created_at) VALUES (?,?,?, 'pending', ?, ?, ?, ?)",
            (grant_id, int(user_id), node_id, json.dumps(selected), note, portfolio_url, now),
        )
    audit_event(
        node_id=node_id,
        user_id=user_id,
        profile=node.get("profile"),
        grant_id=grant_id,
        action="creator.apply",
        result="pending",
        detail=note or ",".join(selected),
    )
    return {"grant_id": grant_id, "status": "pending", "scopes": selected}


def list_creator_applications(status: str = "pending") -> list[dict[str, Any]]:
    sql = (
        "SELECT g.*, n.user_id AS node_user_id, n.profile, n.device_fingerprint, n.status AS node_status "
        "FROM identity_creator_grants g LEFT JOIN identity_nodes n ON n.node_id=g.node_id "
        "WHERE g.status=? ORDER BY g.created_at DESC"
    )
    with db_cursor() as cur:
        rows = cur.execute(sql, (status,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["scopes"] = json.loads(item.get("scopes") or "[]")
        except (TypeError, ValueError):
            item["scopes"] = []
        result.append(item)
    return result


def approve_creator_application(grant_id: str, approved_by: int, review_note: str = "") -> dict[str, Any]:
    with db_cursor(commit=True) as cur:
        row = cur.execute(
            "SELECT * FROM identity_creator_grants WHERE grant_id=? AND status='pending'",
            (grant_id,),
        ).fetchone()
        if not row:
            raise NodeIdentityError("pending application not found")
        node = cur.execute("SELECT * FROM identity_nodes WHERE node_id=?", (row["node_id"],)).fetchone()
        if not node or node["status"] != "active":
            raise NodeIdentityError("node not active")
        now = _now()
        cur.execute(
            "UPDATE identity_nodes SET profile=? WHERE node_id=?",
            (PROFILE_CREATOR, row["node_id"]),
        )
        cur.execute(
            "UPDATE identity_creator_grants SET status='approved', approved_by=?, approved_at=?, "
            "reviewed_at=?, review_note=? WHERE grant_id=?",
            (approved_by, now, now, review_note, grant_id),
        )
        cur.execute(
            "UPDATE identity_creator_grants SET status='revoked', revoke_reason='superseded' "
            "WHERE node_id=? AND status='approved' AND grant_id<>?",
            (row["node_id"], grant_id),
        )
    audit_event(
        node_id=row["node_id"],
        user_id=row["user_id"],
        profile=PROFILE_CREATOR,
        grant_id=grant_id,
        action="creator.approve",
        result="ok",
        detail=review_note,
    )
    return get_active_grant(row["node_id"]) or {}


def reject_creator_application(grant_id: str, reviewed_by: int, reason: str = "") -> bool:
    with db_cursor(commit=True) as cur:
        row = cur.execute(
            "SELECT * FROM identity_creator_grants WHERE grant_id=? AND status='pending'",
            (grant_id,),
        ).fetchone()
        if not row:
            raise NodeIdentityError("pending application not found")
        cur.execute(
            "UPDATE identity_creator_grants SET status='rejected', approved_by=?, reviewed_at=?, "
            "review_note=? WHERE grant_id=?",
            (reviewed_by, _now(), reason, grant_id),
        )
    audit_event(
        node_id=row["node_id"],
        user_id=row["user_id"],
        grant_id=grant_id,
        action="creator.reject",
        result="ok",
        detail=reason,
    )
    return True


def get_active_grant(node_id: str) -> dict[str, Any] | None:
    now = _now()
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM identity_creator_grants WHERE node_id=? AND status='approved' "
            "AND (expires_at IS NULL OR expires_at='' OR expires_at>?) "
            "ORDER BY approved_at DESC LIMIT 1",
            (node_id, now),
        ).fetchone()
    if not row:
        return None
    grant = dict(row)
    try:
        grant["scopes"] = json.loads(grant.get("scopes") or "[]")
    except (TypeError, ValueError):
        grant["scopes"] = []
    return grant


def effective_capabilities(node: dict[str, Any]) -> set[str]:
    if not node or node.get("status") != "active":
        return set()
    caps = set(PROFILE_CAPABILITIES.get(node.get("profile"), set()))
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT capability FROM identity_capabilities WHERE node_id=? "
            "AND (expires_at IS NULL OR expires_at='' OR expires_at>?)",
            (node["node_id"], _now()),
        ).fetchall()
    caps.update(row["capability"] for row in rows)
    return caps


def issue_manifest(
    node_id: str,
    grant_id: str | None = None,
    ttl_minutes: int | None = None,
    capabilities: Iterable[str] | None = None,
) -> str:
    node = get_node(node_id)
    if not node or node.get("status") != "active":
        raise NodeIdentityError("node not active")
    caps = set(capabilities or effective_capabilities(node))
    grant = get_active_grant(node_id)
    creator_caps = set(CREATOR_SCOPES.values())
    if node["profile"] == PROFILE_CREATOR:
        if grant:
            grant_scopes = set(grant.get("scopes") or [])
            caps = {cap for cap in caps if cap not in creator_caps or cap in grant_scopes}
        else:
            caps = {cap for cap in caps if cap not in creator_caps}
    now = int(time.time())
    ttl = int(ttl_minutes or DEFAULT_MANIFEST_TTL_MINUTES)
    payload = {
        "v": MANIFEST_VERSION,
        "node_id": node_id,
        "user_id": int(node["user_id"]),
        "profile": node["profile"],
        "capabilities": sorted(caps),
        "grant_id": (grant or {}).get("grant_id") or grant_id,
        "iat": now,
        "exp": now + max(60, ttl * 60),
        "nonce": secrets.token_hex(8),
    }
    return sign_manifest(payload)


def audit_event(
    action: str,
    node_id: str | None = None,
    user_id: int | None = None,
    profile: str | None = None,
    grant_id: str | None = None,
    capability: str | None = None,
    wg_peer_ip: str | None = None,
    device_fingerprint: str | None = None,
    result: str | None = None,
    detail: str | None = None,
) -> None:
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO identity_audit(node_id, user_id, profile, grant_id, capability, "
                "action, wg_peer_ip, device_fingerprint, result, detail, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node_id, user_id, profile, grant_id, capability, action,
                    wg_peer_ip, device_fingerprint, result, detail, _now(),
                ),
            )
    except Exception:
        # Audit must never break the caller's request path.
        pass


def manifest_allows(manifest: dict[str, Any], capability: str) -> bool:
    return capability in set(manifest.get("capabilities") or [])
