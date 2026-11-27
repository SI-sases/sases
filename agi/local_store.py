"""Persistent local session state for task-level recovery."""
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
        "CREATE TABLE IF NOT EXISTS local_sessions ("
        "agent_id TEXT PRIMARY KEY, goal TEXT, steps_json TEXT, current_step INTEGER DEFAULT 0, "
        "status TEXT, started_at INTEGER, updated_at INTEGER)"
    )
    return conn


def start(agent_id: str, goal: str, steps: list[dict]) -> int:
    conn = _conn()
    row = conn.execute("SELECT current_step FROM local_sessions WHERE agent_id=?", (agent_id,)).fetchone()
    if row:
        conn.close()
        return int(row[0])
    now = int(time.time())
    conn.execute(
        "INSERT INTO local_sessions(agent_id,goal,steps_json,current_step,status,started_at,updated_at) "
        "VALUES(?,?,?,0,'running',?,?)",
        (agent_id, goal, json.dumps(steps, ensure_ascii=False), now, now),
    )
    conn.commit()
    conn.close()
    return 0


def step(agent_id: str, current_step: int) -> None:
    conn = _conn()
    conn.execute("UPDATE local_sessions SET current_step=?,updated_at=? WHERE agent_id=?",
                 (int(current_step), int(time.time()), agent_id))
    conn.commit()
    conn.close()


def finish(agent_id: str, status: str = "done") -> None:
    conn = _conn()
    conn.execute("UPDATE local_sessions SET status=?,updated_at=? WHERE agent_id=?",
                 (status, int(time.time()), agent_id))
    if status in ("done", "failed", "cancelled"):
        conn.execute("DELETE FROM local_sessions WHERE agent_id=?", (agent_id,))
    conn.commit()
    conn.close()
