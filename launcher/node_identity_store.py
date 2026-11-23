"""Client-side Ed25519 identity storage for CDK activation."""
from __future__ import annotations

import base64
import json
import os
import secrets
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

IDENTITY_FILE = "node_identity.json"
LICENSE_FILE = "license.json"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _public_from_private(private_b64: str) -> str:
    private = Ed25519PrivateKey.from_private_bytes(_unb64(private_b64))
    raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64(raw)


def load_or_create(root: str | None = None) -> dict:
    root = root or os.getcwd()
    path = os.path.join(root, IDENTITY_FILE)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            private = data.get("ed25519_private_key")
            if private:
                data["ed25519_public_key"] = _public_from_private(private)
                return data
        except Exception:
            pass

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
    data = {
        "ed25519_private_key": _b64(private_raw),
        "ed25519_public_key": _b64(public_raw),
        "node_id": "",
        "profile": "",
        "manifest": "",
    }
    _write(path, data)
    return data


def save_activation(root: str | None, license_data: dict) -> dict:
    root = root or os.getcwd()
    identity = load_or_create(root)
    license_json = license_data.get("license_json") or {}
    node = license_data.get("node_identity") or {}
    if node:
        identity.update({
            "node_id": node.get("node_id", ""),
            "profile": node.get("profile", ""),
            "manifest": node.get("manifest", ""),
            "issuer_public_key": node.get("issuer_public_key", ""),
        })
    _write(os.path.join(root, IDENTITY_FILE), identity)
    if license_json:
        _write(os.path.join(root, LICENSE_FILE), license_json)
    return identity


def _write(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def refresh_manifest(root: str | None = None, base_url: str = "http://120.77.136.90:8001") -> bool:
    """Refresh an expired manifest using the node's own Ed25519 key."""
    import httpx

    root = root or os.getcwd()
    identity = load_or_create(root)
    node_id = identity.get("node_id")
    private_b64 = identity.get("ed25519_private_key")
    if not node_id or not private_b64:
        return False
    timestamp = int(time.time())
    nonce = secrets.token_hex(8)
    message = f"refresh|{node_id}|{timestamp}|{nonce}"
    private = Ed25519PrivateKey.from_private_bytes(_unb64(private_b64))
    signature = _b64(private.sign(message.encode("utf-8")))
    response = httpx.post(
        base_url.rstrip("/") + "/node/manifest/refresh",
        json={"node_id": node_id, "timestamp": timestamp, "nonce": nonce, "signature": signature},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    identity["manifest"] = data["manifest"]
    identity["issuer_public_key"] = data.get("issuer_public_key", "")
    if data.get("manifest_payload", {}).get("profile"):
        identity["profile"] = data["manifest_payload"]["profile"]
    _write(os.path.join(root, IDENTITY_FILE), identity)
    return True
