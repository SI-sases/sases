"""Thin sub-AGI adapter.

The actual executor is the SASES service; this adapter only emits structured
heartbeats/status.  It never owns business logic.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from .protocol import make_message
from .tools import build_default_registry


def heartbeat(base_url: str, scope: str = "local") -> dict:
    registry = build_default_registry()
    health = registry.invoke("sub", "node.health", {"base_url": base_url})
    version = registry.invoke("sub", "node.version", {"base_url": base_url})
    data = (health.get("data") or {}) if isinstance(health.get("data"), dict) else {}
    node_id = data.get("node_id") or ((version.get("data") or {}).get("node_id")) or "local"
    version_ok = bool(version.get("ok"))
    ok = (bool(health.get("ok")) and bool(data.get("ok"))) or (health.get("status") == 404 and version_ok)
    evidence = {"health": health, "version": version}
    version_data = (version.get("data") or {}) if isinstance(version.get("data"), dict) else {}
    return make_message(
        "agi.heartbeat" if ok else "agi.event",
        node_id=node_id,
        scope=scope,
        severity="info" if ok else "critical",
        payload={"healthy": ok, "version": version_data.get("commit") or "",
                 "tables": (health.get("data") or {}).get("tables") if isinstance(health.get("data"), dict) else None},
        evidence=evidence,
    ).to_dict()


def _token() -> str:
    token = os.environ.get("SASES_AGI_TOKEN", "").strip()
    if token:
        return token
    path = Path(os.environ.get("SASES_AGI_TOKEN_FILE", str(Path("data") / "agi.token")))
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def post_event(url: str, message: dict, token: str | None = None) -> str:
    req = urllib.request.Request(
        url.rstrip("/") + "/events",
        data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "X-SASES-AGI-Token": token or _token()},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--post", default="", help="main AGI URL, e.g. http://127.0.0.1:8099")
    parser.add_argument("--scope", default="local", choices=["local", "fleet"])
    parser.add_argument("--token", default=None)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    message = heartbeat(args.base_url, args.scope)
    if args.post:
        message["_main_response"] = post_event(args.post, message, args.token)
    print(json.dumps(message, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
