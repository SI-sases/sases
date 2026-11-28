"""Detect failed or stuck local/cloud agents and escalate to the commander."""
from __future__ import annotations

import json
import sqlite3
import time

from . import escalation, platform_quota

PLATFORM_LIMIT = ("upload limit", "quota", "daily limit", "上传上限", "次数限制", "limit reached")
LOGIN = ("login", "logged out", "unauthorized", "登录", "掉线")
PERMISSION = ("permission", "forbidden", "403", "权限", "禁止")
TIMEOUT = ("timeout", "timed out", "超时")


def classify(error: str) -> str:
    low = str(error or "").lower()
    if any(w in low for w in PLATFORM_LIMIT):
        return "platform_limit"
    if any(w in low for w in LOGIN):
        return "login"
    if any(w in low for w in PERMISSION):
        return "permission"
    if any(w in low for w in TIMEOUT):
        return "timeout"
    return "execution"


def _already_open(conn: sqlite3.Connection, agent_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM agi_escalations WHERE status='open' AND reason LIKE ? LIMIT 1",
        (f"%{agent_id}%",),
    ).fetchone()
    return bool(row)


def scan(conn: sqlite3.Connection, stale_seconds: int = 600,
         recent_seconds: int = 3600) -> list[dict]:
    escalation.ensure_schema(conn)
    created = []
    try:
        agents = conn.execute("SELECT * FROM agi_agents").fetchall()
    except sqlite3.OperationalError:
        return created
    cols = [r[1] for r in conn.execute("PRAGMA table_info(agi_agents)")]
    for row in agents:
        agent = dict(zip(cols, row))
        agent_id = str(agent.get("agent_id") or "")
        if not agent_id or _already_open(conn, agent_id):
            continue
        status = str(agent.get("status") or "")
        reason = ""
        severity = "high"
        if status == "failed":
            updated = int(agent.get("updated_at") or 0)
            if updated and time.time() - updated > recent_seconds:
                continue
            err = str(agent.get("result_json") or "")[:500]
            kind = classify(err)
            reason = f"子智能体失败 [{kind}] `{agent.get('name') or agent_id}` ({agent_id}): {err}"
            if kind == "platform_limit":
                platform = next((p for p in ("youtube", "douyin", "bilibili", "reddit")
                                 if p in str(agent.get("name") or "").lower() or p in err.lower()), "unknown")
                platform_quota.record(conn, platform, err[:300])
            severity = "critical" if kind in ("platform_limit", "login", "permission") else "high"
        elif status == "needs_approval":
            reason = f"子智能体等待审批 `{agent.get('name') or agent_id}` ({agent_id})"
            severity = "medium"
        elif status == "active":
            last = int(agent.get("last_seen") or agent.get("updated_at") or 0)
            if last and time.time() - last > stale_seconds:
                reason = f"子智能体可能卡死 `{agent.get('name') or agent_id}` ({agent_id})"
                severity = "high"
        if reason:
            eid = escalation.create(conn, str(agent.get("node_id") or "local"), reason,
                                    severity, json.dumps({"agent_id": agent_id}, ensure_ascii=False))
            created.append({"id": eid, "agent_id": agent_id, "reason": reason, "severity": severity})
    return created
