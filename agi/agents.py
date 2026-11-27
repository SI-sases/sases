"""Agent tree and leases for main/sub AGI work."""
from __future__ import annotations

import json
import secrets
import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agi_agents (
            agent_id TEXT PRIMARY KEY,
            parent_run_id TEXT,
            node_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'sub',
            status TEXT NOT NULL DEFAULT 'active',
            task_json TEXT,
            lease_owner TEXT,
            lease_until INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def spawn(conn: sqlite3.Connection, node_id: str, task: dict, role: str = "sub",
          parent_run_id: str = "", ttl: int = 300) -> str:
    ensure_schema(conn)
    now = int(time.time())
    agent_id = "agent_" + secrets.token_hex(8)
    conn.execute(
        "INSERT INTO agi_agents(agent_id,parent_run_id,node_id,role,status,task_json,lease_until,"
        "created_at,updated_at) VALUES(?,?,?,?, 'active', ?,?,?,?)",
        (agent_id, parent_run_id, node_id, role, json.dumps(task, ensure_ascii=False),
         now + max(10, ttl), now, now),
    )
    conn.commit()
    return agent_id


def lease(conn: sqlite3.Connection, agent_id: str, owner: str, ttl: int = 60) -> bool:
    ensure_schema(conn)
    now = int(time.time())
    row = conn.execute("SELECT status,lease_owner,lease_until FROM agi_agents WHERE agent_id=?",
                       (agent_id,)).fetchone()
    if not row or row[0] != "active":
        return False
    if row[2] and row[2] > now and row[1] not in (None, owner):
        return False
    conn.execute("UPDATE agi_agents SET lease_owner=?,lease_until=?,updated_at=? WHERE agent_id=?",
                 (owner, now + max(5, ttl), now, agent_id))
    conn.commit()
    return True


def heartbeat(conn: sqlite3.Connection, agent_id: str, owner: str, ttl: int = 60) -> bool:
    ensure_schema(conn)
    now = int(time.time())
    cur = conn.execute(
        "UPDATE agi_agents SET lease_until=?,updated_at=? WHERE agent_id=? AND status='active' "
        "AND lease_owner=?",
        (now + max(5, ttl), now, agent_id, owner),
    )
    conn.commit()
    return cur.rowcount > 0


def finish(conn: sqlite3.Connection, agent_id: str, status: str = "done") -> bool:
    ensure_schema(conn)
    if status not in {"done", "failed", "cancelled"}:
        raise ValueError("invalid final status")
    cur = conn.execute("UPDATE agi_agents SET status=?,lease_until=NULL,updated_at=? WHERE agent_id=?",
                       (status, int(time.time()), agent_id))
    conn.commit()
    return cur.rowcount > 0


def list_agents(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    ensure_schema(conn)
    sql = "SELECT * FROM agi_agents"
    params: tuple = ()
    if status:
        sql += " WHERE status=?"
        params = (status,)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
