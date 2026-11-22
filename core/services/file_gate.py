# core/services/file_gate.py
# -*- coding: utf-8 -*-
"""静态前端写后语义门：语法之外，拦截重复 id 等明显破坏。"""
import re

_ID_RE = re.compile(r"""id\s*=\s*["']([^"']+)["']""", re.I)


def check_frontend(path):
    low = str(path or "").lower().replace("\\", "/")
    if not low.endswith((".js", ".mjs", ".html", ".htm")):
        return {"ok": True}
    try:
        raw = open(path, encoding="utf-8", errors="ignore").read()
    except Exception as e:
        return {"ok": False, "error": "读取失败: " + str(e)}
    ids = _ID_RE.findall(raw)
    seen = {}
    dup = []
    for i in ids:
        if i in seen:
            dup.append(i)
        seen[i] = seen.get(i, 0) + 1
    # 静态前端写操作：重复 id 直接拦截（同一模板内重复通常就是坏改动）
    bad = sorted({i for i in dup if seen[i] >= 2})
    if bad:
        return {"ok": False, "error": "重复 id: " + ", ".join(bad[:8])}
    return {"ok": True}
