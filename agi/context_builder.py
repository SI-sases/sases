"""Build a bounded context pack from explicit task inputs.

This is deliberately source-agnostic: conversation, workspace files, memory,
and tool evidence can all feed the same builder.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from . import context_pack

_SECRET_KEY = re.compile(r"(pass(word)?|token|secret|cookie|api[_-]?key|authorization)", re.I)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[redacted]" if _SECRET_KEY.search(str(k)) else _redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def artifact_from_path(path: str, access: str = "local") -> dict | None:
    p = Path(path)
    if not p.is_file():
        return None
    data = p.read_bytes()
    return {
        "id": "art_" + hashlib.sha256(data).hexdigest()[:12],
        "type": p.suffix.lstrip(".").lower() or "file",
        "uri": p.resolve().as_uri(),
        "name": p.name,
        "hash": "sha256:" + hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "access": access,
    }


def _dedupe_facts(facts: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for fact in facts:
        if not isinstance(fact, dict) or not fact.get("key"):
            continue
        key = str(fact["key"])
        out[key] = fact
    return list(out.values())


def _dedupe_artifacts(artifacts: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        key = str(art.get("hash") or art.get("uri") or art.get("id") or "")
        if key:
            out[key] = art
    return list(out.values())


def build(conn, goal: str, *, conversation_id: int | None = None,
          facts: list[dict] | None = None, artifacts: list[dict] | None = None,
          constraints: list[str] | None = None, acceptance: list[str] | None = None,
          history_summary: str = "", parent_context_id: str = "",
          budget: int = 4000) -> dict:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("goal is required")
    raw_facts = facts
    facts = []
    for fact in (raw_facts or []):
        safe = _redact(fact)
        if isinstance(safe, dict) and _SECRET_KEY.search(str(safe.get("key") or "")):
            safe["value"] = "[redacted]"
        facts.append(safe)
    facts = _dedupe_facts(facts)
    facts.sort(key=lambda f: 0 if str(f.get("source")) == "user" else 1)
    artifacts = _dedupe_artifacts([_redact(a) for a in (artifacts or [])])
    goal_tokens = {w.lower() for w in __import__("re").findall(r"[\w\u4e00-\u9fff]{2,}", goal)}
    artifacts.sort(key=lambda a: len(goal_tokens & {w.lower() for w in __import__("re").findall(
        r"[\w\u4e00-\u9fff]{2,}", " ".join(str(a.get(k) or "") for k in ("name", "uri", "type")))}),
        reverse=True)
    constraints = list(dict.fromkeys(c for c in (constraints or []) if c))
    acceptance = list(dict.fromkeys(a for a in (acceptance or []) if a))
    context_id = context_pack.create(
        conn, goal,
        scope={"conversation_id": conversation_id, "source": "context-builder"},
        acceptance=acceptance or ["task result reported"],
        constraints=constraints,
        facts=facts,
        artifacts=artifacts,
        history_summary=history_summary,
        parent_context_id=parent_context_id,
    )
    rendered = context_pack.render(conn, context_id, budget)
    return {
        "ok": True,
        "context_id": context_id,
        "tokens": rendered.get("tokens", 0),
        "budget": budget,
        "facts": len(facts),
        "artifacts": len(artifacts),
        "constraints": len(constraints),
        "text": rendered.get("text", ""),
    }


def build_from_paths(conn, goal: str, paths: list[str], **kwargs) -> dict:
    artifacts = [a for p in paths if (a := artifact_from_path(p))]
    return build(conn, goal, artifacts=artifacts, **kwargs)
