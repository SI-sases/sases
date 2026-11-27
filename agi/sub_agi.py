"""Thin sub-AGI adapter.

The actual executor is the SASES service; this adapter only emits structured
heartbeats/status.  It never owns business logic.
"""
from __future__ import annotations

import argparse
import json

from .protocol import make_message
from .tools import build_default_registry


def heartbeat(base_url: str) -> dict:
    registry = build_default_registry()
    health = registry.invoke("sub", "node.health", {"base_url": base_url})
    version = registry.invoke("sub", "node.version", {"base_url": base_url})
    data = (health.get("data") or {}) if isinstance(health.get("data"), dict) else {}
    node_id = data.get("node_id") or ((version.get("data") or {}).get("node_id")) or "local"
    version_ok = bool(version.get("ok"))
    ok = (bool(health.get("ok")) and bool(data.get("ok"))) or (health.get("status") == 404 and version_ok)
    return make_message(
        "agi.heartbeat" if ok else "agi.event",
        node_id=node_id,
        severity="info" if ok else "critical",
        payload={"healthy": ok},
        evidence={"health": health, "version": version},
    ).to_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    print(json.dumps(heartbeat(args.base_url), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
