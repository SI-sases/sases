"""User-facing notifications produced by the main AGI."""
from __future__ import annotations

import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            created_at INTEGER NOT NULL,
            read_at INTEGER
        )
        """
    )
    conn.commit()


def create(conn: sqlite3.Connection, message: str, conversation_id: int | None = None,
           severity: str = "info") -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_notifications(conversation_id,message,severity,created_at) "
        "VALUES(?,?,?,?)",
        (conversation_id, message, severity, int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_after(conn: sqlite3.Connection, after_id: int = 0,
               conversation_id: int | None = None, limit: int = 20) -> list[dict]:
    ensure_schema(conn)
    sql = "SELECT id,conversation_id,message,severity,created_at,read_at FROM agi_notifications WHERE id>?"
    params: list = [int(after_id)]
    if conversation_id is not None:
        sql += " AND (conversation_id IS NULL OR conversation_id=?)"
        params.append(int(conversation_id))
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(max(1, min(limit, 100)))
    rows = conn.execute(sql, params).fetchall()
    keys = ("id", "conversation_id", "message", "severity", "created_at", "read_at")
    return [dict(zip(keys, row)) for row in rows]


def mark_read(conn: sqlite3.Connection, ids: list[int]) -> None:
    if not ids:
        return
    ensure_schema(conn)
    marks = ",".join("?" for _ in ids)
    conn.execute(f"UPDATE agi_notifications SET read_at=? WHERE id IN ({marks})",
                 [int(time.time()), *[int(i) for i in ids]])
    conn.commit()
