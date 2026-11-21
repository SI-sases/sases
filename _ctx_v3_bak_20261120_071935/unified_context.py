# -*- coding: utf-8 -*-
# 统一上下文构建器 v1 — intent / plan / chat 三模式
import os

PROVIDER_CTX = {
    "deepseek": 64000,
    "openai": 128000,
    "anthropic": 200000,
    "moonshot": 32000,
    "kimi": 32000,
    "zhipu": 32000,
    "dashscope": 32000,
    "qwen": 32000,
    "local": 8192,
}
DEFAULT_CTX_WINDOW = 32000
FALLBACK_BUDGET = 48000
_PROTOCOL_PREFIXES = ("[TASK]:", "[STEP_DONE]:", "[SUMMARY]:", "[RED_PACKET]", "[SUPERVISOR_PROGRESS]:", "[TRACE]")


def estimate_tokens(text):
    if not text:
        return 0
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - cn
    return int(cn / 1.5 + other / 4) + 1


def is_doc_paste(content):
    if not content or len(content) < 1500 or len(content) > 30000:
        return False
    md = content.count("\n#") + content.count("\n##")
    numbered = sum(1 for line in content.split("\n")
                   if line.strip()[:2] in ("D1","D2","D3","D4","D5","D6","D7","D8","D9",
                                           "A1","A2","A3","A4","A5","B1","B2","B3","C1","C2","C3"))
    bullets = content.count("\n- ") + content.count("\n* ")
    return md >= 2 or numbered >= 2 or bullets >= 10


def _resolve_budget(user_id=None):
    env_b = os.getenv("SASES_CTX_BUDGET")
    if env_b:
        try:
            return int(env_b)
        except Exception:
            pass
    if user_id:
        try:
            from core.db import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT provider FROM model_configs WHERE user_id=? AND model_type='api' LIMIT 1", (user_id,))
                r = cur.fetchone()
            if r:
                prov = (r[0] if not isinstance(r, dict) else r.get("provider", "")) or ""
                ctx = PROVIDER_CTX.get(str(prov).lower(), DEFAULT_CTX_WINDOW)
                return max(8000, int(ctx * 0.75))
        except Exception as e:
            print("[CTX] _resolve_budget failed: " + str(e))
    return FALLBACK_BUDGET


def _load_history(conversation_id, max_count=30):
    if not conversation_id:
        return []
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
        if not t:
            continue
        if any(t.startswith(p) for p in _PROTOCOL_PREFIXES):
            continue
        who = "用户" if sender == "user" else "AI"
        is_doc = (mtype == "doc_paste") or is_doc_paste(t)
        result.append({"who": who, "content": t, "is_doc": is_doc})
    return result


def _build_history_section(history, budget_remaining):
    n = len(history)
    if n == 0:
        return "", 0
    accepted = []
    used = 0
    for i in range(n - 1, -1, -1):
        msg = history[i]
        from_end = n - i
        if msg.get("is_doc") and from_end <= 10:
            limit = None
        elif from_end <= 3:
            limit = None
        elif from_end <= 10:
            limit = 2000
        elif from_end <= 20:
            limit = 800
        else:
            limit = 300
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
    history = _load_history(conversation_id, max_count=30)

    if mode == "intent":
        hist_text, t_hist = _build_history_section(history, 8000)
        final = (hist_text + "\n\n用户最新: " + content) if hist_text else content
        stats["sections"]["history"] = t_hist
        stats["total"] = estimate_tokens(final)
        print("[CTX] mode=intent total=" + str(stats["total"]))
        return final, stats

    parts = []
    task_ctx_text = ""
    try:
        from core.services.memory_service import recall_by_type
        for _tc in recall_by_type(user_id, "task_context", top_k=3):
            task_ctx_text += str(_tc.get("content", "")) + "\n\n"
    except Exception as e:
        print("[CTX] task_context failed: " + str(e))
    if task_ctx_text:
        t_tc = estimate_tokens(task_ctx_text)
        parts.append("【当前任务】\n" + task_ctx_text)
        stats["used"] += t_tc
        stats["sections"]["task_ctx"] = t_tc

    hist_budget = max(8000, budget - stats["used"] - 12000)
    hist_text, t_hist = _build_history_section(history, hist_budget)
    if hist_text:
        parts.append(hist_text)
        stats["used"] += t_hist
        stats["sections"]["history"] = t_hist

    body = "\n\n".join(parts)
    final = (body + "\n\n【用户问】\n" + content) if body else content
    stats["total"] = estimate_tokens(final)
    print("[CTX] mode=" + mode + " total=" + str(stats["total"]) + "/" + str(budget) + " sections=" + str(stats["sections"]))
    return final, stats


def enrich_plan_input(user_id, conversation_id, user_input):
    """只在用户明确指向前文时注入 doc_paste；找不到时追加系统提示"""
    if not conversation_id:
        return user_input

    _s = (user_input or "").strip()
    _ref_keywords = (
        "执行", "按", "根据", "照", "继续", "上面", "之前", "前面", "刚才",
        "那份", "方案", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
        "A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "C1", "C2", "C3",
        "步骤", "第1", "第2", "第3", "第一", "第二", "第三",
    )
    _is_ref = any(h in _s[:30] for h in _ref_keywords)
    print("[CTX] enrich_plan_input check: user_input=" + _s[:40] + " is_ref=" + str(_is_ref))

    if not _is_ref:
        # 不是指向前文，不注入
        return user_input

    try:
        history = _load_history(conversation_id, 30)
        doc_pastes = [m for m in history if m.get("is_doc")]
        if not doc_pastes:
            # 用户指向前文，但历史里没有 doc_paste，明确告知 AI 不要猜
            print("[CTX] enrich_plan_input: 用户指向前文但无 doc_paste，追加提示")
            return (user_input +
                    "\n\n【系统提示】用户可能在指向前文内容（如'执行 D1'、'按上面做'），"
                    "但当前会话历史里没有找到任何大段方案粘贴。"
                    "如果你无法确定用户指的是什么，请直接回复"
                    "『我在当前会话找不到你说的具体内容，请把方案原文贴到这个会话里再发指令』并停止，"
                    "禁止去读任何文件猜测 D1/D2 是什么。")
        latest = doc_pastes[-1]["content"]
        budget = _resolve_budget(user_id)
        if estimate_tokens(latest) > budget - 4000:
            latest = latest[: int(budget * 4)] + "\n...[方案过长已截断]"
        print("[CTX] enrich_plan_input injected doc_paste len=" + str(len(latest)))
        return ("【用户之前粘贴的完整方案（作为本次任务上下文）】\n" + latest
                + "\n\n【用户当前指令】\n" + user_input)
    except Exception as e:
        print("[CTX] enrich_plan_input failed: " + str(e))
        return user_input
