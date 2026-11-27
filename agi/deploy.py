"""Deployment planning only.

P1 deliberately returns a reviewed plan instead of executing remote commands.
A host deployment agent will execute the same commands later.
"""
from __future__ import annotations

import re

_NODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def _check(value: str, pattern: re.Pattern, name: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {name}")
    return value


def plan_stage(node_id: str = "local", version: str = "next", port: int = 8002) -> dict:
    node_id = _check(node_id, _NODE_RE, "node_id")
    version = _check(version, _VERSION_RE, "version")
    return {
        "action": "stage",
        "node_id": node_id,
        "version": version,
        "port": port,
        "dry_run": True,
        "requires_approval": True,
        "commands": [
            "backup users.db and .env",
            f"create staging tree for {version}",
            f"start staging on 127.0.0.1:{port}",
            f"GET http://127.0.0.1:{port}/health",
        ],
        "acceptance": ["health ok", "schema ok", "login ok"],
    }


def plan_promote(node_id: str = "local", version: str = "next") -> dict:
    node_id = _check(node_id, _NODE_RE, "node_id")
    version = _check(version, _VERSION_RE, "version")
    return {
        "action": "promote",
        "node_id": node_id,
        "version": version,
        "dry_run": True,
        "requires_approval": True,
        "commands": [
            "verify staging health again",
            "backup current tree",
            "switch systemd to staging",
            "GET /health on production",
        ],
        "rollback": "deploy.rollback",
    }


def plan_rollback(node_id: str = "local", version: str = "previous") -> dict:
    node_id = _check(node_id, _NODE_RE, "node_id")
    version = _check(version, _VERSION_RE, "version")
    return {
        "action": "rollback",
        "node_id": node_id,
        "version": version,
        "dry_run": True,
        "requires_approval": True,
        "commands": ["stop staged service", "restore previous tree", "restart and verify /health"],
    }
