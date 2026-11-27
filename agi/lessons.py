"""Store and retrieve operational lessons for the main AGI."""
from __future__ import annotations

import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            failure TEXT,
            action TEXT,
            result TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def record(conn: sqlite3.Connection, failure: str, action: str, result: str = "",
           node_id: str = "") -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_lessons(node_id,failure,action,result,created_at) VALUES(?,?,?,?,?)",
        (node_id, failure, action, result, int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def search(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict]:
    ensure_schema(conn)
    words = [w for w in str(query or "").lower().split() if len(w) >= 2]
    rows = conn.execute(
        "SELECT id,node_id,failure,action,result,created_at FROM agi_lessons ORDER BY id DESC LIMIT 100"
    ).fetchall()
    scored = []
    for row in rows:
        text = " ".join(str(x or "") for x in row[1:]).lower()
        score = sum(text.count(w) for w in words)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    keys = ("id", "node_id", "failure", "action", "result", "created_at")
    return [dict(zip(keys, row)) for _, row in scored[:max(1, min(limit, 20))]]
