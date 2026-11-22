# core/services/todo_service.py
# -*- coding: utf-8 -*-
"""DSH 风格 todo_write：整表替换、单 in_progress、持久化到 agent_todos。"""
import json
from datetime import datetime

from ..db import db_cursor

VALID = ("pending", "in_progress", "completed")


def _key(run_id):
    try:
        return int(run_id or 0)
    except Exception:
        return 0


def write(user_id, conversation_id, run_id, todos):
    if not isinstance(todos, list):
        return {"success": False, "error": "todos 必须是数组"}
    clean = []
    seen = set()
    in_progress = 0
    for it in todos:
        if not isinstance(it, dict):
            return {"success": False, "error": "todo 项必须是对象"}
        content = str(it.get("content") or "").strip()
        status = str(it.get("status") or "pending").strip().lower()
        if not content:
            return {"success": False, "error": "todo content 不能为空"}
        if content in seen:
            return {"success": False, "error": "todo content 重复: " + content}
        if status not in VALID:
            return {"success": False, "error": "todo status 非法: " + status}
        seen.add(content)
        if status == "in_progress":
            in_progress += 1
        clean.append({"content": content, "status": status})
    if in_progress > 1:
        return {"success": False, "error": "最多只能有一个 in_progress"}

    counts = {s: sum(1 for x in clean if x["status"] == s) for s in VALID}
    payload = json.dumps(clean, ensure_ascii=False)
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO agent_todos (conversation_id, run_id, items_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(conversation_id, run_id)
            DO UPDATE SET items_json=excluded.items_json, updated_at=excluded.updated_at
        """, (int(conversation_id), _key(run_id), payload, datetime.now().isoformat()))
    return {"success": True, "counts": counts, "todos": clean,
            "message": "Updated todo list: %d pending, %d in progress, %d completed." %
                       (counts["pending"], counts["in_progress"], counts["completed"])}


def get(conversation_id, run_id=None):
    with db_cursor() as cur:
        cur.execute("SELECT items_json FROM agent_todos WHERE conversation_id=? AND run_id=?",
                    (int(conversation_id), _key(run_id)))
        row = cur.fetchone()
    if not row:
        return []
    try:
        return json.loads(row["items_json"])
    except Exception:
        return []


def format_for_prompt(conversation_id, run_id=None):
    todos = get(conversation_id, run_id)
    if not todos:
        return ""
    counts = {s: sum(1 for t in todos if t.get("status") == s) for s in VALID}
    lines = ["【当前计划】pending=%d in_progress=%d completed=%d" %
             (counts["pending"], counts["in_progress"], counts["completed"])]
    for i, t in enumerate(todos, 1):
        if t.get("status") == "completed":
            continue
        mark = ">" if t["status"] == "in_progress" else " "
        lines.append("%d. [%s] %s" % (i, mark, t["content"]))
    return "\n".join(lines)


def pending(conversation_id, run_id=None):
    return [t for t in get(conversation_id, run_id) if t.get("status") != "completed"]


def reset(conversation_id, run_id=None):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM agent_todos WHERE conversation_id=? AND run_id=?",
                    (int(conversation_id), _key(run_id)))
