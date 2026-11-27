"""Single-main leader lock per scope.

A local main AGI and a fleet main AGI may both exist, but only one owner may
hold a given scope at a time.  The lock is lease-based so a crashed main AGI
does not block the fleet forever.
"""
from __future__ import annotations

import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_leader (
            scope TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def status(conn: sqlite3.Connection, scope: str) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT scope,owner,expires_at,updated_at FROM agi_leader WHERE scope=?", (scope,)
    ).fetchone()
    if not row:
        return None
    now = int(time.time())
    return {"scope": row[0], "owner": row[1], "expires_at": row[2],
            "updated_at": row[3], "active": row[2] > now}


def acquire(conn: sqlite3.Connection, scope: str, owner: str, ttl: int = 60) -> bool:
    ensure_schema(conn)
    now = int(time.time())
    current = status(conn, scope)
    if current and current["active"] and current["owner"] != owner:
        return False
    conn.execute(
        "INSERT INTO agi_leader(scope,owner,expires_at,updated_at) VALUES(?,?,?,?) "
        "ON CONFLICT(scope) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at,"
        "updated_at=excluded.updated_at",
        (scope, owner, now + max(5, ttl), now),
    )
    conn.commit()
    return True


def renew(conn: sqlite3.Connection, scope: str, owner: str, ttl: int = 60) -> bool:
    ensure_schema(conn)
    now = int(time.time())
    row = conn.execute("SELECT owner,expires_at FROM agi_leader WHERE scope=?", (scope,)).fetchone()
    if not row or row[0] != owner or row[1] <= now:
        return False
    conn.execute("UPDATE agi_leader SET expires_at=?,updated_at=? WHERE scope=?",
                 (now + max(5, ttl), now, scope))
    conn.commit()
    return True


def release(conn: sqlite3.Connection, scope: str, owner: str) -> bool:
    ensure_schema(conn)
    cur = conn.execute("DELETE FROM agi_leader WHERE scope=? AND owner=?", (scope, owner))
    conn.commit()
    return cur.rowcount > 0
