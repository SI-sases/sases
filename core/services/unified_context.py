# -*- coding: utf-8 -*-
# 统一上下文构建器 v4 — 全面放宽版
import os
from . import ctx_limits as L

PROVIDER_CTX = {
    "deepseek": 64000, "openai": 128000, "anthropic": 200000,
    "moonshot": 32000, "kimi": 32000, "zhipu": 32000,
    "dashscope": 32000, "qwen": 32000, "local": 8192,
}
_PROTOCOL_PREFIXES = ("[TASK]:", "[STEP_DONE]:", "[SUMMARY]:", "[RED_PACKET]",
                      "[SUPERVISOR_PROGRESS]:", "[TRACE]")


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
            cur.execute("SELECT sender, content, msg_type FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (conversation_id, max_count))
            rows = list(cur.fetchall())
    except Exception as e:
        print("[CTX] _load_history failed: " + str(e))
        return []
    result = []
    for r in reversed(rows):
        if isinstance(r, dict):
            sender, content, mtype = r.get("sender"), r.get("content"), r.get("msg_type")
        else:
            sender, content, mtype = r[0], r[1], (r[2] if len(r) > 2 else None)
        t = str(content or "")
        if not t or any(t.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        who = "用户" if sender == "user" else "AI"
        result.append({"who": who, "content": t, "is_doc": (mtype == "doc_paste") or is_doc_paste(t)})
    return result


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
