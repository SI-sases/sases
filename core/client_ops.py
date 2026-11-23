"""Client remote operations queue (allowlisted, no arbitrary shell)."""
from __future__ import annotations

import json
import time
from typing import Any

from core.db import db_cursor

ALLOWED_ACTIONS = {
    "status",
    "update_client",
    "start_client",
    "stop_client",
    "install_wireguard",
    "import_tunnel",
    "capture_screen",
}


class ClientOpsError(Exception):
    pass


def enqueue(node_id: str, action: str, payload: dict | None = None, requested_by: int | None = None) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ClientOpsError(f"action not allowed: {action}")
    if not node_id:
        raise ClientOpsError("node_id required")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO client_operations(node_id, action, payload, status, requested_by, created_at) "
            "VALUES (?,?,?, 'pending', ?, ?)",
            (node_id, action, json.dumps(payload or {}, ensure_ascii=False), requested_by, now),
        )
        op_id = cur.lastrowid
    return {"id": op_id, "node_id": node_id, "action": action, "status": "pending"}


def claim_next(node_id: str) -> dict[str, Any] | None:
    with db_cursor(commit=True) as cur:
        row = cur.execute(
            "SELECT * FROM client_operations WHERE node_id=? AND status='pending' "
            "ORDER BY id LIMIT 1",
            (node_id,),
        ).fetchone()
        if not row:
            return None
        changed = cur.execute(
            "UPDATE client_operations SET status='running', started_at=? "
            "WHERE id=? AND status='pending'",
            (time.strftime("%Y-%m-%dT%H:%M:%S"), row["id"]),
        ).rowcount
        if not changed:
            return None
    item = dict(row)
    item["status"] = "running"
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
            "UPDATE client_operations SET status=?, finished_at=?, result=? WHERE id=?",
            (status, time.strftime("%Y-%m-%dT%H:%M:%S"),
             json.dumps(result, ensure_ascii=False) if result is not None else None, op_id),
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
