"""Shared checkpoint phases for local browser adapters."""
from __future__ import annotations

import json
import os
import time


def _path() -> str:
    return os.environ.get("SASES_CHECKPOINT_FILE", "")


def load() -> dict:
    path = _path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        return json.loads(open(path, encoding="utf-8").read() or "{}")
    except Exception:
        return {}


def save(phase: str) -> None:
    path = _path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, "w", encoding="utf-8").write(json.dumps({"phase": phase}))
        pause_file = os.environ.get("SASES_BROWSER_PAUSE_FILE", "")
        if os.path.isfile(pause_file):
            wanted = open(pause_file, encoding="utf-8").read().strip()
            if wanted == phase:
                time.sleep(float(os.environ.get("SASES_BROWSER_PAUSE_SECONDS", "20")))
    except Exception:
        pass


def clear() -> None:
    path = _path()
    if not path:
        return
    try:
        os.remove(path)
    except Exception:
        pass
