# core/redact.py
# -*- coding: utf-8 -*-
"""P2-4: 统一敏感信息脱敏。"""
import re

_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{16,}"), "sk-***"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "ghp_***"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "github_pat_***"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***"),
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-]{10,}"), "Bearer ***"),
    (re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*['\"]?[A-Za-z0-9._\-]{6,}"),
     r"\1=***"),
]


def redact(text, limit: int = None):
    if text is None:
        return ""
    s = str(text)
    for rx, repl in _PATTERNS:
        s = rx.sub(repl, s)
    if limit:
        s = s[:limit]
    return s
