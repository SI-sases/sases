"""Task-local browser tab management."""
from __future__ import annotations

from .browser import _python, _root, _run_cmd


def _tab(action: str, name: str = "") -> dict:
    script = _root() / "scripts" / "browser_tab.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_tab.py missing"}
    cmd = [_python(), str(script), action]
    if name:
        cmd += ["--name", name]
    return _run_cmd(cmd, timeout=20)


def new_tab(name: str = "") -> dict:
    return _tab("new", name)


def close_tab(name: str = "") -> dict:
    return _tab("close", name)
