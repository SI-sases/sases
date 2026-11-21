# core/services/llm_usage_service.py
# -*- coding: utf-8 -*-
"""LLM 用量记录：真实 token、缓存命中、按用途统计。"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..db import db_cursor


def _num(v) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def record_from_response(resp, user_id=None, conversation_id=None, purpose="generic", prefix_hash=None) -> Optional[int]:
    """从 OpenAI 兼容响应里提取 usage 并落库；失败静默。"""
    try:
        usage = getattr(resp, "usage", None)
        if usage is None:
            return None
        prompt_tokens = _num(getattr(usage, "prompt_tokens", 0))
        completion_tokens = _num(getattr(usage, "completion_tokens", 0))
        total_tokens = _num(getattr(usage, "total_tokens", prompt_tokens + completion_tokens))
        # DeepSeek: prompt_cache_hit_tokens / prompt_cache_miss_tokens
        cached = _num(getattr(usage, "prompt_cache_hit_tokens", 0))
        model = getattr(resp, "model", None) or ""
        return record(user_id, conversation_id, model, purpose,
                      prompt_tokens, completion_tokens, total_tokens, cached, prefix_hash)
    except Exception as e:
        print("[usage] record_from_response failed: " + str(e))
        return None


def record(user_id, conversation_id, model, purpose, prompt_tokens, completion_tokens,
           total_tokens, cached_tokens=0, prefix_hash=None) -> int:
    request_id = "llm_" + uuid.uuid4().hex[:16]
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO llm_usage (request_id, user_id, conversation_id, model, purpose, "
            "prompt_tokens, completion_tokens, total_tokens, cached_tokens, prefix_hash, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (request_id, user_id, conversation_id, model, purpose,
             int(prompt_tokens or 0), int(completion_tokens or 0), int(total_tokens or 0),
             int(cached_tokens or 0), prefix_hash, datetime.utcnow().replace(microsecond=0).isoformat()),
        )
        return cur.lastrowid


def summary(user_id=None, days: int = 7) -> Dict[str, Any]:
    cut = (datetime.utcnow() - timedelta(days=max(1, int(days or 7)))).replace(microsecond=0).isoformat()
    where = "created_at >= ?"
    args = [cut]
    if user_id:
        where += " AND user_id=?"
        args.append(user_id)
    with db_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS calls, COALESCE(SUM(prompt_tokens),0) AS prompt_tokens, "
            "COALESCE(SUM(completion_tokens),0) AS completion_tokens, "
            "COALESCE(SUM(total_tokens),0) AS total_tokens, "
            "COALESCE(SUM(cached_tokens),0) AS cached_tokens FROM llm_usage WHERE " + where,
            tuple(args),
        )
        row = dict(cur.fetchone() or {})
        cur.execute(
            "SELECT purpose, COUNT(*) AS calls, COALESCE(SUM(total_tokens),0) AS tokens "
            "FROM llm_usage WHERE " + where + " GROUP BY purpose ORDER BY calls DESC",
            tuple(args),
        )
        by_purpose = [dict(r) for r in cur.fetchall()]
        cur.execute(
            "SELECT COALESCE(prefix_hash,'') AS prefix_hash, COUNT(*) AS calls, "
            "COALESCE(SUM(prompt_tokens),0) AS prompt_tokens, "
            "COALESCE(SUM(cached_tokens),0) AS cached_tokens "
            "FROM llm_usage WHERE " + where + " GROUP BY prefix_hash ORDER BY calls DESC LIMIT 10",
            tuple(args),
        )
        by_prefix = []
        for r in cur.fetchall():
            d = dict(r)
            p = int(d.get("prompt_tokens") or 0)
            d["hit_rate"] = round(int(d.get("cached_tokens") or 0) / p, 4) if p else 0.0
            by_prefix.append(d)
    prompt = int(row.get("prompt_tokens") or 0)
    cached = int(row.get("cached_tokens") or 0)
    row["cache_hit_rate"] = round(cached / prompt, 4) if prompt else 0.0
    row["days"] = days
    row["by_purpose"] = by_purpose
    row["by_prefix"] = by_prefix
    return row


def recent(user_id=None, limit: int = 20):
    limit = max(1, min(int(limit or 20), 200))
    sql = "SELECT request_id, model, purpose, prompt_tokens, completion_tokens, total_tokens, cached_tokens, created_at FROM llm_usage"
    args = []
    if user_id:
        sql += " WHERE user_id=?"
        args.append(user_id)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with db_cursor() as cur:
        cur.execute(sql, tuple(args))
        return [dict(r) for r in cur.fetchall()]
