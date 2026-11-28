"""Opt-in browser fallback policy.

Auto profile fallback is disabled by default. Even when enabled it only
creates a new queued task; write/publish actions still require approval.
"""
from __future__ import annotations

import os


def enabled() -> bool:
    return os.environ.get("SASES_AUTO_PROFILE_FALLBACK", "").lower() in ("1", "true", "yes", "on")


def choose_profile(current: str, profiles: list[str]) -> str:
    for name in profiles:
        if name and name != current:
            return name
    return ""
