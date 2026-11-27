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
            name TEXT,
            goal TEXT,
            kind TEXT NOT NULL DEFAULT 'subagent',
            progress TEXT,
            result_json TEXT,
            trace_id TEXT,
            context_json TEXT,
            model_profile TEXT,
            result_schema_json TEXT,
            parent_agent_id TEXT,
            depth INTEGER NOT NULL DEFAULT 0,
            last_seen INTEGER,
            lease_owner TEXT,
            lease_until INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agi_agent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            type TEXT NOT NULL,
            payload_json TEXT,
            created_at INTEGER NOT NULL,
            ack_at INTEGER
        );
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(agi_agents)")}
    for name, ddl in (
        ("name", "TEXT"), ("goal", "TEXT"), ("kind", "TEXT NOT NULL DEFAULT 'subagent'"),
        ("progress", "TEXT"), ("result_json", "TEXT"), ("trace_id", "TEXT"),
        ("last_seen", "INTEGER"), ("context_json", "TEXT"),
        ("model_profile", "TEXT"), ("result_schema_json", "TEXT"),
        ("parent_agent_id", "TEXT"), ("depth", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE agi_agents ADD COLUMN {name} {ddl}")
    conn.commit()


def spawn(conn: sqlite3.Connection, node_id: str, task: dict, role: str = "sub",
          parent_run_id: str = "", ttl: int = 300, name: str = "", goal: str = "",
          kind: str = "subagent", trace_id: str = "", status: str = "active",
          context: dict | None = None, model_profile: str = "",
          result_schema: dict | None = None, parent_agent_id: str = "", depth: int = 0) -> str:
    ensure_schema(conn)
    now = int(time.time())
    agent_id = "agent_" + secrets.token_hex(8)
    conn.execute(
        "INSERT INTO agi_agents(agent_id,parent_run_id,node_id,role,status,task_json,name,goal,"
        "kind,progress,trace_id,context_json,model_profile,result_schema_json,parent_agent_id,"
        "depth,last_seen,lease_until,created_at,updated_at) "
        "VALUES(?,?,?,?, ?,?,?,?,?, '', ?,?,?,?,?,?,?,?,?,?)",
        (agent_id, parent_run_id, node_id, role, status, json.dumps(task, ensure_ascii=False),
         name or goal or "subagent", goal or name or "", kind, trace_id,
         json.dumps(context or {}, ensure_ascii=False), model_profile,
         json.dumps(result_schema or {}, ensure_ascii=False), parent_agent_id, int(depth),
         now, now + max(10, ttl), now, now),
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


def finish(conn: sqlite3.Connection, agent_id: str, status: str = "done",
           result: dict | None = None) -> bool:
    ensure_schema(conn)
    if status not in {"done", "failed", "cancelled", "needs_approval"}:
        raise ValueError("invalid final status")
    cur = conn.execute(
        "UPDATE agi_agents SET status=?,result_json=COALESCE(?,result_json),lease_until=NULL,"
        "updated_at=? WHERE agent_id=?",
        (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
         int(time.time()), agent_id),
    )
    conn.commit()
    return cur.rowcount > 0


def claim_next(conn: sqlite3.Connection, owner: str, ttl: int = 300) -> str | None:
    ensure_schema(conn)
    now = int(time.time())
    row = conn.execute(
        "SELECT agent_id FROM agi_agents WHERE status='queued' ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    agent_id = row[0]
    cur = conn.execute(
        "UPDATE agi_agents SET status='active',lease_owner=?,lease_until=?,last_seen=?,updated_at=? "
        "WHERE agent_id=? AND status='queued'",
        (owner, now + max(10, ttl), now, now, agent_id),
    )
    conn.commit()
    return agent_id if cur.rowcount else None


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


def get_agent(conn: sqlite3.Connection, agent_id: str) -> dict | None:
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM agi_agents WHERE agent_id=?", (agent_id,)).fetchone()
    return dict(row) if row else None


def set_progress(conn: sqlite3.Connection, agent_id: str, progress: str) -> bool:
    ensure_schema(conn)
    now = int(time.time())
    cur = conn.execute(
        "UPDATE agi_agents SET progress=?,last_seen=?,updated_at=? WHERE agent_id=?",
        (progress, now, now, agent_id),
    )
    conn.commit()
    return cur.rowcount > 0


def add_message(conn: sqlite3.Connection, agent_id: str, direction: str, kind: str,
                payload: dict | None = None) -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_agent_messages(agent_id,direction,type,payload_json,created_at) "
        "VALUES(?,?,?,?,?)",
        (agent_id, direction, kind, json.dumps(payload or {}, ensure_ascii=False),
         int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def messages(conn: sqlite3.Connection, agent_id: str, limit: int = 100) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM agi_agent_messages WHERE agent_id=? ORDER BY id ASC LIMIT ?",
        (agent_id, max(1, min(limit, 500))),
    ).fetchall()
    return [dict(row) for row in rows]


def unread_messages(conn: sqlite3.Connection, agent_id: str) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM agi_agent_messages WHERE agent_id=? AND direction='parent_to_child' "
        "AND ack_at IS NULL ORDER BY id ASC",
        (agent_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def ack_message(conn: sqlite3.Connection, message_id: int) -> None:
    ensure_schema(conn)
    conn.execute("UPDATE agi_agent_messages SET ack_at=? WHERE id=?",
                 (int(time.time()), message_id))
    conn.commit()


def cancel(conn: sqlite3.Connection, agent_id: str) -> bool:
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE agi_agents SET status='cancelled',lease_until=NULL,updated_at=? "
        "WHERE agent_id=? AND status IN ('active','queued')",
        (int(time.time()), agent_id),
    )
    conn.commit()
    return cur.rowcount > 0
