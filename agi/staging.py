"""Run a candidate SASES package on an alternate port and verify it.

This is the only P3 executor: it never touches the production port or tree.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def _python(root: Path) -> Path:
    for candidate in (root / "python-embed" / "python.exe", root / "venv312" / "Scripts" / "python.exe"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no python-embed/venv python in candidate root")


def _get(url: str) -> tuple[bool, dict]:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return True, json.loads(resp.read().decode("utf-8") or "{}")
    except Exception:
        return False, {}


def verify(root: str, port: int = 8030, timeout: int = 45) -> dict:
    root_path = Path(root).resolve()
    python = _python(root_path)
    if not (root_path / "scripts" / "run_forever.py").exists():
        raise FileNotFoundError("candidate is missing scripts/run_forever.py")
    env = os.environ.copy()
    env.update({
        "SASES_PORT": str(port),
        "SASES_DISABLE_LOCAL_EMBEDDING": "1",
        "EMBEDDING_MODE": "api",
    })
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
    log = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
    proc = subprocess.Popen(
        [str(python), "scripts/run_forever.py"],
        cwd=str(root_path), env=env, stdout=log, stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout
    health_ok = False
    version_ok = False
    version: dict = {}
    health: dict = {}
    try:
        while time.time() < deadline:
            health_ok, health = _get(base + "/health")
            version_ok, version = _get(base + "/version")
            if health_ok or version_ok:
                break
            time.sleep(2)
    finally:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, text=True)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log.close()
    return {
        "ok": bool(health_ok or version_ok),
        "root": str(root_path),
        "port": port,
        "health": health,
        "version": version,
        "log": log.name,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--port", type=int, default=8030)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.port), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
