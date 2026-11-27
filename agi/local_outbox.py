"""Durable local result outbox for the local runtime."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


def _path() -> Path:
    p = Path("data") / "local_runtime.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_path()))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS outbox ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, status TEXT, result_json TEXT, "
        "created_at INTEGER, attempts INTEGER DEFAULT 0)"
    )
    return conn


def add(agent_id: str, status: str, result: dict) -> int:
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO outbox(agent_id,status,result_json,created_at) VALUES(?,?,?,?)",
        (agent_id, status, json.dumps(result, ensure_ascii=False), int(time.time())),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def pending(limit: int = 20) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT id,agent_id,status,result_json,attempts FROM outbox ORDER BY id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "agent_id": r[1], "status": r[2],
             "result": json.loads(r[3] or "{}"), "attempts": r[4]} for r in rows]


def remove(row_id: int) -> None:
    conn = _conn()
    conn.execute("DELETE FROM outbox WHERE id=?", (row_id,))
    conn.commit()
    conn.close()


def bump(row_id: int) -> None:
    conn = _conn()
    conn.execute("UPDATE outbox SET attempts=attempts+1 WHERE id=?", (row_id,))
    conn.commit()
    conn.close()
