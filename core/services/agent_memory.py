# core/services/agent_memory.py
# -*- coding: utf-8 -*-
"""A0: LLM 消息日志（append-only），与 UI 的 messages 双写。"""
import json
from datetime import datetime

from ..db import db_cursor

_PROTOCOL_PREFIXES = ("[TASK]:", "[STEP_DONE]:", "[SUMMARY]:", "[TRACE]",
                      "[SUPERVISOR_PROGRESS]:", "[RED_PACKET]", "[MODIFY]")


def _next_seq(cur, conversation_id):
    cur.execute("SELECT COALESCE(MAX(seq),0)+1 FROM agent_messages WHERE conversation_id=?",
                (conversation_id,))
    row = cur.fetchone()
    return int(row[0] if not isinstance(row, dict) else row["COALESCE(MAX(seq),0)+1"])


def append(conversation_id, role, content, run_id=None, tool_calls=None, tool_call_id=None):
    if not conversation_id:
        return None
    with db_cursor(commit=True) as cur:
        seq = _next_seq(cur, conversation_id)
        cur.execute(
            "INSERT INTO agent_messages (conversation_id, run_id, seq, role, content, tool_calls, tool_call_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (int(conversation_id), run_id, seq, str(role or "user"), str(content or ""),
             json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
             tool_call_id, datetime.utcnow().replace(microsecond=0).isoformat()),
        )
        return seq


def history(conversation_id, limit=400, run_id=None):
    with db_cursor() as cur:
        # 恢复同一个 run：只取这个 run 的消息，避免其他任务/旧上下文污染
        if run_id:
            cur.execute(
                "SELECT role, content, tool_calls, tool_call_id FROM agent_messages "
                "WHERE conversation_id=? AND run_id=? AND COALESCE(compacted,0)=0 "
                "ORDER BY seq DESC LIMIT ?",
                (int(conversation_id), int(run_id), int(limit)),
            )
            rows = [dict(r) for r in cur.fetchall()]
            rows.reverse()
            return [{"role": r["role"], "content": r["content"] or "",
                     **({"tool_calls": json.loads(r["tool_calls"])} if r.get("tool_calls") else {}),
                     **({"tool_call_id": r["tool_call_id"]} if r.get("tool_call_id") else {})}
                    for r in rows]
        cur.execute("SELECT * FROM agent_summary WHERE conversation_id=?", (int(conversation_id),))
        srow = cur.fetchone()
        summary_msg_id = None
        covered = 0
        _sum = ""
        if srow:
            d = dict(srow)
            summary_msg_id = d.get("summary_message_id")
            covered = int(d.get("covered_until_id") or 0)
            _sum = d.get("summary") or ""

        if summary_msg_id:
            cur.execute("SELECT content FROM agent_messages WHERE id=?", (int(summary_msg_id),))
            sr = cur.fetchone()
            if sr:
                _sum = sr["content"] or _sum
            cur.execute(
                "SELECT role, content, tool_calls, tool_call_id FROM agent_messages "
                "WHERE conversation_id=? AND COALESCE(compacted,0)=0 AND id<>? "
                "ORDER BY seq DESC LIMIT ?",
                (int(conversation_id), int(summary_msg_id), int(limit)),
            )
        else:
            cur.execute(
                "SELECT role, content, tool_calls, tool_call_id FROM agent_messages "
                "WHERE conversation_id=? AND id>? ORDER BY seq DESC LIMIT ?",
                (int(conversation_id), covered, int(limit)),
            )
        rows = [dict(r) for r in cur.fetchall()]
    rows.reverse()
    out = []
    if srow and _sum:
        out.append({"role": "assistant" if summary_msg_id else "user",
                    "content": _sum if summary_msg_id else "【历史摘要】\n" + str(_sum)})
    for r in rows:
        m = {"role": r["role"], "content": r["content"] or ""}
        if r.get("tool_calls"):
            try:
                m["tool_calls"] = json.loads(r["tool_calls"])
            except Exception:
                pass
        if r.get("tool_call_id"):
            m["tool_call_id"] = r["tool_call_id"]
        out.append(m)
    return out


def replace_tool_result(conversation_id, tool_call_id, content):
    if not tool_call_id:
        return 0
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE agent_messages SET content=? WHERE id=("
            "SELECT id FROM agent_messages WHERE conversation_id=? AND role='tool' AND tool_call_id=? "
            "ORDER BY id DESC LIMIT 1)",
            (str(content or ""), int(conversation_id), tool_call_id),
        )
        return cur.rowcount


def count(conversation_id):
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM agent_messages WHERE conversation_id=?", (int(conversation_id),))
        r = cur.fetchone()
        return int(r[0] if not isinstance(r, dict) else list(r.values())[0])


def backfill(conversation_id):
    """从 UI messages 回填一次；已有日志则跳过。"""
    if not conversation_id or count(conversation_id) > 0:
        return 0
    with db_cursor() as cur:
        cur.execute("SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id ASC",
                    (int(conversation_id),))
        rows = [dict(r) for r in cur.fetchall()]
    n = 0
    for r in rows:
        text = str(r.get("content") or "")
        if not text or any(text.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        append(conversation_id, "user" if r.get("sender") == "user" else "assistant", text)
        n += 1
    return n
