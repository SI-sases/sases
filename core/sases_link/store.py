"""Durable peer-to-peer message store for SASES Link."""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from core.db import db_cursor

_ready = False


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def ensure_schema() -> None:
    global _ready
    if _ready:
        return
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS link_peers (
                peer_id TEXT PRIMARY KEY,
                node_id TEXT,
                base_url TEXT,
                capabilities TEXT,
                status TEXT DEFAULT 'unknown',
                last_seen TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS link_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT UNIQUE NOT NULL,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT,
                error TEXT,
                idempotency_key TEXT,
                created_at TEXT,
                updated_at TEXT,
                expires_at TEXT
            )
            """
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_link_msg_idem ON link_messages(sender, idempotency_key)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS link_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT,
                msg_id TEXT,
                result TEXT,
                created_at TEXT
            )
            """
        )
    _ready = True


def hello(peer_id: str, node_id: str, base_url: str, capabilities: list[str]) -> dict:
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT peer_id FROM link_peers WHERE peer_id=?", (peer_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE link_peers SET node_id=?, base_url=?, capabilities=?, status='online', last_seen=? WHERE peer_id=?",
                (node_id, base_url, json.dumps(capabilities, ensure_ascii=False), _now(), peer_id),
            )
        else:
            cur.execute(
                "INSERT INTO link_peers(peer_id,node_id,base_url,capabilities,status,last_seen,created_at) VALUES (?,?,?,?,?,?,?)",
                (peer_id, node_id, base_url, json.dumps(capabilities, ensure_ascii=False), "online", _now(), _now()),
            )
    return {"peer_id": peer_id, "status": "online"}


def list_peers() -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM link_peers ORDER BY last_seen DESC")
        return [dict(row) for row in cur.fetchall()]


def enqueue(
    sender: str,
    receiver: str,
    action: str,
    payload: dict | None = None,
    idempotency_key: str | None = None,
    timeout_sec: int = 300,
) -> dict:
    ensure_schema()
    if idempotency_key:
        with db_cursor() as cur:
            cur.execute(
                "SELECT msg_id,status FROM link_messages WHERE sender=? AND idempotency_key=?",
                (sender, idempotency_key),
            )
            row = cur.fetchone()
            if row:
                return {"msg_id": row["msg_id"], "status": row["status"], "duplicate": True}
    msg_id = "msg_" + uuid.uuid4().hex[:20]
    expires = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + timeout_sec))
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO link_messages(msg_id,sender,receiver,action,payload,status,idempotency_key,created_at,updated_at,expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (msg_id, sender, receiver, action, json.dumps(payload or {}, ensure_ascii=False),
             "pending", idempotency_key, _now(), _now(), expires),
        )
    audit(sender, "send", msg_id, action)
    return {"msg_id": msg_id, "status": "pending"}


def inbox(receiver: str, limit: int = 50) -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM link_messages WHERE receiver=? AND status='pending' ORDER BY id ASC LIMIT ?",
            (receiver, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def ack(msg_id: str, status: str, result: Any = None, error: str | None = None, actor: str = "unknown") -> dict:
    ensure_schema()
    if status not in ("accepted", "running", "done", "failed", "cancelled"):
        raise ValueError("invalid status")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE link_messages SET status=?, result=?, error=?, updated_at=? WHERE msg_id=?",
            (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
             error, _now(), msg_id),
        )
        if cur.rowcount == 0:
            raise KeyError(msg_id)
    audit(actor, "ack:" + status, msg_id, error or "")
    return {"msg_id": msg_id, "status": status}


def list_messages(peer_id: str | None = None, limit: int = 50) -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        if peer_id:
            cur.execute(
                "SELECT * FROM link_messages WHERE sender=? OR receiver=? ORDER BY id DESC LIMIT ?",
                (peer_id, peer_id, limit),
            )
        else:
            cur.execute("SELECT * FROM link_messages ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]


def audit(actor: str, action: str, msg_id: str = "", result: str = "") -> None:
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO link_audit(actor,action,msg_id,result,created_at) VALUES (?,?,?,?,?)",
            (actor, action, msg_id, result, _now()),
        )


def list_audit(limit: int = 100) -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM link_audit ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]
