#!/usr/bin/env python3
"""Reference CDK activation that also provisions an edge node identity."""
from __future__ import annotations

import argparse
import base64
import json
import os

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def keypair():
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
    enc = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return enc(private_raw), enc(public_raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--key", required=True)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--device", default="reference-device")
    parser.add_argument("--out", default=".")
    parser.add_argument("--wg-pubkey")
    args = parser.parse_args()

    private, public = keypair()
    payload = {
        "key_code": args.key,
        "device_fingerprint": args.device,
        "user_id": args.user_id,
        "ed25519_pubkey": public,
    }
    if args.wg_pubkey:
        payload["wg_pubkey"] = args.wg_pubkey
    response = httpx.post(args.base + "/auth/license/activate", json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "license.json"), "w", encoding="utf-8") as handle:
        json.dump(data["license_json"], handle, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "node_identity.json"), "w", encoding="utf-8") as handle:
        json.dump({
            "node_id": data["node_identity"]["node_id"],
            "profile": data["node_identity"]["profile"],
            "ed25519_private_key": private,
            "ed25519_public_key": public,
            "manifest": data["node_identity"]["manifest"],
            "issuer_public_key": data["node_identity"]["issuer_public_key"],
        }, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"status": data["status"], "node": data["node_identity"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
