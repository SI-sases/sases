# core/services/agent_compact.py
# -*- coding: utf-8 -*-
"""A6: agent_messages 压缩（摘要 + 保留近期）。"""
from datetime import datetime

from ..db import db_cursor


async def maybe_compact(conversation_id, user_id, keep=20, threshold=40):
    if not conversation_id:
        return False
    with db_cursor() as cur:
        cur.execute("SELECT id, covered_until_id, summary FROM agent_summary WHERE conversation_id=?",
                    (int(conversation_id),))
        srow = cur.fetchone()
        covered = int(srow["covered_until_id"] or 0) if srow else 0
        cur.execute("SELECT id, role, content FROM agent_messages WHERE conversation_id=? AND id>? ORDER BY seq",
                    (int(conversation_id), covered))
        rows = [dict(r) for r in cur.fetchall()]
    if len(rows) < threshold:
        return False

    old, recent = rows[:-keep], rows[-keep:]
    if len(old) < 10:
        return False

    body = []
    for r in old:
        body.append(str(r.get("role")) + ": " + str(r.get("content") or "")[:500])
    prompt = ("请把下面的旧对话压缩成中文摘要，供后续继续任务。\n"
              "保留：用户目标、已改文件、失败原因、未决问题。\n"
              "不超过 800 字，不要输出 JSON。\n\n【旧对话】\n" + "\n".join(body)[:20000])
    try:
        from .swarm.llm_parser import _call_llm
        from .swarm.prompts import BASE_SYSTEM
        summary = (await _call_llm(prompt, BASE_SYSTEM, max_tokens=900,
                                   purpose="compaction", user_id=user_id,
                                   conversation_id=conversation_id) or "").strip()
    except Exception as e:
        print("[compact] 摘要失败: " + str(e))
        return False
    if not summary:
        return False

    covered_id = old[-1]["id"]
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM agent_summary WHERE conversation_id=?", (int(conversation_id),))
        cur.execute("INSERT INTO agent_summary (conversation_id, covered_until_id, summary, created_at) "
                    "VALUES (?,?,?,?)", (int(conversation_id), covered_id, summary, now))
    print("[compact] conv=" + str(conversation_id) + " covered_until=" + str(covered_id))
    return True
