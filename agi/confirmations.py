"""Pending user confirmations for conflicting instructions."""
from __future__ import annotations

import json
import sqlite3
import time


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agi_confirmations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            goal TEXT NOT NULL,
            history_json TEXT,
            options_json TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            choice TEXT,
            created_at INTEGER NOT NULL,
            resolved_at INTEGER
        )
        """
    )
    conn.commit()


def create(conn: sqlite3.Connection, conversation_id: int, goal: str,
           history: list[str], options: list[str]) -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agi_confirmations(conversation_id,goal,history_json,options_json,status,created_at) "
        "VALUES(?,?,?,?, 'pending', ?)",
        (int(conversation_id), goal, json.dumps(history, ensure_ascii=False),
         json.dumps(options, ensure_ascii=False), int(time.time())),
    )
    conn.commit()
    return int(cur.lastrowid)


def pending(conn: sqlite3.Connection, conversation_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT id,conversation_id,goal,history_json,options_json,status,choice FROM agi_confirmations "
        "WHERE conversation_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        (int(conversation_id),),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "conversation_id": row[1], "goal": row[2],
            "history": json.loads(row[3] or "[]"), "options": json.loads(row[4] or "[]"),
            "status": row[5], "choice": row[6]}


def resolve(conn: sqlite3.Connection, confirmation_id: int, choice: str) -> bool:
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE agi_confirmations SET status='resolved',choice=?,resolved_at=? "
        "WHERE id=? AND status='pending'",
        (choice, int(time.time()), int(confirmation_id)),
    )
    conn.commit()
    return cur.rowcount > 0
