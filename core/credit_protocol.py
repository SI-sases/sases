"""Canonical SASES credit protocol.

There is exactly one credit protocol in the official network. Nodes that speak a
different protocol are rejected for credit sync. Forks may run their own system,
but they are not compatible with the official network.
"""
from __future__ import annotations

import hashlib
import json
import os

PROTOCOL = "sases-credit-v1"
RULES = {
    "credits_per_compute": 5.0,
    "stake_apy": 0.1,
    "pool_share": 0.5,
    "max_red_packet": 300,
    "credit_types": ["credits", "compute"],
}
RULES_HASH = hashlib.sha256(
    json.dumps(RULES, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def strict() -> bool:
    return os.environ.get("SASES_CREDIT_STRICT", "0") in ("1", "true", "yes")


def accepted(value: str | None) -> bool:
    """Accept the canonical protocol. Legacy peers may omit it unless strict."""
    if value:
        return value == PROTOCOL
    return not strict()


def describe() -> dict:
    return {"protocol": PROTOCOL, "rules": RULES, "rules_hash": RULES_HASH}
