"""Read-only browser snapshot helper."""
from __future__ import annotations

import os
import time
from pathlib import Path

from .browser import _python, _root, _run_cmd


def cleanup(root: str | Path | None = None, max_age_days: int | None = None) -> list[str]:
    base = Path(root) if root else _root() / "data" / "browser_snapshots"
    if not base.is_dir():
        return []
    days = int(os.environ.get("SASES_SNAPSHOT_TTL_DAYS", max_age_days or 7))
    cutoff = time.time() - max(1, days) * 86400
    removed = []
    for path in base.glob("*"):
        if path.is_file() and path.stat().st_mtime < cutoff:
            try:
                path.unlink()
                removed.append(path.name)
            except OSError:
                pass
    return removed


def capture(screenshot: str = "", max_elements: int = 200, timeout: int = 30) -> dict:
    script = _root() / "scripts" / "browser_snapshot.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_snapshot.py missing"}
    cmd = [_python(), str(script), "--max-elements", str(max_elements)]
    if screenshot:
        Path(screenshot).parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--screenshot", str(screenshot)]
    return _run_cmd(cmd, timeout=timeout)
