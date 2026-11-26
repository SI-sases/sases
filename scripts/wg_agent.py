#!/usr/bin/env python3
"""Host-side WireGuard peer agent for the SASES container.

It only accepts authenticated requests to add one peer with one /32.
It never executes arbitrary shell input.
"""
from __future__ import annotations

import base64
import fcntl
import ipaddress
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("SASES_WG_AGENT_TOKEN", "")
HOST = os.environ.get("SASES_WG_AGENT_HOST", "172.17.0.1")
PORT = int(os.environ.get("SASES_WG_AGENT_PORT", "8010"))
IFACE = os.environ.get("SASES_WG_INTERFACE", "wg0")
CIDR = os.environ.get("SASES_WG_CIDR", "10.0.0.0/24")
WG = "/usr/bin/wg"
CONF = os.environ.get("SASES_WG_CONF", f"/etc/wireguard/{IFACE}.conf")
NET = ipaddress.ip_network(CIDR)


def _valid_key(key: str) -> bool:
    if len(key) != 44 or not key.endswith("="):
        return False
    try:
        return len(base64.b64decode(key)) == 32
    except Exception:
        return False


def _existing() -> dict[str, str]:
    out = subprocess.run([WG, "show", IFACE, "allowed-ips"], capture_output=True, text=True, timeout=10)
    peers: dict[str, str] = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            for ip in parts[1].split():
                peers[ip] = parts[0]
    return peers


def _persist(pubkey: str, ip_text: str) -> bool:
    """Append the peer to wg0.conf once, under an exclusive lock."""
    if not os.path.isfile(CONF):
        return False
    lock_path = CONF + ".agent.lock"
    with open(lock_path, "w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        text = open(CONF, encoding="utf-8").read()
        if pubkey in text:
            return True
        if not os.path.exists(CONF + ".bak.agent"):
            with open(CONF + ".bak.agent", "w", encoding="utf-8") as backup:
                backup.write(text)
        block = (
            "\n[Peer]\n"
            f"PublicKey = {pubkey}\n"
            f"AllowedIPs = {ip_text}/32\n"
            "PersistentKeepalive = 25\n"
        )
        with open(CONF, "a", encoding="utf-8") as handle:
            handle.write(block)
        os.chmod(CONF, 0o600)
    return True


def _remove_persist(pubkey: str) -> bool:
    """Remove a peer block from wg0.conf under the same lock."""
    if not os.path.isfile(CONF):
        return False
    lock_path = CONF + ".agent.lock"
    with open(lock_path, "w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        text = open(CONF, encoding="utf-8").read()
        blocks = re.split(r"(?=\n\[Peer\])", text)
        kept = [b for b in blocks if f"PublicKey = {pubkey}" not in b]
        if len(kept) == len(blocks):
            return False
        with open(CONF, "w", encoding="utf-8") as handle:
            handle.write("".join(kept))
        os.chmod(CONF, 0o600)
    return True


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "iface": IFACE, "cidr": CIDR})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/peer", "/peer/remove"):
            self._send(404, {"error": "not found"})
            return
        if not TOKEN or self.headers.get("X-SASES-WG-Token", "") != TOKEN:
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode())
            pubkey = str(body.get("pubkey", ""))
            if not _valid_key(pubkey):
                raise ValueError("invalid pubkey")
            if self.path == "/peer/remove":
                subprocess.run(
                    [WG, "set", IFACE, "peer", pubkey, "remove"],
                    check=False, capture_output=True, text=True, timeout=10,
                )
                removed = _remove_persist(pubkey)
                print(f"peer removed pubkey={pubkey[:8]} config_removed={removed}", flush=True)
                self._send(200, {"ok": True, "config_removed": removed})
                return
            ip_text = str(body.get("ip", ""))
            node_id = str(body.get("node_id", ""))
            ip = ipaddress.ip_address(ip_text)
            if ip not in NET or ip in (NET.network_address, NET.broadcast_address):
                raise ValueError("ip outside pool")
            existing = _existing()
            if ip_text in existing and existing[ip_text] != pubkey:
                self._send(409, {"error": "ip already assigned"})
                return
            if ip_text in existing and existing[ip_text] == pubkey:
                persisted = _persist(pubkey, ip_text)
                self._send(200, {"ok": True, "idempotent": True, "persisted": persisted})
                return
            subprocess.run(
                [WG, "set", IFACE, "peer", pubkey, "allowed-ips", f"{ip_text}/32", "persistent-keepalive", "25"],
                check=True, capture_output=True, text=True, timeout=10,
            )
            persisted = _persist(pubkey, ip_text)
            print(f"peer added node={node_id} ip={ip_text} persisted={persisted}", flush=True)
            self._send(200, {"ok": True, "ip": ip_text, "persisted": persisted})
        except subprocess.CalledProcessError as exc:
            self._send(500, {"error": "wg failed", "detail": (exc.stderr or "").strip()[:200]})
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    if not TOKEN:
        print("SASES_WG_AGENT_TOKEN is required", file=sys.stderr)
        raise SystemExit(2)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
