"""Durable per-agent tool trace for main-AGI supervision."""
from __future__ import annotations

import json
import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            tool TEXT,
            args_json TEXT,
            result_json TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def add(conn: sqlite3.Connection, agent_id: str, seq: int, event_type: str,
        tool: str = "", args: dict | None = None, result: dict | None = None) -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_agent_events(agent_id,seq,event_type,tool,args_json,result_json,created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (agent_id, int(seq), event_type, tool,
         json.dumps(args or {}, ensure_ascii=False),
         json.dumps(result or {}, ensure_ascii=False), int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_for(conn: sqlite3.Connection, agent_id: str, limit: int = 200) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,seq,event_type,tool,args_json,result_json,created_at "
        "FROM agi_agent_events WHERE agent_id=? ORDER BY seq ASC,id ASC LIMIT ?",
        (agent_id, max(1, min(limit, 500))),
    ).fetchall()
    keys = ("id", "seq", "event_type", "tool", "args_json", "result_json", "created_at")
    return [dict(zip(keys, row)) for row in rows]
