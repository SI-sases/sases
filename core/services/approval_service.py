# core/services/approval_service.py
# -*- coding: utf-8 -*-
"""P2-1: 写/网络/命令操作的审批。"""
import os
from datetime import datetime

from ..db import db_cursor

WRITE_TOOLS = {"file_write", "smart_edit", "file_replace_range", "delete_block", "split_block", "git_ops"}
NETWORK_TOOLS = {"web_fetch", "api_call", "http_async", "ssh_exec"}


def require_enabled() -> bool:
    return os.getenv("SASES_REQUIRE_APPROVAL", "0") == "1"


def is_risky(step) -> bool:
    mid = str(step.get("module_id") or "")
    if mid.startswith("mcp."):
        return True
    if mid in WRITE_TOOLS or mid in NETWORK_TOOLS:
        return True
    if str(step.get("command") or "").strip():
        return True
    return False


def _tool_of(step) -> str:
    return str(step.get("module_id") or step.get("command") or "")[:120]


def is_approved(run_id, step_id, step) -> bool:
    if not run_id:
        return True
    tool = _tool_of(step)
    with db_cursor() as cur:
        cur.execute("SELECT decision, scope FROM approvals WHERE run_id=? AND step_id=?",
                    (run_id, str(step_id)))
        row = cur.fetchone()
        if row:
            decision = row["decision"] if isinstance(row, dict) else row[0]
            scope = row["scope"] if isinstance(row, dict) else row[1]
            if decision == "allow" and scope in ("once", "session"):
                return True
            if decision == "deny":
                return False
        cur.execute("SELECT 1 FROM approvals WHERE run_id=? AND tool_id=? AND scope='session' AND decision='allow' LIMIT 1",
                    (run_id, tool))
        return cur.fetchone() is not None


async def request_approval(run_id, step_id, step, conversation_id=None, user_id=None):
    tool = _tool_of(step)
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT decision FROM approvals WHERE run_id=? AND step_id=?", (run_id, str(step_id)))
        if cur.fetchone():
            return
        cur.execute(
            "INSERT INTO approvals (run_id, step_id, tool_id, decision, scope, created_at) "
            "VALUES (?,?,?,'pending','once',?)",
            (run_id, str(step_id), tool, datetime.utcnow().replace(microsecond=0).isoformat()),
        )
    try:
        from . import trace_service
        trace_service.emit(run_id, conversation_id, 1, "awaiting_approval",
                           content="等待确认：" + tool, tool=tool, status="pending")
    except Exception as e:
        print("[approval] trace 失败: " + str(e))
    try:
        from ..broadcast.ws_hub import broadcast_to_user
        if user_id:
            await broadcast_to_user(user_id, {
                "type": "approval_request",
                "run_id": run_id,
                "step_id": str(step_id),
                "tool": tool,
                "description": str(step.get("description") or "")[:200],
                "conversation_id": conversation_id,
            })
    except Exception as e:
        print("[approval] WS 推送失败: " + str(e))


def save_pending(run_id, step_id, tool_call_id, tool_id, args):
    import json
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO agent_pending_tools (run_id, step_id, tool_call_id, tool_id, args, created_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(run_id, step_id) DO UPDATE SET "
            "tool_call_id=excluded.tool_call_id, tool_id=excluded.tool_id, args=excluded.args, status='pending'",
            (int(run_id), str(step_id), tool_call_id, str(tool_id),
             json.dumps(args or {}, ensure_ascii=False), datetime.utcnow().replace(microsecond=0).isoformat()),
        )


def get_pending(run_id):
    import json
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM agent_pending_tools WHERE run_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (int(run_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["args"] = json.loads(d.get("args") or "{}")
        except Exception:
            d["args"] = {}
        return d


def clear_pending(pending_id):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE agent_pending_tools SET status='done' WHERE id=?", (int(pending_id),))


def decide(run_id, step_id, decision, scope="once"):
    decision = "allow" if decision in ("allow", "once", "session", "approve") else "deny"
    scope = "session" if scope == "session" else "once"
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE approvals SET decision=?, scope=?, decided_at=? WHERE run_id=? AND step_id=?",
                    (decision, scope, now, run_id, str(step_id)))
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO approvals (run_id, step_id, tool_id, decision, scope, created_at, decided_at) "
                "VALUES (?,?,?,?,?,?,?)", (run_id, str(step_id), "", decision, scope, now, now))
        if decision == "allow":
            cur.execute("UPDATE supervisor_runs SET status='running' WHERE id=? AND status='awaiting_approval'", (run_id,))
        else:
            cur.execute("UPDATE supervisor_runs SET status='cancelled', finished_at=? WHERE id=? AND status='awaiting_approval'", (now, run_id))
            cur.execute("UPDATE swarm_pending_tasks SET cancelled=1, status='cancelled' WHERE supervisor_run_id=?", (run_id,))
    return True
