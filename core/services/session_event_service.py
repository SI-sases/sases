"""Append-only session event log.

Additive: existing messages remain the source for chat rendering. New message
rows also produce events, so the log can be replayed or consumed by agents.
"""
from __future__ import annotations

from core.db import db_cursor


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(session_id, seq)
            )
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_messages_session_event
            AFTER INSERT ON messages
            BEGIN
                INSERT INTO session_events(session_id, seq, type, payload_json, created_at)
                VALUES (
                    NEW.conversation_id,
                    COALESCE((SELECT MAX(seq) FROM session_events WHERE session_id = NEW.conversation_id), 0) + 1,
                    'message.created',
                    json_object(
                        'message_id', NEW.id,
                        'sender', NEW.sender,
                        'sender_agent_id', NEW.sender_agent_id,
                        'msg_type', NEW.msg_type,
                        'content', NEW.content,
                        'attachments', NEW.attachments
                    ),
                    COALESCE(NEW.created_at, CURRENT_TIMESTAMP)
                );
            END
            """
        )


def list_events(session_id: int, after_seq: int = 0, limit: int = 200) -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id,session_id,seq,type,payload_json,created_at FROM session_events "
            "WHERE session_id=? AND seq>? ORDER BY seq LIMIT ?",
            (session_id, int(after_seq), max(1, min(int(limit), 1000))),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "session_id": r[1], "seq": r[2], "type": r[3],
         "payload": r[4], "created_at": r[5]}
        for r in rows
    ]


def latest_seq(session_id: int) -> int:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(seq),0) FROM session_events WHERE session_id=?", (session_id,))
        return int(cur.fetchone()[0] or 0)


def backfill(session_id: int) -> int:
    """Import existing messages once. Returns the number of inserted events."""
    import json
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT COUNT(*) FROM session_events WHERE session_id=?", (session_id,))
        if int(cur.fetchone()[0] or 0) > 0:
            return 0
        cur.execute(
            "SELECT id,sender,sender_agent_id,content,msg_type,attachments,created_at "
            "FROM messages WHERE conversation_id=? ORDER BY id",
            (session_id,),
        )
        rows = cur.fetchall()
        for seq, row in enumerate(rows, 1):
            payload = {
                "message_id": row[0], "sender": row[1], "sender_agent_id": row[2],
                "content": row[3], "msg_type": row[4], "attachments": row[5],
            }
            cur.execute(
                "INSERT OR IGNORE INTO session_events(session_id,seq,type,payload_json,created_at) "
                "VALUES (?,?,?,?,?)",
                (session_id, seq, "message.created", json.dumps(payload, ensure_ascii=False), row[6]),
            )
        return len(rows)
