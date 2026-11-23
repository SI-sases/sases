#!/usr/bin/env python3
"""SASES node identity admin CLI.

Examples:
  python scripts/node_admin.py init-official --user-id 3
  python scripts/node_admin.py init-creator --user-id 7 --wg-pubkey KEY
  python scripts/node_admin.py grant-creator --node-id node_xxx --scopes publish_tool
  python scripts/node_admin.py manifest --node-id node_xxx
  python scripts/node_admin.py revoke-node --node-id node_xxx --reason lost
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import node_identity as ni  # noqa: E402
from core.db import init_db  # noqa: E402
from core.migrations import ensure_schema  # noqa: E402


def _print(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _create(args, profile: str):
    private, public = ni.generate_node_keypair()
    node = ni.create_node(
        user_id=args.user_id,
        profile=profile,
        ed25519_pubkey=public,
        wg_pubkey=args.wg_pubkey,
        device_fingerprint=args.device_fingerprint,
        node_id=args.node_id,
    )
    manifest = ni.issue_manifest(node["node_id"])
    _print({
        "node": node,
        "private_key_once": private,
        "public_key": public,
        "manifest": manifest,
        "issuer_public_key": ni.issuer_public_key(),
        "warning": "private_key_once is shown only now; store it in the client secure store",
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="SASES node identity admin")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-edge", help="create an edge node")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--node-id")
    p.add_argument("--wg-pubkey")
    p.add_argument("--device-fingerprint")
    p.set_defaults(func=lambda a: _create(a, ni.PROFILE_EDGE))

    p = sub.add_parser("init-creator", help="create a creator node (grant still required)")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--node-id")
    p.add_argument("--wg-pubkey")
    p.add_argument("--device-fingerprint")
    p.set_defaults(func=lambda a: _create(a, ni.PROFILE_CREATOR))

    p = sub.add_parser("init-official", help="create an official node")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--node-id")
    p.add_argument("--wg-pubkey")
    p.add_argument("--device-fingerprint")
    p.set_defaults(func=lambda a: _create(a, ni.PROFILE_OFFICIAL))

    p = sub.add_parser("grant-creator", help="approve creator scopes")
    p.add_argument("--node-id", required=True)
    p.add_argument("--scopes", default="provide_api,publish_tool,publish_template,propose_registry")
    p.add_argument("--approved-by", type=int)
    p.add_argument("--expires-at")
    p.set_defaults(func=lambda a: _print(ni.grant_creator(
        user_id=int((ni.get_node(a.node_id) or {}).get("user_id") or 0),
        node_id=a.node_id,
        scopes=[s.strip() for s in a.scopes.split(",") if s.strip()],
        approved_by=a.approved_by,
        expires_at=a.expires_at,
    )))

    p = sub.add_parser("revoke-grant", help="revoke the active creator grant")
    p.add_argument("--node-id", required=True)
    p.add_argument("--reason", default="revoked by admin")
    p.set_defaults(func=lambda a: _print({"ok": ni.revoke_creator_grant(a.node_id, a.reason)}))

    p = sub.add_parser("list-applications", help="list creator applications")
    p.add_argument("--status", default="pending")
    p.set_defaults(func=lambda a: _print(ni.list_creator_applications(a.status)))

    p = sub.add_parser("approve-creator", help="approve a creator application")
    p.add_argument("--grant-id", required=True)
    p.add_argument("--reviewed-by", type=int, default=3)
    p.add_argument("--note", default="")
    p.set_defaults(func=lambda a: _print(ni.approve_creator_application(a.grant_id, a.reviewed_by, a.note)))

    p = sub.add_parser("reject-creator", help="reject a creator application")
    p.add_argument("--grant-id", required=True)
    p.add_argument("--reviewed-by", type=int, default=3)
    p.add_argument("--reason", default="")
    p.set_defaults(func=lambda a: _print({"ok": ni.reject_creator_application(a.grant_id, a.reviewed_by, a.reason)}))

    p = sub.add_parser("revoke-node", help="revoke a node")
    p.add_argument("--node-id", required=True)
    p.add_argument("--reason", default="revoked by admin")
    p.set_defaults(func=lambda a: _print({"ok": ni.revoke_node(a.node_id, a.reason)}))

    p = sub.add_parser("bind-wg", help="bind a node to a WireGuard public key")
    p.add_argument("--node-id", required=True)
    p.add_argument("--wg-pubkey", required=True)
    p.add_argument("--device-fingerprint")
    p.set_defaults(func=lambda a: _print({"ok": ni.bind_node_wg(a.node_id, a.wg_pubkey, a.device_fingerprint)}))

    p = sub.add_parser("manifest", help="issue a manifest")
    p.add_argument("--node-id", required=True)
    p.add_argument("--ttl-minutes", type=int)
    p.set_defaults(func=lambda a: _print({
        "manifest": ni.issue_manifest(a.node_id, ttl_minutes=a.ttl_minutes),
        "issuer_public_key": ni.issuer_public_key(),
    }))

    p = sub.add_parser("list", help="list nodes")
    p.add_argument("--user-id", type=int)
    p.add_argument("--status")
    p.set_defaults(func=lambda a: _print(ni.list_nodes(a.user_id, a.status)))

    args = parser.parse_args()
    init_db()
    ensure_schema()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
