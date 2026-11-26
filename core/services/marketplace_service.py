"""Read-only marketplace index."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INDEX = ROOT / "marketplace" / "index.json"
TYPES = {"skill", "plugin", "workflow", "adapter"}


def _load() -> list[dict]:
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    out = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        if not str(item.get("id") or "").strip():
            continue
        if str(item.get("type") or "") not in TYPES:
            continue
        out.append({
            "id": str(item["id"]),
            "type": str(item["type"]),
            "name": str(item.get("name") or item["id"]),
            "description": str(item.get("description") or ""),
            "url": str(item.get("url") or ""),
            "version": str(item.get("version") or ""),
        })
    return out


def list_entries(query: str = "", kind: str = "") -> list[dict]:
    items = _load()
    q = (query or "").strip().lower()
    if kind:
        items = [x for x in items if x["type"] == kind]
    if q:
        items = [x for x in items if q in (x["name"] + " " + x["description"] + " " + x["id"]).lower()]
    return items


def get_entry(entry_id: str) -> dict:
    for item in _load():
        if item["id"] == entry_id:
            return item
    raise KeyError("entry not found")
