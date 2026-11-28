"""Platform quota state (upload limits, daily caps)."""
from __future__ import annotations

import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_platform_quota (
            platform TEXT PRIMARY KEY,
            exhausted_until INTEGER,
            reason TEXT,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def record(conn: sqlite3.Connection, platform: str, reason: str = "",
           hours: int = 24) -> None:
    ensure_schema(conn)
    now = int(time.time())
    conn.execute(
        "INSERT INTO agi_platform_quota(platform,exhausted_until,reason,updated_at) "
        "VALUES(?,?,?,?) ON CONFLICT(platform) DO UPDATE SET "
        "exhausted_until=excluded.exhausted_until,reason=excluded.reason,updated_at=excluded.updated_at",
        (platform, now + hours * 3600, reason, now),
    )
    conn.commit()


def list_expired(conn: sqlite3.Connection) -> list[dict]:
    ensure_schema(conn)
    now = int(time.time())
    rows = conn.execute(
        "SELECT platform,exhausted_until,reason FROM agi_platform_quota "
        "WHERE exhausted_until<=? ORDER BY exhausted_until ASC",
        (now,),
    ).fetchall()
    return [{"platform": r[0], "exhausted_until": r[1], "reason": r[2]} for r in rows]


def remove(conn: sqlite3.Connection, platform: str) -> None:
    ensure_schema(conn)
    conn.execute("DELETE FROM agi_platform_quota WHERE platform=?", (platform,))
    conn.commit()


def list_active(conn: sqlite3.Connection) -> list[dict]:
    ensure_schema(conn)
    now = int(time.time())
    rows = conn.execute(
        "SELECT platform,exhausted_until,reason FROM agi_platform_quota WHERE exhausted_until>? "
        "ORDER BY exhausted_until ASC",
        (now,),
    ).fetchall()
    return [{"platform": r[0], "exhausted_until": r[1], "reason": r[2]} for r in rows]
