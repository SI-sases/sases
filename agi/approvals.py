"""Human approval queue for AGI actions that must not auto-run."""
from __future__ import annotations

import json
import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool TEXT NOT NULL,
            args_json TEXT,
            description TEXT,
            risk TEXT NOT NULL DEFAULT 'high',
            trace_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            decided_by TEXT,
            created_at INTEGER NOT NULL,
            decided_at INTEGER
        )
        """
    )
    conn.commit()


def create(conn: sqlite3.Connection, tool: str, args: dict | None = None,
           description: str = "", risk: str = "high", trace_id: str = "") -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_approvals(tool,args_json,description,risk,trace_id,status,created_at) "
        "VALUES(?,?,?,?,?, 'pending', ?)",
        (tool, json.dumps(args or {}, ensure_ascii=False), description, risk, trace_id,
         int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_pending(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    return list_by_status(conn, "pending", limit)


def list_by_status(conn: sqlite3.Connection, status: str, limit: int = 50) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,tool,args_json,description,risk,trace_id,status,created_at "
        "FROM agi_approvals WHERE status=? ORDER BY id ASC LIMIT ?",
        (status, max(1, min(limit, 200))),
    ).fetchall()
    keys = ("id", "tool", "args_json", "description", "risk", "trace_id", "status", "created_at")
    return [dict(zip(keys, row)) for row in rows]


def mark_executed(conn: sqlite3.Connection, approval_id: int) -> bool:
    ensure_schema(conn)
    cur = conn.execute("UPDATE agi_approvals SET status='executed' WHERE id=? AND status='allow'",
                       (approval_id,))
    conn.commit()
    return cur.rowcount > 0


def decide(conn: sqlite3.Connection, approval_id: int, decision: str,
           decided_by: str = "commander") -> bool:
    ensure_schema(conn)
    if decision not in {"allow", "deny"}:
        raise ValueError("decision must be allow or deny")
    cur = conn.execute(
        "UPDATE agi_approvals SET status=?,decided_by=?,decided_at=? "
        "WHERE id=? AND status='pending'",
        (decision, decided_by, int(time.time()), approval_id),
    )
    conn.commit()
    return cur.rowcount > 0
