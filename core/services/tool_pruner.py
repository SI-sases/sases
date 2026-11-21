# core/services/tool_pruner.py
# -*- coding: utf-8 -*-
"""M1: 工具结果裁剪（只影响本轮请求，完整内容仍在 agent_messages）。"""
from .token_meter import estimate_text

MARKER = "\n...[middle pruned]...\n"


def prune_content(text, threshold=8192, head=4096, tail=1024):
    s = str(text or "")
    if len(s) <= int(threshold):
        return s, False
    h = int(head)
    t = int(tail)
    return s[:h] + MARKER + s[-t:], True


def prune_messages(messages, threshold=8192, head=4096, tail=1024):
    out = []
    count = 0
    before = 0
    after = 0
    for m in messages or []:
        if not isinstance(m, dict):
            out.append(m)
            continue
        if m.get("role") != "tool":
            out.append(m)
            continue
        content = m.get("content")
        before += estimate_text(content)
        pruned, changed = prune_content(content, threshold, head, tail)
        after += estimate_text(pruned)
        if changed:
            count += 1
            m2 = dict(m)
            m2["content"] = pruned
            out.append(m2)
        else:
            out.append(m)
    return out, count, max(0, before - after)
