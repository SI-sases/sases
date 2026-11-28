"""Task-local browser tab management."""
from __future__ import annotations

from .browser import _python, _root, _run_cmd


def _tab(action: str) -> dict:
    script = _root() / "scripts" / "browser_tab.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_tab.py missing"}
    return _run_cmd([_python(), str(script), action], timeout=20)


def new_tab() -> dict:
    return _tab("new")


def close_tab() -> dict:
    return _tab("close")
