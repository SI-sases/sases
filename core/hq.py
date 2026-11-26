"""Minimal HQ campaign / approval / task queue storage."""
from __future__ import annotations

import json
import time
from typing import Any

from core.db import db_cursor

MAX_ATTEMPTS = 3


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hq_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_approval',
                content_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                approved_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hq_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                region TEXT NOT NULL,
                action TEXT NOT NULL DEFAULT 'publish',
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending_approval',
                executor TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_until TEXT,
                result_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(campaign_id, platform)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_hq_tasks_status ON hq_tasks(status, region)")


def _row(row) -> dict:
    return {
        "id": row[0],
        "campaign_id": row[1],
        "platform": row[2],
        "region": row[3],
        "action": row[4],
        "payload": json.loads(row[5] or "{}"),
        "status": row[6],
        "executor": row[7],
        "attempts": row[8],
        "lease_until": row[9],
        "result": json.loads(row[10]) if row[10] else None,
        "error": row[11],
        "created_at": row[12],
        "updated_at": row[13],
    }


def create_campaign(name: str, region: str, platforms: list[str], content: dict[str, Any]) -> dict:
    ensure_schema()
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO hq_campaigns(name, region, status, content_json, created_at) VALUES (?,?,?,?,?)",
            (name, region, "pending_approval", json.dumps(content, ensure_ascii=False), now),
        )
        campaign_id = cur.lastrowid
        for platform in platforms:
            cur.execute(
                """
                INSERT INTO hq_tasks(campaign_id, platform, region, payload_json, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (campaign_id, platform, region, json.dumps(content, ensure_ascii=False), "pending_approval", now, now),
            )
    return get_campaign(campaign_id)


def get_campaign(campaign_id: int) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT id,name,region,status,content_json,created_at,approved_at FROM hq_campaigns WHERE id=?", (campaign_id,))
        row = cur.fetchone()
    if not row:
        raise KeyError("campaign not found")
    return {
        "id": row[0],
        "name": row[1],
        "region": row[2],
        "status": row[3],
        "content": json.loads(row[4] or "{}"),
        "created_at": row[5],
        "approved_at": row[6],
    }


def approve_campaign(campaign_id: int) -> dict:
    ensure_schema()
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE hq_campaigns SET status='approved', approved_at=? WHERE id=?", (now, campaign_id))
        cur.execute("UPDATE hq_tasks SET status='queued', updated_at=? WHERE campaign_id=? AND status='pending_approval'", (now, campaign_id))
    return get_campaign(campaign_id)


def list_campaigns(limit: int = 50) -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM hq_campaigns ORDER BY id DESC LIMIT ?", (limit,))
        ids = [r[0] for r in cur.fetchall()]
    return [get_campaign(i) for i in ids]


def list_tasks(status: str | None = None, limit: int = 100) -> list[dict]:
    ensure_schema()
    sql = (
        "SELECT id,campaign_id,platform,region,action,payload_json,status,executor,attempts,lease_until,"
        "result_json,error,created_at,updated_at FROM hq_tasks"
    )
    args: list[Any] = []
    if status:
        sql += " WHERE status=?"
        args.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with db_cursor() as cur:
        cur.execute(sql, args)
        return [_row(r) for r in cur.fetchall()]


def get_task(task_id: int) -> dict:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id,campaign_id,platform,region,action,payload_json,status,executor,attempts,lease_until,"
            "result_json,error,created_at,updated_at FROM hq_tasks WHERE id=?",
            (task_id,),
        )
        row = cur.fetchone()
    if not row:
        raise KeyError("task not found")
    return _row(row)


def claim_task(executor: str, platform: str | None = None, manual: bool | None = None) -> dict | None:
    ensure_schema()
    now = _now()
    with db_cursor(commit=True) as cur:
        sql = "SELECT id FROM hq_tasks WHERE status='queued'"
        args: list[Any] = []
        if platform:
            sql += " AND platform=?"
            args.append(platform)
        if manual is True:
            sql += " AND json_extract(payload_json, '$.manual') = 1"
        elif manual is False:
            sql += " AND COALESCE(json_extract(payload_json, '$.manual'), 0) = 0"
        sql += " ORDER BY id LIMIT 1"
        cur.execute(sql, args)
        row = cur.fetchone()
        if not row:
            return None
        task_id = row[0]
        cur.execute(
            "UPDATE hq_tasks SET status='running', executor=?, attempts=attempts+1, lease_until=?, updated_at=? WHERE id=?",
            (executor, "9999-12-31T23:59:59", now, task_id),
        )
    return get_task(task_id)


def complete_task(task_id: int, status: str, result: dict | None = None, error: str | None = None) -> dict:
    ensure_schema()
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT attempts FROM hq_tasks WHERE id=?", (task_id,)
        )
        row = cur.fetchone()
        if not row:
            raise KeyError("task not found")
        attempts = row[0]
        final_status = status
        if status == "failed" and attempts < MAX_ATTEMPTS:
            final_status = "queued"
        cur.execute(
            "UPDATE hq_tasks SET status=?, result_json=?, error=?, updated_at=?, lease_until=NULL WHERE id=?",
            (final_status, json.dumps(result, ensure_ascii=False) if result is not None else None, error, now, task_id),
        )
    return get_task(task_id)


def cancel_task(task_id: int, reason: str = "cancelled by operator") -> dict:
    """Close a task without automatic retry."""
    ensure_schema()
    now = _now()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE hq_tasks SET status='cancelled', error=?, updated_at=?, lease_until=NULL WHERE id=?",
            (reason, now, task_id),
        )
        if cur.rowcount == 0:
            raise KeyError("task not found")
    return get_task(task_id)
