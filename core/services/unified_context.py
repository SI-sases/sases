# -*- coding: utf-8 -*-
# 统一上下文构建器 v4 — 全面放宽版
import json
import os
from . import ctx_limits as L

PROVIDER_CTX = {
    "deepseek": 64000, "openai": 128000, "anthropic": 200000,
    "moonshot": 32000, "kimi": 32000, "zhipu": 32000,
    "dashscope": 32000, "qwen": 32000, "local": 8192,
}
_PROTOCOL_PREFIXES = ("[TASK]:", "[STEP_DONE]:", "[SUMMARY]:", "[RED_PACKET]",
                      "[SUPERVISOR_PROGRESS]:", "[TRACE]")

# A2: 会话压缩参数
COMPACT_RATIO = 0.75
RETAIN_RATIO = 0.18
HEADROOM = 8192
MIN_COMPACT_MESSAGES = 6
MAX_SUMMARY_CHARS = 1600
_COMPACTING = set()


def estimate_tokens(text):
    if not text:
        return 0
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return int(cn / 1.5 + (len(text) - cn) / 4) + 1


def is_doc_paste(content):
    if not content:
        return False
    if len(content) < L.DOC_PASTE_MIN_CHARS or len(content) > L.DOC_PASTE_MAX_CHARS:
        return False
    md = content.count("\n#") + content.count("\n##")
    numbered = sum(1 for line in content.split("\n")
                   if len(line.strip()) >= 2 and line.strip()[0] in "DABCP" and line.strip()[1:2].isdigit())
    bullets = content.count("\n- ") + content.count("\n* ")
    return md >= 2 or numbered >= 2 or bullets >= 10


def _has_plan_numbering(text):
    import re
    hits = len(re.findall(r'(?:^|[\s，。；:：])(?:[DABCP]\d{1,2})(?:[\s:：、]|$)', text or ""))
    return hits >= 2


def _resolve_budget(user_id=None):
    env_b = os.getenv("SASES_CTX_BUDGET")
    if env_b:
        try: return int(env_b)
        except: pass
    if user_id:
        try:
            from core.db import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT provider FROM model_configs WHERE user_id=? AND model_type='api' LIMIT 1", (user_id,))
                r = cur.fetchone()
            if r:
                prov = (r[0] if not isinstance(r, dict) else r.get("provider", "")) or ""
                ctx = PROVIDER_CTX.get(str(prov).lower(), L.CTX_BUDGET)
                return max(8000, int(ctx * 0.75))
        except Exception as e:
            print("[CTX] _resolve_budget failed: " + str(e))
    return L.CTX_BUDGET


def _load_history(conversation_id, max_count=None):
    if not conversation_id:
        return []
    max_count = max_count or L.HISTORY_MAX_COUNT
    try:
        from core.db import db_cursor
        with db_cursor() as cur:
            cur.execute("SELECT id, sender, content, msg_type FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (conversation_id, max_count))
            rows = list(cur.fetchall())
    except Exception as e:
        print("[CTX] _load_history failed: " + str(e))
        return []
    summ = _summary_record(conversation_id)
    cut = int((summ or {}).get("covered_until_id") or 0)
    result = []
    for r in reversed(rows):
        if isinstance(r, dict):
            _id, sender, content, mtype = r.get("id"), r.get("sender"), r.get("content"), r.get("msg_type")
        else:
            _id, sender, content, mtype = r[0], r[1], r[2], (r[3] if len(r) > 3 else None)
        if cut and _id is not None and int(_id) <= cut:
            continue
        t = str(content or "")
        if not t or any(t.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        who = "用户" if sender == "user" else "AI"
        result.append({"id": _id, "who": who, "content": t, "is_doc": (mtype == "doc_paste") or is_doc_paste(t)})
    if summ and summ.get("content"):
        result.insert(0, {"id": 0, "who": "系统摘要", "content": summ["content"],
                          "is_doc": True, "is_summary": True})
    return result


def _raw_history(conversation_id, limit=400):
    try:
        from core.db import db_cursor
        with db_cursor() as cur:
            cur.execute("SELECT id, sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                        (conversation_id, limit))
            rows = list(cur.fetchall())
    except Exception as e:
        print("[CTX] _raw_history failed: " + str(e))
        return []
    out = []
    for r in reversed(rows):
        if isinstance(r, dict):
            _id, sender, content = r.get("id"), r.get("sender"), r.get("content")
        else:
            _id, sender, content = r[0], r[1], r[2]
        t = str(content or "")
        if not t or any(t.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        out.append({"id": _id, "who": "用户" if sender == "user" else "AI", "content": t})
    return out


def _summary_record(conversation_id):
    try:
        from core.db import db_cursor
        with db_cursor() as cur:
            cur.execute(
                "SELECT content, full_data FROM safety_memory WHERE task_id=? AND memory_type='conversation_summary' "
                "ORDER BY id DESC LIMIT 1",
                (str(conversation_id),),
            )
            r = cur.fetchone()
        if not r:
            return None
        content = r["content"] if isinstance(r, dict) else r[0]
        full = (r["full_data"] if isinstance(r, dict) else r[1]) or "{}"
        try:
            data = json.loads(full)
        except Exception:
            data = {}
        return {"content": str(content or ""), "covered_until_id": int(data.get("covered_until_id") or 0)}
    except Exception as e:
        print("[CTX] _summary_record failed: " + str(e))
        return None


def _save_summary(conversation_id, user_id, text, covered_until_id, stats):
    try:
        from core.db import db_cursor
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM safety_memory WHERE task_id=? AND memory_type='conversation_summary'",
                        (str(conversation_id),))
        from . import memory_service
        memory_service.remember(
            user_id=user_id,
            memory_type="conversation_summary",
            content=text,
            task_id=str(conversation_id),
            importance=0.85,
            full_data={"covered_until_id": int(covered_until_id), **stats},
            enable_dedup=False,
        )
    except Exception as e:
        print("[CTX] _save_summary failed: " + str(e))


def _prune_tool_text(text, head=1200, tail=400):
    s = str(text or "")
    if len(s) <= head + tail + 100:
        return s
    return s[:head] + "\n…（完整结果见 run_trace / run_artifacts）…\n" + s[-tail:]


def _summarize_prompt(rows):
    lines = []
    for m in rows:
        lines.append(m["who"] + ": " + _prune_tool_text(m["content"]))
    body = "\n".join(lines)
    if len(body) > 24000:
        body = body[:12000] + "\n…（中间省略）…\n" + body[-12000:]
    return (
        "你是会话压缩器。把下面的旧对话压缩成一段中文摘要，供后续任务继续使用。\n"
        "必须保留：用户目标、已确认方案、改过的文件与行号、失败原因、未决问题、用户偏好。\n"
        "禁止：编造、输出 JSON、输出工具调用、超过 " + str(MAX_SUMMARY_CHARS) + " 字。\n\n"
        "【旧对话】\n" + body + "\n\n【摘要】"
    )


async def maybe_compact(conversation_id, user_id, budget=None, force=False):
    """[deprecated] 旧 messages 压缩；新执行链统一使用 agent_compact。"""
    print("[CTX] unified_context.maybe_compact 已停用，请使用 agent_compact")
    return False


async def _legacy_maybe_compact(conversation_id, user_id, budget=None, force=False):
    """接近预算时压缩最旧历史；返回是否发生压缩。"""
    if os.getenv("SASES_DISABLE_COMPACTION") == "1":
        return False
    if not conversation_id or conversation_id in _COMPACTING:
        return False
    budget = int(budget or _resolve_budget(user_id))
    if not force:
        try:
            from core.db import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT 1 FROM supervisor_runs WHERE conversation_id=? AND status IN "
                            "('running','running_resumed','paused','restart_pending') LIMIT 1",
                            (conversation_id,))
                if cur.fetchone():
                    return False
        except Exception:
            pass

    _COMPACTING.add(conversation_id)
    try:
        rows = _raw_history(conversation_id)
        if len(rows) < MIN_COMPACT_MESSAGES:
            return False
        used = sum(estimate_tokens(m["content"]) for m in rows)
        threshold = min(int(budget * COMPACT_RATIO), budget - HEADROOM)
        if not force and used <= threshold:
            return False

        retain = max(400, int(budget * RETAIN_RATIO))
        acc, cut = 0, len(rows)
        for i in range(len(rows) - 1, -1, -1):
            acc += estimate_tokens(rows[i]["content"])
            if acc > retain:
                cut = i + 1
                break
        old = rows[:cut]
        if len(old) < 3:
            return False

        from .swarm.llm_parser import _call_llm
        raw = await _call_llm(_summarize_prompt(old), max_tokens=1200,
                              purpose="compaction", user_id=user_id, conversation_id=conversation_id)
        summary = (raw or "").strip()
        if not summary:
            return False
        if len(summary) > MAX_SUMMARY_CHARS:
            summary = summary[:MAX_SUMMARY_CHARS]
        covered = old[-1]["id"]
        _save_summary(conversation_id, user_id, summary, covered, {
            "messages_before": len(rows), "messages_compacted": len(old),
            "tokens_before": used, "cut_index": len(old),
        })
        print("[CTX] compacted conv=" + str(conversation_id) + " old=" + str(len(old))
              + " tokens=" + str(used) + " covered_until=" + str(covered))
        return True
    except Exception as e:
        print("[CTX] maybe_compact failed: " + str(e))
        return False
    finally:
        _COMPACTING.discard(conversation_id)


def _build_history_section(history, budget_remaining):
    n = len(history)
    if n == 0:
        return "", 0
    accepted, used = [], 0
    for i in range(n - 1, -1, -1):
        msg = history[i]
        from_end = n - i
        if msg.get("is_doc") and from_end <= 20:
            limit = None
        elif from_end <= L.HISTORY_RECENT_FULL:
            limit = None
        elif from_end <= 100:
            limit = L.HISTORY_NEAR_LIMIT
        elif from_end <= 150:
            limit = L.HISTORY_MID_LIMIT
        else:
            limit = L.HISTORY_FAR_LIMIT
        content = msg["content"]
        if limit is not None and len(content) > limit:
            content = content[:limit] + " ...[已截断]"
        line = msg["who"] + ": " + content
        t = estimate_tokens(line)
        if used + t > budget_remaining:
            print("[CTX] history truncated at #" + str(from_end))
            break
        accepted.append(line)
        used += t
    accepted.reverse()
    return "【会话历史】\n" + "\n\n".join(accepted), used


def build_context(user_id, conversation_id, content, mode="chat"):
    budget = _resolve_budget(user_id)
    stats = {"mode": mode, "budget": budget, "used": 0, "sections": {}}
    history = _load_history(conversation_id)

    if mode == "intent":
        ht, th = _build_history_section(history, 15000)
        final = (ht + "\n\n用户最新: " + content) if ht else content
        print("[CTX] mode=intent total=" + str(estimate_tokens(final)))
        return final, stats

    parts = []
    tct = ""
    try:
        from core.services.memory_service import recall_by_type
        for _tc in recall_by_type(user_id, "task_context", top_k=L.TASK_CTX_TOP_K):
            tct += str(_tc.get("content", "")) + "\n\n"
    except Exception as e:
        print("[CTX] task_context failed: " + str(e))
    if tct:
        t = estimate_tokens(tct)
        parts.append("【当前任务】\n" + tct)
        stats["used"] += t
        stats["sections"]["task_ctx"] = t

    hb = max(20000, budget - stats["used"] - 20000)
    ht, th = _build_history_section(history, hb)
    if ht:
        parts.append(ht)
        stats["used"] += th
        stats["sections"]["history"] = th

    body = "\n\n".join(parts)
    final = (body + "\n\n【用户问】\n" + content) if body else content
    print("[CTX] mode=" + mode + " total=" + str(estimate_tokens(final)) + "/" + str(budget) + " sections=" + str(stats["sections"]))
    return final, stats


def enrich_plan_input(user_id, conversation_id, user_input):
    """用户指向前文时注入完整上下文（幂等 + 兜底历史）"""
    if not conversation_id:
        return user_input

    _s = (user_input or "").strip()
    # 幂等：如果已经是 enrich 后的内容，先剥离再重注入
    if '【用户之前粘贴的完整方案' in _s or '【系统提示】用户可能在指向前文' in _s or '【最近对话历史' in _s:
        while '【用户之前粘贴的完整方案' in _s:
            _s = re.sub(r'^【用户之前粘贴的完整方案[^】]*】\s*', '', _s, count=1)
        if '【系统提示】用户可能在指向前文' in _s:
            _s = _s.split('【系统提示】用户可能在指向前文')[0].strip()
        if '【用户当前指令】' in _s:
            _p = _s.rsplit('【用户当前指令】', 1)
            if len(_p[1]) < 3000:
                _s = _p[1].strip()
        print("[CTX] enrich_plan_input: 已剥离污染前缀")
        user_input = _s

    _ref_keywords = (
        "执行", "按", "根据", "照", "继续", "上面", "之前", "前面", "刚才",
        "那份", "方案", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
        "A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "C1", "C2", "C3",
        "P1", "P2", "P3", "步骤", "第1", "第2", "第3",
    )
    _is_ref = any(h in _s[:50] for h in _ref_keywords)
    print("[CTX] enrich_plan_input check: is_ref=" + str(_is_ref) + " input=" + _s[:40])

    if not _is_ref:
        return user_input

    try:
        history = _load_history(conversation_id)
        if not history:
            return user_input
        budget = _resolve_budget(user_id)

        # S1: 优先注入上一轮 answer（用户说"继续"接上文，不是重读方案）
        try:
            from core.db import db_cursor as _dbc_s1
            with _dbc_s1() as _c_s1:
                _c_s1.execute(
                    "SELECT task_id, content FROM safety_memory "
                    "WHERE user_id=? AND memory_type='task_result' "
                    "ORDER BY id DESC LIMIT 3",
                    (user_id,)
                )
                _r_s1 = _c_s1.fetchall()
            if _r_s1:
                _sums = []
                for _row in _r_s1:
                    _txt = (_row['content'] if isinstance(_row, dict) else _row[1]) or ''
                    if _txt.strip():
                        _sums.append(_txt[:600])
                if _sums:
                    _prev = '\n\n'.join(_sums)
                    print("[CTX] enrich_plan_input injected previous_answer len=" + str(len(_prev)))
                    return ("【上一轮执行摘要（接上文用）】\n" + _prev +
                            "\n\n【用户当前指令】\n" + user_input)
        except Exception as _e_s1:
            print("[CTX] S1 查上一轮失败: " + str(_e_s1))

        # 优先 doc_paste / 长消息 / 有编号的方案
        _doc_cands = []
        for m in history:
            t = m.get("content") or ""
            if m.get("is_doc") or len(t) >= 500 or _has_plan_numbering(t):
                _doc_cands.append(m)

        if _doc_cands:
            latest = _doc_cands[-1]["content"]
            _max = int(budget * 0.75 * 4)
            if len(latest) > _max:
                latest = latest[:_max] + "\n...[方案过长已截断]"
            print("[CTX] enrich_plan_input injected doc len=" + str(len(latest)))
            return ("【用户之前粘贴的完整方案】\n" + latest +
                    "\n\n【用户当前指令】\n" + user_input)

        # 兜底：最近 50 条历史原文
        recent = history[-L.ENRICH_FALLBACK_COUNT:]
        lines, used = [], 0
        _hb = int(budget * L.ENRICH_FALLBACK_BUDGET_RATIO)
        for m in recent:
            line = m["who"] + ": " + m["content"]
            t = estimate_tokens(line)
            if used + t > _hb: break
            lines.append(line)
            used += t
        if not lines:
            return user_input
        print("[CTX] enrich_plan_input injected recent " + str(len(lines)) + " msgs, " + str(used) + " tokens")
        return ("【最近对话历史】\n" + "\n\n".join(lines) +
                "\n\n【用户当前指令】\n" + user_input)
    except Exception as e:
        print("[CTX] enrich_plan_input failed: " + str(e))
        return user_input


import re
