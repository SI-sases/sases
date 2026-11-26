#!/usr/bin/env python3
"""Small node health check for cron/Task Scheduler."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request

BASE = os.environ.get("SASES_HEALTH_URL", "http://127.0.0.1:8001").rstrip("/")
DB = os.environ.get("SASES_DB_PATH", "users.db")
OUT = os.environ.get("SASES_HEALTH_OUT", "data/health.json")


def get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as r:
            return r.status, r.read(500).decode("utf-8", "replace")
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def main() -> int:
    version_status, version_body = get("/version")
    health_status, _ = get("/health")
    db = {"path": DB, "exists": os.path.exists(DB)}
    if db["exists"]:
        try:
            conn = sqlite3.connect(DB)
            db["integrity"] = conn.execute("PRAGMA quick_check").fetchone()[0]
            db["tables"] = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            conn.close()
        except Exception as exc:
            db["error"] = str(exc)
    disk = shutil.disk_usage(os.path.dirname(os.path.abspath(DB)) or ".")
    payload = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base": BASE,
        "version_status": version_status,
        "version": version_body,
        "health_status": health_status,
        "db": db,
        "disk_free_gb": round(disk.free / 1024 ** 3, 2),
        "ok": version_status == 200 and db.get("integrity") == "ok" and disk.free > 1024 ** 3,
    }
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
