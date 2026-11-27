"""Collect relevant context from prior contexts and operational lessons."""
from __future__ import annotations

import re
import sqlite3

from . import context_pack, lessons

_WORD = re.compile(r"[\w\u4e00-\u9fff]{2,}")


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")}


def _score(text: str, goal_tokens: set[str]) -> int:
    return len(_tokens(text) & goal_tokens)


def collect(conn: sqlite3.Connection, goal: str, conversation_id: int | None = None,
            limit: int = 8) -> dict:
    goal_tokens = _tokens(goal)
    facts: list[dict] = []
    artifacts: list[dict] = []
    constraints: list[str] = []
    history: list[str] = []

    if conversation_id:
        previous = context_pack.find_by_conversation(conn, int(conversation_id))
        if previous:
            facts.extend(previous.get("facts") or [])
            artifacts.extend(previous.get("artifacts") or [])
            constraints.extend(previous.get("constraints") or [])
            if previous.get("history_summary"):
                history.append(str(previous["history_summary"]))

    for lesson in lessons.search(conn, goal, limit):
        facts.append({
            "key": f"lesson_{lesson.get('id')}",
            "value": f"{lesson.get('failure')} -> {lesson.get('action')}",
            "source": "lesson",
        })
        if lesson.get("node_id"):
            history.append(f"node={lesson['node_id']}")

    ranked = sorted(
        artifacts,
        key=lambda a: _score(" ".join(str(a.get(k) or "") for k in ("name", "uri", "type")), goal_tokens),
        reverse=True,
    )[:limit]
    seen = set()
    deduped = []
    for art in ranked:
        key = art.get("hash") or art.get("uri") or art.get("id")
        if key and key not in seen:
            seen.add(key)
            deduped.append(art)
    return {
        "facts": facts,
        "artifacts": deduped,
        "constraints": list(dict.fromkeys(constraints)),
        "history_summary": " ".join(history).strip(),
        "used_conversation": bool(conversation_id and history),
    }
