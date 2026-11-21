# core/services/keyword_search.py
# -*- coding: utf-8 -*-
"""无 embedding 时的关键词检索（中文 bigram + 英文词）。"""
import re

_ASCII = re.compile(r"[a-z0-9_]{2,}")
_CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")


def terms(text, limit=24):
    s = str(text or "").lower()
    out = []
    for w in _ASCII.findall(s):
        out.append(w)
    for run in _CJK_RUN.findall(s):
        if len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
    seen = []
    for t in out:
        if t not in seen:
            seen.append(t)
        if len(seen) >= limit:
            break
    return seen


def score(text, ts):
    s = str(text or "").lower()
    if not s or not ts:
        return 0.0
    hits = sum(1 for t in ts if t in s)
    return hits / float(len(ts))


def rank(rows, text_of, query, top_k=5, min_score=0.12):
    ts = terms(query)
    scored = []
    for r in rows:
        sc = score(text_of(r), ts)
        if sc >= min_score:
            scored.append((sc, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]
