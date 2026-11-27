"""Versioned skill catalog and static evaluation for the main AGI."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip().lower()] = value.strip()
            body = parts[2].lstrip("\n")
    name = meta.get("name") or path.parent.name
    return {
        "name": name,
        "description": meta.get("description", "")[:300],
        "version": meta.get("version", ""),
        "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "body": body,
        "path": str(path),
    }


def list_skills() -> list[dict]:
    out = []
    if not SKILLS.is_dir():
        return out
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        if not _ID.match(path.parent.name):
            continue
        skill = _parse(path)
        out.append({k: skill[k] for k in ("name", "description", "version", "hash")})
    return out


def load_skill(name: str) -> dict:
    if not _ID.match(name or ""):
        raise KeyError("invalid skill name")
    path = SKILLS / name / "SKILL.md"
    if not path.is_file():
        raise KeyError("skill not found")
    return _parse(path)


def evaluate_skill(name: str) -> dict:
    skill = load_skill(name)
    checks = {
        "has_body": len(skill["body"].strip()) >= 20,
        "has_description": len(skill["description"]) >= 5,
        "has_version": bool(skill["version"]),
        "hash": skill["hash"],
    }
    return {"name": name, "ok": all(v for k, v in checks.items() if k != "hash"), "checks": checks}
