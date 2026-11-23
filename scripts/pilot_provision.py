#!/usr/bin/env python3
"""Provision a pilot client: WireGuard config + edge node identity + manifest.

Run on the Shenzhen server as root:
  python scripts/pilot_provision.py --user-id 1 --name pilot-1 --ip 10.10.0.20
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import node_identity as ni  # noqa: E402

OUT_DIR = "/root/wg_clients/pilots"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--ip", required=True)
    args = parser.parse_args()

    subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "wg_client.py"),
         "add", "--name", args.name, "--ip", args.ip],
        cwd=ROOT,
        check=True,
    )

    wg_path = f"/root/wg_clients/{args.name}.conf"
    with open(wg_path, encoding="utf-8") as handle:
        wg_conf = handle.read()

    wg_pubkey = ""
    for line in subprocess.check_output(["wg", "show", "wg1", "allowed-ips"], text=True).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith(args.ip + "/"):
            wg_pubkey = parts[0]
            break

    private, public = ni.generate_node_keypair()
    node = ni.create_node(args.user_id, ni.PROFILE_EDGE, ed25519_pubkey=public)
    if wg_pubkey:
        ni.bind_node_wg(node["node_id"], wg_pubkey, device_fingerprint=args.name)
    manifest = ni.issue_manifest(node["node_id"])

    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {
        "user_id": args.user_id,
        "name": args.name,
        "node_id": node["node_id"],
        "profile": node["profile"],
        "ed25519_private_key": private,
        "ed25519_public_key": public,
        "wg_pubkey": wg_pubkey,
        "issuer_public_key": ni.issuer_public_key(),
        "manifest": manifest,
        "wg_conf": wg_conf,
    }
    out = os.path.join(OUT_DIR, f"{args.name}.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.chmod(out, 0o600)
    print(f"created {out}")
    print(f"node_id {node['node_id']}")
    print(f"device_ip {args.ip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
