"""Quiet startup logging helpers.

Set SASES_BOOT_VERBOSE=1 to restore per-service startup lines.
Errors are never suppressed by these helpers; callers print errors directly.
"""
from __future__ import annotations

import os


def verbose() -> bool:
    return os.environ.get("SASES_BOOT_VERBOSE", "").lower() in ("1", "true", "yes", "on")


def boot(message: str) -> None:
    if verbose():
        print(message, flush=True)
