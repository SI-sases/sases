"""Client remote operations queue (allowlisted, no arbitrary shell)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any

from core.db import db_cursor

ALLOWED_ACTIONS = {
    "status",
    "update_client",
    "start_client",
    "stop_client",
    "restart_client",
    "install_wireguard",
    "import_tunnel",
    "capture_screen",
}

LEASE_SECONDS = 60
MAX_ATTEMPTS = 3


class ClientOpsError(Exception):
    pass


def _now() -> str:
    return datetime.utcnow().isoformat()


def enqueue(
    node_id: str,
    action: str,
    payload: dict | None = None,
    requested_by: int | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ClientOpsError(f"action not allowed: {action}")
    if not node_id:
        raise ClientOpsError("node_id required")
    if idempotency_key:
        with db_cursor() as cur:
            row = cur.execute(
                "SELECT id, status FROM client_operations WHERE idempotency_key=? "
                "ORDER BY id DESC LIMIT 1",
                (idempotency_key,),
            ).fetchone()
        if row:
            return {"id": row["id"], "node_id": node_id, "action": action, "status": row["status"]}
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO client_operations(node_id, action, payload, status, requested_by, "
            "created_at, attempts, idempotency_key) VALUES (?,?,?, 'pending', ?, ?, 0, ?)",
            (node_id, action, json.dumps(payload or {}, ensure_ascii=False), requested_by, _now(), idempotency_key),
        )
        op_id = cur.lastrowid
    return {"id": op_id, "node_id": node_id, "action": action, "status": "pending"}


def claim_next(node_id: str) -> dict[str, Any] | None:
    now = datetime.utcnow()
    now_text = now.isoformat()
    lease_until = (now + timedelta(seconds=LEASE_SECONDS)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE client_operations SET status='failed', finished_at=?, lease_until=NULL "
            "WHERE status='running' AND lease_until IS NOT NULL AND lease_until < ? "
            "AND attempts >= ?",
            (now_text, now_text, MAX_ATTEMPTS),
        )
        cur.execute(
            "UPDATE client_operations SET status='pending', lease_until=NULL "
            "WHERE status='running' AND lease_until IS NOT NULL AND lease_until < ? "
            "AND attempts < ?",
            (now_text, MAX_ATTEMPTS),
        )
        row = cur.execute(
            "SELECT * FROM client_operations WHERE node_id=? AND status='pending' "
            "ORDER BY id LIMIT 1",
            (node_id,),
        ).fetchone()
        if not row:
            return None
        changed = cur.execute(
            "UPDATE client_operations SET status='running', started_at=COALESCE(started_at, ?), "
            "attempts=attempts+1, lease_until=? WHERE id=? AND status='pending'",
            (now_text, lease_until, row["id"]),
        ).rowcount
        if not changed:
            return None
        updated = cur.execute("SELECT * FROM client_operations WHERE id=?", (row["id"],)).fetchone()
    item = dict(updated)
    try:
        item["payload"] = json.loads(item.get("payload") or "{}")
    except (TypeError, ValueError):
        item["payload"] = {}
    return item


def complete(op_id: int, status: str, result: Any = None) -> bool:
    if status not in ("done", "failed"):
        raise ClientOpsError("status must be done/failed")
    with db_cursor(commit=True) as cur:
        changed = cur.execute(
            "UPDATE client_operations SET status=?, finished_at=?, lease_until=NULL, result=? WHERE id=?",
            (status, _now(), json.dumps(result, ensure_ascii=False) if result is not None else None, op_id),
        ).rowcount
    return bool(changed)


def list_operations(node_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    sql = "SELECT * FROM client_operations"
    args: list[Any] = []
    if node_id:
        sql += " WHERE node_id=?"
        args.append(node_id)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(int(limit), 100)))
    with db_cursor() as cur:
        rows = cur.execute(sql, args).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        for key in ("payload", "result"):
            try:
                item[key] = json.loads(item[key]) if item.get(key) else None
            except (TypeError, ValueError):
                pass
        result.append(item)
    return result
