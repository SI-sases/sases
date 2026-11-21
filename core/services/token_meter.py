# core/services/token_meter.py
# -*- coding: utf-8 -*-
"""M0: DSH 风格 token 估算（无模型调用，确定性）。"""
import re

_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def estimate_text(text):
    s = str(text or "")
    if not s:
        return 0
    cjk = len(_CJK.findall(s))
    other = len(s) - cjk
    return int(cjk / 1.5 + other / 4) + 1


def estimate_message(msg):
    if not isinstance(msg, dict):
        return 0
    total = 4
    total += estimate_text(msg.get("content"))
    calls = msg.get("tool_calls") or []
    for c in calls:
        fn = (c or {}).get("function") or {}
        total += 10 + estimate_text(fn.get("name")) + estimate_text(fn.get("arguments"))
    return total


def estimate_tools(tools):
    total = 0
    for t in tools or []:
        fn = (t or {}).get("function") or {}
        total += 30 + estimate_text(fn.get("name")) + estimate_text(fn.get("description"))
        total += estimate_text(fn.get("parameters"))
    return total


def measure(messages, tools=None, system_prompt=None):
    """返回 total / messages / tools / system 及阈值参考。"""
    msgs = list(messages or [])
    messages_tokens = sum(estimate_message(m) for m in msgs)
    tools_tokens = estimate_tools(tools)
    system_tokens = estimate_text(system_prompt) if system_prompt else 0
    total = messages_tokens + tools_tokens + system_tokens
    return {
        "total": total,
        "messages": messages_tokens,
        "tools": tools_tokens,
        "system": system_tokens,
    }


def pressure_budget(model_window=131072, output_cap=4096, headroom=32768,
                    threshold_ratio=0.8, retain_ratio=0.16):
    """DSH 风格：threshold = min(W*0.8, W-O-B)，保留最近 retain。"""
    w = int(model_window or 131072)
    o = int(output_cap or 4096)
    b = int(headroom or 0)
    threshold = min(int(w * threshold_ratio), max(0, w - o - b))
    retain = int((w - o) * retain_ratio)
    return {"model_window": w, "output_cap": o, "headroom": b,
            "threshold": threshold, "retain_tokens": retain}
