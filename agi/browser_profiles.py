"""Browser profile to CDP endpoint mapping.

SASES_BROWSER_PROFILES is a JSON object:
  {"default": "http://127.0.0.1:9222", "account_a": "http://127.0.0.1:9223"}
"""
from __future__ import annotations

import json
import os


def mapping() -> dict[str, str]:
    raw = os.environ.get("SASES_BROWSER_PROFILES", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items() if str(v).strip()}


def cdp_for(profile: str) -> str:
    return mapping().get(profile or "default", os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222"))
