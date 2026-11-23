#!/usr/bin/env python3
"""Provision and revoke WireGuard wg1 clients for SASES.

Run on the Shenzhen server as root:
  python scripts/wg_client.py add --name alice --ip 10.10.0.11
  python scripts/wg_client.py list
  python scripts/wg_client.py revoke --name alice
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess

CONF = "/etc/wireguard/wg1.conf"
CLIENT_DIR = "/root/wg_clients"
REVOKED_DIR = "/root/wg_clients/revoked"
ENDPOINT = os.getenv("WG_ENDPOINT", "120.77.136.90:51821")
NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")


def run(cmd, input_text=None):
    return subprocess.check_output(cmd, input=input_text, text=True).strip()


def keypair():
    private = run(["wg", "genkey"])
    public = run(["wg", "pubkey"], input_text=private + "\n")
    return private, public


def server_pubkey():
    return run(["wg", "show", "wg1", "public-key"])


def read_conf():
    with open(CONF, encoding="utf-8") as handle:
        return handle.read()


def write_conf(text):
    with open(CONF, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(CONF, 0o600)


def peers():
    result = []
    block = None
    for line in read_conf().splitlines():
        stripped = line.strip()
        if stripped == "[Peer]":
            if block:
                result.append(block)
            block = {"name": "", "public_key": "", "allowed_ips": ""}
            continue
        if block is None:
            continue
        if stripped.lower().startswith("# wg-client:"):
            block["name"] = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("publickey"):
            block["public_key"] = stripped.split("=", 1)[1].strip()
        elif stripped.lower().startswith("allowedips"):
            block["allowed_ips"] = stripped.split("=", 1)[1].strip()
    if block:
        result.append(block)
    return [p for p in result if p.get("public_key")]


def add(args):
    if not NAME_RE.match(args.name):
        raise SystemExit("invalid name")
    for peer in peers():
        if peer["name"] == args.name:
            raise SystemExit(f"client already exists: {args.name}")
        if peer["allowed_ips"].startswith(args.ip + "/"):
            raise SystemExit(f"ip already used: {args.ip}")
    if args.ip == "10.10.0.1":
        raise SystemExit("10.10.0.1 is the server address")

    private, public = keypair()
    block = f"\n[Peer]\n# wg-client: {args.name}\nPublicKey = {public}\nAllowedIPs = {args.ip}/32\n"
    write_conf(read_conf().rstrip() + "\n" + block)
    subprocess.run(["wg", "set", "wg1", "peer", public, "allowed-ips", f"{args.ip}/32"], check=True)

    os.makedirs(CLIENT_DIR, exist_ok=True)
    client_conf = f"""[Interface]
PrivateKey = {private}
Address = {args.ip}/32

[Peer]
PublicKey = {server_pubkey()}
Endpoint = {ENDPOINT}
AllowedIPs = 10.10.0.0/24
PersistentKeepalive = 25
"""
    path = os.path.join(CLIENT_DIR, f"{args.name}.conf")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(client_conf)
    os.chmod(path, 0o600)
    print(f"created {path}")
    print(f"device_ip {args.ip}")


def revoke(args):
    target = None
    for peer in peers():
        if peer["name"] == args.name:
            target = peer
            break
    if not target:
        raise SystemExit(f"client not found: {args.name}")

    lines = read_conf().splitlines()
    keep = []
    skipping = False
    for line in lines:
        if line.strip() == "[Peer]":
            skipping = False
        if line.strip().lower() == f"# wg-client: {args.name}".lower():
            skipping = True
            if keep and keep[-1].strip() == "[Peer]":
                keep.pop()
            continue
        if skipping:
            continue
        keep.append(line)
    write_conf("\n".join(keep).rstrip() + "\n")
    subprocess.run(["wg", "set", "wg1", "peer", target["public_key"], "remove"], check=True)

    os.makedirs(REVOKED_DIR, exist_ok=True)
    src = os.path.join(CLIENT_DIR, f"{args.name}.conf")
    if os.path.exists(src):
        shutil.move(src, os.path.join(REVOKED_DIR, f"{args.name}.conf"))
    print(f"revoked {args.name}")


def list_clients(args):
    for peer in peers():
        print(f"{peer['name'] or '-'}\t{peer['allowed_ips']}\t{peer['public_key']}")


def main():
    parser = argparse.ArgumentParser(description="SASES wg1 client admin")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add")
    p.add_argument("--name", required=True)
    p.add_argument("--ip", required=True)
    p.set_defaults(func=add)

    p = sub.add_parser("revoke")
    p.add_argument("--name", required=True)
    p.set_defaults(func=revoke)

    p = sub.add_parser("list")
    p.set_defaults(func=list_clients)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
