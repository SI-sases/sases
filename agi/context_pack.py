"""Versioned, budgeted context packs for main and sub agents."""
from __future__ import annotations

import json
import secrets
import sqlite3
import time
from typing import Any


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agi_contexts (
            context_id TEXT PRIMARY KEY,
            parent_context_id TEXT,
            scope_json TEXT,
            goal TEXT NOT NULL,
            acceptance_json TEXT,
            constraints_json TEXT,
            state_json TEXT,
            facts_json TEXT,
            artifacts_json TEXT,
            history_summary TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            token_estimate INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agi_context_patches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_id TEXT NOT NULL,
            agent_id TEXT,
            patch_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _load(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "null") or default
    except json.JSONDecodeError:
        return default


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def create(conn: sqlite3.Connection, goal: str, *, scope: dict | None = None,
           acceptance: list[str] | None = None, constraints: list[str] | None = None,
           facts: list[dict] | None = None, artifacts: list[dict] | None = None,
           history_summary: str = "", parent_context_id: str = "") -> str:
    ensure_schema(conn)
    now = int(time.time())
    context_id = "ctx_" + secrets.token_hex(8)
    state = {"status": "queued", "current_step": 0, "plan": []}
    conn.execute(
        "INSERT INTO agi_contexts(context_id,parent_context_id,scope_json,goal,acceptance_json,"
        "constraints_json,state_json,facts_json,artifacts_json,history_summary,version,"
        "token_estimate,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,1,0,?,?)",
        (context_id, parent_context_id, _dump(scope or {}), goal.strip(),
         _dump(acceptance or []), _dump(constraints or []), _dump(state),
         _dump(facts or []), _dump(artifacts or []), history_summary, now, now),
    )
    conn.commit()
    return context_id


def get(conn: sqlite3.Connection, context_id: str) -> dict | None:
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM agi_contexts WHERE context_id=?", (context_id,)).fetchone()
    if not row:
        return None
    keys = ("context_id", "parent_context_id", "scope_json", "goal", "acceptance_json",
            "constraints_json", "state_json", "facts_json", "artifacts_json",
            "history_summary", "version", "token_estimate", "created_at", "updated_at")
    data = dict(zip(keys, row))
    for key in ("scope_json", "acceptance_json", "constraints_json", "state_json",
                "facts_json", "artifacts_json"):
        data[key[:-5]] = _load(data.pop(key), [] if key != "state_json" and key != "scope_json" else {})
    return data


def render(conn: sqlite3.Connection, context_id: str, budget: int = 4000) -> dict:
    pack = get(conn, context_id)
    if not pack:
        return {"ok": False, "error": "context not found"}
    lines = [f"# Context {context_id}", f"## Goal\n{pack['goal']}"]
    for title, key in (("Acceptance", "acceptance"), ("Constraints", "constraints")):
        values = pack.get(key) or []
        if values:
            lines.append("## " + title + "\n" + "\n".join(f"- {v}" for v in values))
    facts = pack.get("facts") or []
    if facts:
        lines.append("## Facts\n" + "\n".join(
            f"- {f.get('key')}: {f.get('value')}" for f in facts if isinstance(f, dict)))
    artifacts = pack.get("artifacts") or []
    if artifacts:
        lines.append("## Artifacts\n" + "\n".join(
            f"- {a.get('name') or a.get('id')}: {a.get('uri')}" for a in artifacts if isinstance(a, dict)))
    if pack.get("history_summary"):
        lines.append("## History\n" + pack["history_summary"])
    text = "\n\n".join(lines)
    if len(text) > budget * 4:
        text = text[:budget * 4] + "\n\n[truncated to budget]"
    return {"ok": True, "context_id": context_id, "text": text, "tokens": _tokens(text)}


def patch(conn: sqlite3.Connection, context_id: str, update: dict,
          agent_id: str = "") -> bool:
    ensure_schema(conn)
    pack = get(conn, context_id)
    if not pack:
        return False
    facts = list(pack.get("facts") or [])
    for fact in update.get("facts") or []:
        if isinstance(fact, dict):
            facts = [f for f in facts if not (isinstance(f, dict) and f.get("key") == fact.get("key"))]
            facts.append(fact)
    artifacts = list(pack.get("artifacts") or []) + [
        a for a in (update.get("artifacts") or []) if isinstance(a, dict)]
    constraints = list(pack.get("constraints") or []) + [
        c for c in (update.get("constraints") or []) if c and c not in (pack.get("constraints") or [])]
    state = dict(pack.get("state") or {})
    state.update(update.get("state") or {})
    now = int(time.time())
    conn.execute(
        "UPDATE agi_contexts SET facts_json=?,artifacts_json=?,constraints_json=?,state_json=?,"
        "version=version+1,updated_at=? WHERE context_id=?",
        (_dump(facts), _dump(artifacts), _dump(constraints), _dump(state), now, context_id),
    )
    conn.execute(
        "INSERT INTO agi_context_patches(context_id,agent_id,patch_json,created_at) VALUES(?,?,?,?)",
        (context_id, agent_id, _dump(update), now),
    )
    conn.commit()
    return True


def fork(conn: sqlite3.Connection, context_id: str, goal: str | None = None) -> str | None:
    pack = get(conn, context_id)
    if not pack:
        return None
    return create(conn, goal or pack["goal"], scope=pack.get("scope") or {},
                  acceptance=pack.get("acceptance") or [],
                  constraints=pack.get("constraints") or [],
                  facts=pack.get("facts") or [], artifacts=pack.get("artifacts") or [],
                  history_summary=pack.get("history_summary") or "",
                  parent_context_id=context_id)
