"""Client-side WireGuard tunnel provisioning for the SASES launcher."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request

from .wireguard_setup import ensure_wireguard, find_config, import_tunnel, is_installed

WG_EXE = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "WireGuard", "wg.exe")


def _run(args: list[str], data: str | None = None) -> str:
    proc = subprocess.run(args, input=data, capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "wg command failed").strip()[:200])
    return proc.stdout.strip()


def generate_keypair() -> tuple[str, str]:
    if not os.path.isfile(WG_EXE):
        raise RuntimeError("wg.exe not found; install WireGuard first")
    private = _run([WG_EXE, "genkey"])
    public = _run([WG_EXE, "pubkey"], private + "\n")
    return private, public


def request_config(manifest: str, wg_pubkey: str, base_url: str | None = None) -> dict:
    base = (base_url or os.environ.get("SASES_TUNNEL_API", "http://127.0.0.1:8001")).rstrip("/")
    req = urllib.request.Request(
        base + "/node/tunnel/config",
        data=json.dumps({"wg_pubkey": wg_pubkey}).encode(),
        headers={"Content-Type": "application/json", "X-SASES-Node-Manifest": manifest},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def write_config(root: str, private: str, cfg: dict) -> str:
    base = os.path.join(root, "wireguard")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, "wg0.conf")
    text = (
        "[Interface]\n"
        f"PrivateKey = {private}\n"
        f"Address = {cfg['address']}\n"
        f"DNS = {cfg.get('dns', '1.1.1.1')}\n\n"
        "[Peer]\n"
        f"PublicKey = {cfg['server_public_key']}\n"
        f"Endpoint = {cfg['endpoint']}\n"
        f"AllowedIPs = {cfg.get('allowed_ips', '10.0.0.0/24')}\n"
        "PersistentKeepalive = 25\n"
    )
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def ensure_tunnel(root: str | None = None, base_url: str | None = None) -> dict:
    root = root or os.getcwd()
    existing = find_config(root)
    if existing:
        import_tunnel(existing)
        return {"ok": True, "config": existing, "existing": True}
    identity_path = os.path.join(root, "node_identity.json")
    if not os.path.isfile(identity_path):
        raise RuntimeError("node_identity.json missing; activate CDK first")
    with open(identity_path, encoding="utf-8") as handle:
        manifest = (json.load(handle) or {}).get("manifest")
    if not manifest:
        raise RuntimeError("node manifest missing; activate CDK first")
    if not is_installed():
        ensure_wireguard(root)
    private, public = generate_keypair()
    cfg = request_config(manifest, public, base_url)
    path = write_config(root, private, cfg)
    import_tunnel(path)
    return {"ok": True, "config": path, "address": cfg.get("address"), "existing": False}
