"""Read-only browser snapshot helper."""
from __future__ import annotations

from pathlib import Path

from .browser import _python, _root, _run_cmd


def capture(screenshot: str = "", max_elements: int = 200, timeout: int = 30) -> dict:
    script = _root() / "scripts" / "browser_snapshot.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_snapshot.py missing"}
    cmd = [_python(), str(script), "--max-elements", str(max_elements)]
    if screenshot:
        Path(screenshot).parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--screenshot", str(screenshot)]
    return _run_cmd(cmd, timeout=timeout)
