"""Region routing policy for the SASES HQ node."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(ROOT, "region_policy.json")


def load() -> dict:
    with open(POLICY, encoding="utf-8-sig") as handle:
        return json.load(handle)


def route(audience: str) -> str | None:
    audience = (audience or "").strip().lower()
    for name, region in load().get("regions", {}).items():
        if audience in (region.get("audience", ""), region.get("scope", "")):
            return name
    return None


if __name__ == "__main__":
    import sys
    print(route(sys.argv[1] if len(sys.argv) > 1 else ""))
