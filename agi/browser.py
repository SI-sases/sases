"""Browser tools backed by the local CDP Playwright worker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _python() -> str:
    explicit = os.environ.get("SASES_BROWSER_PYTHON", "").strip()
    if explicit and Path(explicit).exists():
        return explicit
    return sys.executable


def _run(args: list[str], timeout: int = 90) -> dict[str, Any]:
    script = _root() / "scripts" / "browser_act.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_act.py missing"}
    cmd = [_python(), str(script), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(_root()))
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "browser action timed out"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1] or "{}")
    except Exception:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "browser worker failed")[-800:]}


def open_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    if not url:
        return {"ok": False, "error": "url is required"}
    cmd = ["--url", url, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def fill_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    fields = args.get("fields") or {}
    if not isinstance(fields, dict) or not fields:
        return {"ok": False, "error": "fields must be a non-empty object"}
    cmd = ["--url", url, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    for selector, value in fields.items():
        cmd += ["--fill", f"{selector}={value}"]
    if args.get("click"):
        cmd += ["--click", str(args["click"])]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def click_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    selector = str(args.get("selector") or "")
    if not selector:
        return {"ok": False, "error": "selector is required"}
    cmd = ["--url", url, "--click", selector, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)
