"""User memory store (global and per-session)."""
from __future__ import annotations

import time

from core.db import db_cursor

SCOPES = {"global", "session"}


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                scope TEXT NOT NULL DEFAULT 'global',
                session_id INTEGER NOT NULL DEFAULT 0,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, scope, session_id, key)
            )
            """
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def list_memory(user_id: int, scope: str = "global", session_id: int | None = None) -> list[dict]:
    ensure_schema()
    if scope not in SCOPES:
        raise ValueError("invalid scope")
    with db_cursor() as cur:
        if scope == "session":
            cur.execute(
                "SELECT id,scope,session_id,key,value,created_at,updated_at FROM memory_entries "
                "WHERE user_id=? AND scope='session' AND session_id=? ORDER BY updated_at DESC",
                (user_id, session_id),
            )
        else:
            cur.execute(
                "SELECT id,scope,session_id,key,value,created_at,updated_at FROM memory_entries "
                "WHERE user_id=? AND scope='global' AND session_id=0 ORDER BY updated_at DESC",
                (user_id,),
            )
        rows = cur.fetchall()
    return [
        {"id": r[0], "scope": r[1], "session_id": r[2], "key": r[3],
         "value": r[4], "created_at": r[5], "updated_at": r[6]}
        for r in rows
    ]


def set_memory(user_id: int, key: str, value: str, scope: str = "global",
               session_id: int | None = None) -> dict:
    ensure_schema()
    if scope not in SCOPES:
        raise ValueError("invalid scope")
    if scope == "session" and not session_id:
        raise ValueError("session_id required")
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO memory_entries(user_id,scope,session_id,key,value,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(user_id,scope,session_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (user_id, scope, session_id if scope == "session" else 0, key, value, now, now),
        )
        cur.execute(
            "SELECT id,scope,session_id,key,value,created_at,updated_at FROM memory_entries "
            "WHERE user_id=? AND scope=? AND session_id=? AND key=?",
            (user_id, scope, session_id if scope == "session" else 0, key),
        )
        r = cur.fetchone()
    return {"id": r[0], "scope": r[1], "session_id": r[2], "key": r[3],
            "value": r[4], "created_at": r[5], "updated_at": r[6]}


def delete_memory(user_id: int, memory_id: int) -> bool:
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM memory_entries WHERE id=? AND user_id=?", (memory_id, user_id))
        return cur.rowcount > 0


def summarize_work_logs(user_id: int, hours: int = 6) -> int:
    """Store a bounded summary of recent work logs as global memory."""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(hours=max(1, hours))).isoformat()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id,agent_id,command,output,status,created_at FROM work_logs "
            "WHERE user_id=? AND created_at>=? ORDER BY id DESC LIMIT 50",
            (user_id, cutoff),
        )
        rows = cur.fetchall()
    if not rows:
        return 0
    lines = []
    for r in rows[:20]:
        task = str(r["command"] or r["agent_id"] or "")[:120]
        status = str(r["status"] or "")
        summary = str(r["output"] or "")[:160]
        lines.append(f"- {task} [{status}] {summary}".strip())
    value = "Recent work logs:\n" + "\n".join(lines)
    return int(set_memory(user_id, "work_summary", value)["id"])


def backfill_embeddings(limit: int = 200) -> int:
    """Embedding backfill is optional; FTS/keyword search is the active path."""
    return 0


def prompt_for(user_id: int, session_id: int | None = None, max_chars: int = 2000) -> str:
    """Bounded prompt block for global and current-session memory."""
    items = list_memory(user_id, "global")
    if session_id:
        items += list_memory(user_id, "session", session_id)
    if not items:
        return ""
    lines = ["## Saved memory", "Use only when relevant; do not repeat it verbatim."]
    used = 0
    for item in items[:30]:
        line = "- " + str(item["key"]) + ": " + str(item["value"]).replace("\n", " ")[:300]
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines) if len(lines) > 2 else ""
