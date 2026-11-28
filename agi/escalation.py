"""Escalations are the only path from main AGI to the human commander."""
from __future__ import annotations

import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT NOT NULL,
            evidence_json TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER
        )
        """
    )
    conn.commit()


def create(conn: sqlite3.Connection, node_id: str, reason: str, severity: str = "high",
           evidence: str = "{}") -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_escalations(node_id,reason,severity,evidence_json,status,created_at) "
        "VALUES(?,?,?,?, 'open', ?)",
        (node_id, reason, severity, evidence, int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def create_dedup(conn: sqlite3.Connection, node_id: str, reason: str,
                 severity: str = "high", evidence: str = "{}") -> int:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT id FROM agi_escalations WHERE status='open' AND node_id=? AND reason=? "
        "ORDER BY id DESC LIMIT 1",
        (node_id, reason),
    ).fetchone()
    if row:
        return int(row[0])
    return create(conn, node_id, reason, severity, evidence)


def resolve_node_reason(conn: sqlite3.Connection, node_id: str, reason: str) -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE agi_escalations SET status='resolved',resolved_at=? "
        "WHERE status='open' AND node_id=? AND reason=?",
        (int(time.time()), node_id, reason),
    )
    conn.commit()
    return int(cur.rowcount)


def list_open(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,node_id,reason,severity,status,created_at FROM agi_escalations "
        "WHERE status='open' ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)
    ).fetchall()
    keys = ("id", "node_id", "reason", "severity", "status", "created_at")
    return [dict(zip(keys, row)) for row in rows]


def resolve(conn: sqlite3.Connection, escalation_id: int) -> bool:
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE agi_escalations SET status='resolved',resolved_at=? WHERE id=? AND status='open'",
        (int(time.time()), escalation_id),
    )
    conn.commit()
    return cur.rowcount > 0
