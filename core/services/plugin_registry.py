"""File-based plugin registry (metadata MVP).

A plugin is a directory under ``plugins/`` with a ``plugin.json`` manifest.
This MVP discovers, validates, enables and disables plugins. It does not
execute plugin code; adapters/tools can opt into the manifest later.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.db import db_cursor

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS = ROOT / "plugins"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
TYPES = {"adapter", "tool", "skill"}


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plugins (
                plugin_id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                manifest_json TEXT NOT NULL,
                installed_at TEXT NOT NULL
            )
            """
        )


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _read_manifest(path: Path) -> dict | None:
    try:
        data = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    pid = str(data.get("id") or path.name)
    if not ID_RE.match(pid) or pid != path.name:
        return None
    if str(data.get("type") or "") not in TYPES:
        return None
    if not str(data.get("version") or "").strip():
        return None
    data["id"] = pid
    data.setdefault("name", pid)
    data.setdefault("description", "")
    entry = data.get("entrypoint")
    if entry:
        candidate = (path / str(entry)).resolve()
        if path.resolve() not in candidate.parents or not candidate.is_file() or candidate.suffix != ".py":
            return None
        data["entrypoint"] = candidate.relative_to(path.resolve()).as_posix()
    return data


def sync() -> None:
    ensure_schema()
    found = {}
    if PLUGINS.is_dir():
        for path in PLUGINS.iterdir():
            if path.is_dir() and ID_RE.match(path.name):
                manifest = _read_manifest(path)
                if manifest:
                    found[path.name] = manifest
    with db_cursor(commit=True) as cur:
        for pid, manifest in found.items():
            cur.execute(
                "INSERT INTO plugins(plugin_id,enabled,manifest_json,installed_at) VALUES (?,0,?,?) "
                "ON CONFLICT(plugin_id) DO UPDATE SET manifest_json=excluded.manifest_json",
                (pid, json.dumps(manifest, ensure_ascii=False), _now()),
            )
        if found:
            q = ",".join("?" for _ in found)
            cur.execute(f"DELETE FROM plugins WHERE plugin_id NOT IN ({q})", tuple(found))


def list_plugins() -> list[dict]:
    sync()
    with db_cursor() as cur:
        cur.execute("SELECT plugin_id,enabled,manifest_json,installed_at FROM plugins ORDER BY plugin_id")
        rows = cur.fetchall()
    out = []
    for row in rows:
        manifest = json.loads(row[2] or "{}")
        out.append({
            "id": row[0], "enabled": bool(row[1]),
            "installed_at": row[3],
            "name": manifest.get("name", row[0]),
            "version": manifest.get("version", ""),
            "type": manifest.get("type", ""),
            "description": manifest.get("description", ""),
        })
    return out


def set_enabled(plugin_id: str, enabled: bool) -> dict:
    sync()
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE plugins SET enabled=? WHERE plugin_id=?", (1 if enabled else 0, plugin_id))
        if cur.rowcount == 0:
            raise KeyError("plugin not found")
    return get_plugin(plugin_id)


def get_plugin(plugin_id: str) -> dict:
    for item in list_plugins():
        if item["id"] == plugin_id:
            return item
    raise KeyError("plugin not found")


def get_manifest(plugin_id: str) -> dict:
    path = PLUGINS / plugin_id / "plugin.json"
    manifest = _read_manifest(PLUGINS / plugin_id) if path.is_file() else None
    if not manifest:
        raise KeyError("plugin not found")
    return manifest
