import base64
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import core.db as db
import core.node_identity as ni
from core.migrations import _migrate_v13_node_identity


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "users.db"))
    with db.db_cursor(commit=True) as cur:
        _migrate_v13_node_identity(cur)

    issuer = Ed25519PrivateKey.generate()
    raw = issuer.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setenv("SASES_NODE_SIGNING_KEY", _b64(raw))
    yield


def test_manifest_roundtrip_and_tamper(temp_db):
    _priv, pub = ni.generate_node_keypair()
    node = ni.create_node(1, "edge", ed25519_pubkey=pub)
    token = ni.issue_manifest(node["node_id"])
    payload = ni.decode_manifest(token)
    assert payload["profile"] == "edge"
    assert payload["node_id"] == node["node_id"]
    assert ni.CAP_CALL_API in payload["capabilities"]
    assert ni.CAP_WRITE_REGISTRY not in payload["capabilities"]

    body, sig = token.split(".", 1)
    tampered = body[:-2] + ("AA" if not body.endswith("AA") else "BB") + "." + sig
    with pytest.raises(ni.ManifestError):
        ni.decode_manifest(tampered)


def test_expired_manifest_rejected(temp_db):
    payload = {
        "v": ni.MANIFEST_VERSION,
        "node_id": "node_x",
        "user_id": 1,
        "profile": "edge",
        "capabilities": ["call_api"],
        "grant_id": None,
        "iat": 0,
        "exp": int(time.time()) - 1,
        "nonce": "x",
    }
    token = ni.sign_manifest(payload)
    with pytest.raises(ni.ManifestError):
        ni.decode_manifest(token)


def test_creator_requires_grant(temp_db):
    _priv, pub = ni.generate_node_keypair()
    node = ni.create_node(2, "creator", ed25519_pubkey=pub)

    before = ni.decode_manifest(ni.issue_manifest(node["node_id"]))
    assert ni.CAP_PUBLISH_TOOL not in before["capabilities"]

    ni.grant_creator(2, node["node_id"], ["publish_tool"], approved_by=99)
    after = ni.decode_manifest(ni.issue_manifest(node["node_id"]))
    assert ni.CAP_PUBLISH_TOOL in after["capabilities"]
    assert ni.CAP_PROVIDE_API not in after["capabilities"]

    ni.revoke_creator_grant(node["node_id"], "test")
    revoked = ni.decode_manifest(ni.issue_manifest(node["node_id"]))
    assert ni.CAP_PUBLISH_TOOL not in revoked["capabilities"]


def test_official_capabilities(temp_db):
    _priv, pub = ni.generate_node_keypair()
    node = ni.create_node(3, "official", ed25519_pubkey=pub)
    caps = ni.decode_manifest(ni.issue_manifest(node["node_id"]))["capabilities"]
    assert ni.CAP_INSTALL_TOOL in caps
    assert ni.CAP_WRITE_REGISTRY in caps
    assert ni.CAP_ISSUE_LICENSE in caps
    assert ni.CAP_ADMIN_CONSOLE in caps


def test_revoked_node_cannot_get_manifest(temp_db):
    _priv, pub = ni.generate_node_keypair()
    node = ni.create_node(4, "edge", ed25519_pubkey=pub)
    assert ni.revoke_node(node["node_id"], "test")
    with pytest.raises(ni.NodeIdentityError):
        ni.issue_manifest(node["node_id"])
