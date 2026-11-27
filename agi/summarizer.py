"""Summarize recent user turns without losing constraints or decisions."""
from __future__ import annotations

import json
import os
import re

_SECRET = re.compile(r"(password|token|secret|cookie|api[_-]?key|authorization)\s*[:=]\s*\S+", re.I)
_CONSTRAINT = ("不要", "不能", "必须", "先", "dry-run", "manual", "approval", "标题", "文件")


def _fallback(history: list[str], goal: str) -> str:
    lines = []
    for item in history[-8:]:
        text = str(item or "").strip()
        if not text:
            continue
        text = _SECRET.sub(r"\1=[redacted]", text)
        if len(text) > 240:
            text = text[:240]
        lines.append(text)
    constraints = [line for line in lines if any(w in line for w in _CONSTRAINT)]
    body = "；".join(lines)
    if constraints:
        body += "\n约束：" + "；".join(dict.fromkeys(constraints))
    return f"目标：{goal}\n{body}"[:1600]


def summarize(history: list[str], goal: str, max_chars: int = 1600) -> dict:
    history = [str(h) for h in (history or []) if str(h or "").strip()]
    if not history:
        return {"ok": True, "mode": "empty", "summary": ""}
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key and not api_key.startswith("sk-dummy"):
        try:
            from openai import OpenAI
            from core.config import DEEPSEEK_BASE_URL, MODEL_NAME
            client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
            prompt = (
                "Summarize the user's recent turns for a task agent. Keep: goal, explicit "
                "constraints, file names/paths, decisions, open questions. Drop smalltalk. "
                "Return plain text, no markdown.\nGoal: %s\nTurns: %s"
                % (goal, json.dumps(history[-12:], ensure_ascii=False))
            )
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "Summarize faithfully; never invent facts."},
                          {"role": "user", "content": prompt}],
                temperature=0, max_tokens=300, timeout=15,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return {"ok": True, "mode": "llm", "summary": _SECRET.sub(r"\1=[redacted]", text)[:max_chars]}
        except Exception:
            pass
    return {"ok": True, "mode": "fallback", "summary": _fallback(history, goal)[:max_chars]}
