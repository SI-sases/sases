# core/services/agent_compact.py
# -*- coding: utf-8 -*-
"""M2: agent_messages 压缩。

- 默认保留旧的条数压缩；
- SASES_TOKEN_COMPACT=1 时使用 DSH 风格 token 压力压缩。
"""
import os
from datetime import datetime

from ..db import db_cursor
from . import token_meter


async def maybe_compact(conversation_id, user_id, keep=20, threshold=40, force=False):
    if os.getenv("SASES_TOKEN_COMPACT", "1") == "1":
        return await _token_compact(conversation_id, user_id, force=force)
    return await _count_compact(conversation_id, user_id, keep, threshold)


async def _count_compact(conversation_id, user_id, keep=20, threshold=40):
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
    summary = summary.replace("[ASK_USER]:", "").strip()
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


async def _token_compact(conversation_id, user_id, force=False):
    if not conversation_id:
        return False
    with db_cursor() as cur:
        cur.execute("SELECT id, role, content, tool_calls, tool_call_id FROM agent_messages "
                    "WHERE conversation_id=? AND COALESCE(compacted,0)=0 ORDER BY seq",
                    (int(conversation_id),))
        rows = [dict(r) for r in cur.fetchall()]
    if len(rows) < 10:
        return False

    msgs = []
    for r in rows:
        m = {"role": r["role"], "content": r["content"] or ""}
        if r.get("tool_calls"):
            import json
            try:
                m["tool_calls"] = json.loads(r["tool_calls"])
            except Exception:
                pass
        msgs.append(m)
    from core.harness_runtime import harness_runtime
    from .fast_agent import tool_schema
    from .swarm.prompts import BASE_SYSTEM
    tools = [tool_schema(t) for t in sorted(harness_runtime.list_tools(), key=lambda t: getattr(t, "module_id", "") or "")]
    before = token_meter.measure(msgs, tools=tools, system_prompt=BASE_SYSTEM)["total"]
    budget = token_meter.pressure_budget(
        model_window=int(os.getenv("SASES_CTX_WINDOW", "131072")),
        output_cap=int(os.getenv("SASES_CTX_OUTPUT", "4096")),
        headroom=int(os.getenv("SASES_CTX_HEADROOM", "32768")),
    )
    if before < budget["threshold"] and not force:
        return False

    retain = budget["retain_tokens"]
    keep = []
    acc = 0
    for r in reversed(rows):
        acc += token_meter.estimate_text(r.get("content"))
        keep.append(r)
        if acc >= retain:
            break
    keep.reverse()
    old = rows[:len(rows) - len(keep)]
    # 不把 assistant tool_calls / tool result 对切断
    while keep and keep[0].get("role") == "tool":
        old.append(keep.pop(0))
    if old and old[-1].get("role") == "assistant" and old[-1].get("tool_calls"):
        keep.insert(0, old.pop())
    if len(old) < 5:
        return False

    old_msgs = []
    for r in old:
        role = r["role"]
        text = r["content"] or ""
        if role == "tool":
            old_msgs.append({"role": "user", "content": "[工具结果] " + text})
        elif role == "assistant" and r.get("tool_calls"):
            old_msgs.append({"role": "assistant", "content": text or "[调用工具]"})
        else:
            old_msgs.append({"role": role, "content": text})
    from .swarm.llm_parser import client, MODEL
    from .swarm.prompts import BASE_PREFIX_HASH
    messages = [{"role": "system", "content": BASE_SYSTEM}] + old_msgs + [
        {"role": "user", "content": "请总结以上历史，保留用户目标、已改文件、失败原因、未决问题；不要调用工具。"}
    ]
    try:
        resp = await __import__("asyncio").to_thread(
            client.chat.completions.create,
            model=MODEL, messages=messages, tools=tools or None, tool_choice="none",
            temperature=0.2, max_tokens=800,
            extra_body={"thinking": {"type": "disabled"}},
        )
        summary = (resp.choices[0].message.content or "").strip()
        try:
            from .llm_usage_service import record_from_response
            record_from_response(resp, user_id=user_id, conversation_id=conversation_id,
                                 purpose="compaction", prefix_hash=BASE_PREFIX_HASH)
        except Exception:
            pass
    except Exception as e:
        print("[compact] token 摘要失败: " + str(e))
        return False
    if not summary:
        return False
    summary = summary.replace("[ASK_USER]:", "").strip()
    if not summary:
        return False

    now = datetime.utcnow().replace(microsecond=0).isoformat()
    old_ids = [r["id"] for r in old]
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT COALESCE(MAX(seq),0)+1 FROM agent_messages WHERE conversation_id=?",
                    (int(conversation_id),))
        seq = int(cur.fetchone()[0])
        cur.execute("INSERT INTO agent_messages (conversation_id, seq, role, content, created_at, compacted) "
                    "VALUES (?,?,?,?,?,0)",
                    (int(conversation_id), seq, "assistant", "【历史摘要】" + summary, now))
        summary_id = cur.lastrowid
        q = ",".join("?" * len(old_ids))
        cur.execute("UPDATE agent_messages SET compacted=1 WHERE id IN (" + q + ")", old_ids)
        cur.execute("DELETE FROM agent_summary WHERE conversation_id=?", (int(conversation_id),))
        cur.execute(
            "INSERT INTO agent_summary (conversation_id, covered_until_id, summary, created_at, "
            "summary_message_id, tokens_before, tokens_after, reason) VALUES (?,?,?,?,?,?,?,?)",
            (int(conversation_id), old_ids[-1], summary, now, summary_id, before,
             token_meter.measure([{"role": "assistant", "content": summary}])["total"], "token_pressure"),
        )
    print("[compact] conv=" + str(conversation_id) + " token " + str(before) +
          " -> covered " + str(len(old_ids)) + " msgs")
    return True
