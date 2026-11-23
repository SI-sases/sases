# core/node_auth.py
"""Request-level node permission checks.

Modes:
  off     - do nothing
  shadow  - verify and audit, never block (default)
  enforce - reject missing/invalid manifests for protected routes
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from core import node_identity as ni

MODE = os.getenv("SASES_NODE_AUTH_MODE", "shadow").strip().lower()
ENFORCE_PRESENT = os.getenv("SASES_NODE_AUTH_ENFORCE_PRESENT", "true").strip().lower() not in ("0", "false", "no")
MANIFEST_HEADER = "X-SASES-Node-Manifest"


@dataclass
class NodeCheck:
    ok: bool
    reason: str = ""
    status_code: int = 0
    node_id: str | None = None
    user_id: int | None = None
    profile: str | None = None
    capability: str | None = None


def required_capability(path: str, method: str) -> str | None:
    if path.startswith("/admin"):
        return ni.CAP_ADMIN_CONSOLE
    if path.startswith("/tools/install"):
        return ni.CAP_INSTALL_TOOL
    if path.startswith("/tools/") and method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        return ni.CAP_INSTALL_TOOL
    return None


def check_request(path: str, method: str, manifest: str | None, require_manifest: bool = False) -> NodeCheck:
    capability = required_capability(path, method)
    if require_manifest and not capability:
        capability = ni.CAP_CALL_API
    if not manifest:
        if capability or require_manifest:
            return NodeCheck(False, "manifest required", 401, capability=capability)
        return NodeCheck(True)

    try:
        payload = ni.decode_manifest(manifest)
    except ni.ManifestError as exc:
        return NodeCheck(False, f"invalid manifest: {exc}", 401)

    node = ni.get_node(payload.get("node_id", ""))
    if not node:
        return NodeCheck(False, "node not found", 401, node_id=payload.get("node_id"))
    if node.get("status") != "active":
        return NodeCheck(False, "node revoked", 403, node_id=node.get("node_id"))
    if int(payload.get("user_id", -1)) != int(node.get("user_id", -2)):
        return NodeCheck(False, "manifest user mismatch", 403, node_id=node.get("node_id"))
    if payload.get("profile") != node.get("profile"):
        return NodeCheck(False, "manifest profile mismatch", 403, node_id=node.get("node_id"))

    caps = ni.effective_capabilities(node)
    if capability and capability not in caps:
        return NodeCheck(
            False,
            f"capability required: {capability}",
            403,
            node_id=node.get("node_id"),
            user_id=node.get("user_id"),
            profile=node.get("profile"),
            capability=capability,
        )
    return NodeCheck(
        True,
        node_id=node.get("node_id"),
        user_id=node.get("user_id"),
        profile=node.get("profile"),
        capability=capability,
    )


def should_block(check: NodeCheck, manifest: str | None) -> bool:
    """Enforce only for clients that actually present a manifest.

    Legacy clients without a manifest remain in shadow mode until the rollout
    is complete. A client that presents an invalid/insufficient manifest is
    always rejected, otherwise it could bypass enforcement by sending garbage.
    """
    if check.ok:
        return False
    if MODE == "enforce":
        return True
    return bool(ENFORCE_PRESENT and manifest)


def audit_check(path: str, method: str, check: NodeCheck, wg_peer_ip: str | None = None, blocked: bool = False) -> None:
    if check.ok:
        return
    ni.audit_event(
        action=f"{method.upper()} {path}",
        node_id=check.node_id,
        user_id=check.user_id,
        profile=check.profile,
        capability=check.capability,
        wg_peer_ip=wg_peer_ip,
        result="denied" if (blocked or MODE == "enforce") else "shadow",
        detail=check.reason,
    )
