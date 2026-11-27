"""Main AGI shadow runtime.

P0 intentionally does only observe/diagnose/record.  It never edits a running
SASES tree and never restarts a production service.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .protocol import Message, make_message
from .tools import ToolRegistry, build_default_registry


def _default_db() -> str:
    return os.environ.get("SASES_AGI_DB", str(Path("data") / "agi.db"))


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agi_nodes (
                node_id TEXT PRIMARY KEY,
                scope TEXT NOT NULL DEFAULT 'local',
                kind TEXT NOT NULL DEFAULT 'cloud',
                role TEXT NOT NULL DEFAULT 'main',
                version TEXT,
                health TEXT,
                last_seen INTEGER
            );
            CREATE TABLE IF NOT EXISTS agi_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                evidence_json TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agi_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playbook TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                trace_id TEXT,
                run_id TEXT,
                parent_run_id TEXT,
                started_at INTEGER NOT NULL,
                finished_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS agi_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                failure TEXT,
                action TEXT,
                result TEXT,
                created_at INTEGER NOT NULL
            );
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(agi_nodes)")}
        if "kind" not in cols:
            conn.execute("ALTER TABLE agi_nodes ADD COLUMN kind TEXT NOT NULL DEFAULT 'cloud'")
        conn.execute("UPDATE agi_nodes SET kind='client' WHERE scope='local'")
        run_cols = {row[1] for row in conn.execute("PRAGMA table_info(agi_runs)")}
        for name in ("trace_id", "run_id", "parent_run_id"):
            if name not in run_cols:
                conn.execute(f"ALTER TABLE agi_runs ADD COLUMN {name} TEXT")


class MainAGI:
    def __init__(self, base_url: str | None = None, db_path: str | None = None,
                 registry: ToolRegistry | None = None) -> None:
        self.base_url = (base_url or os.environ.get("SASES_AGI_TARGET", "http://127.0.0.1:8001")).rstrip("/")
        self.db_path = db_path or _default_db()
        self.registry = registry or build_default_registry()
        ensure_schema(self.db_path)

    def record_event(self, message: Message) -> None:
        with _connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO agi_events(node_id,type,severity,message,evidence_json,created_at) VALUES(?,?,?,?,?,?)",
                (message.node_id, message.type, message.severity,
                 str(message.payload.get("message") or ""),
                 json.dumps(message.evidence, ensure_ascii=False), message.created_at),
            )

    def _node_id(self, health: dict[str, Any], version: dict[str, Any]) -> str:
        for result in (health, version):
            data = result.get("data") or {}
            if isinstance(data, dict) and data.get("node_id"):
                return str(data["node_id"])
        return "local"

    def run_once(self) -> dict[str, Any]:
        started = int(time.time())
        trace_id = "trace_" + uuid.uuid4().hex[:16]
        trace_run_id = "run_" + uuid.uuid4().hex[:16]
        with _connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO agi_runs(playbook,status,trace_id,run_id,started_at) "
                "VALUES('health_check','running',?,?,?)",
                (trace_id, trace_run_id, started),
            )
            db_run_id = cur.lastrowid

        health = self.registry.invoke("main", "node.health", {"base_url": self.base_url})
        version = self.registry.invoke("main", "node.version", {"base_url": self.base_url})
        node_id = self._node_id(health, version)
        version_ok = bool(version.get("ok"))
        health_ok = bool(health.get("ok")) and bool((health.get("data") or {}).get("ok"))
        # Older nodes may not expose /health yet; a live /version is sufficient.
        healthy = health_ok or (health.get("status") == 404 and version_ok)
        if health_ok:
            message = "node healthy"
        elif health.get("status") == 404 and version_ok:
            message = "health endpoint missing; version is live"
        else:
            message = f"health check failed: {health.get('error') or health.get('status')}"
        severity = "info" if healthy else "critical"
        event = make_message(
            "agi.heartbeat" if healthy else "agi.event",
            node_id=node_id,
            severity=severity,
            payload={"message": message, "healthy": healthy},
            evidence={"health": health, "version": version},
            trace_id=trace_id,
            run_id=trace_run_id,
        )
        self.record_event(event)
        with _connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO agi_nodes(node_id,scope,kind,role,version,health,last_seen) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET scope=excluded.scope,kind=excluded.kind,"
                "version=excluded.version,health=excluded.health,last_seen=excluded.last_seen",
                (node_id, "local", "client", "main", (version.get("data") or {}).get("commit") or "",
                 "ok" if healthy else "error", event.created_at),
            )
            conn.execute(
                "UPDATE agi_runs SET status=?,result_json=?,finished_at=? WHERE id=?",
                ("ok" if healthy else "failed", json.dumps({"health": health, "version": version}, ensure_ascii=False), int(time.time()), db_run_id),
            )
        return {"ok": healthy, "node_id": node_id, "trace_id": trace_id, "run_id": trace_run_id,
                "event": event.to_dict(), "health": health, "version": version}

    def loop(self, interval: int = 30) -> None:
        while True:
            try:
                result = self.run_once()
                print(json.dumps(result, ensure_ascii=False))
            except Exception as exc:  # noqa: BLE001 - keep the supervisor alive
                print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            time.sleep(max(5, interval))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    agi = MainAGI(base_url=args.base_url, db_path=args.db)
    if args.once:
        print(json.dumps(agi.run_once(), ensure_ascii=False))
        return 0
    agi.loop(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
