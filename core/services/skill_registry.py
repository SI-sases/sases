"""Read-only skill registry for SKILL.md packages."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def list_skills() -> list[dict]:
    out = []
    if not SKILLS.is_dir():
        return out
    for path in sorted(SKILLS.iterdir()):
        if not path.is_dir() or not NAME_RE.match(path.name):
            continue
        skill = path / "SKILL.md"
        if not skill.is_file():
            continue
        text = skill.read_text(encoding="utf-8", errors="replace")[:20000]
        title = path.name
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        out.append({"name": path.name, "title": title, "description": _description(text)})
    return out


def _description(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return (lines[0] if lines else "")[:300]


def load_skill(name: str) -> dict:
    if not NAME_RE.match(name or ""):
        raise KeyError("invalid skill name")
    path = SKILLS / name / "SKILL.md"
    if not path.is_file():
        raise KeyError("skill not found")
    return {"name": name, "content": path.read_text(encoding="utf-8", errors="replace")}
