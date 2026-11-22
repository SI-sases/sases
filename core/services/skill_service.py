# core/services/skill_service.py
# -*- coding: utf-8 -*-
"""DSH 兼容技能：data/skills/<id>/SKILL.md 或 data/skills/<id>.md。"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL_DIR = os.path.join(ROOT, "data", "skills")


def _parse(path, fallback_id):
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception:
        return None
    meta = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            body = parts[2].lstrip("\n")
    sid = str(meta.get("name") or fallback_id).strip()
    title = str(meta.get("description") or "").strip()
    if not title:
        for line in body.splitlines():
            if line.strip():
                title = line.strip().lstrip("#").strip()
                break
    return {"id": sid, "name": sid, "label": sid,
            "description": title or sid, "desc": title or sid,
            "content": body, "path": path}


def list_skills():
    out = []
    if not os.path.isdir(SKILL_DIR):
        return out
    for name in sorted(os.listdir(SKILL_DIR)):
        p = os.path.join(SKILL_DIR, name)
        if os.path.isdir(p):
            sp = os.path.join(p, "SKILL.md")
            if os.path.isfile(sp):
                item = _parse(sp, name)
                if item:
                    out.append(item)
        elif name.lower().endswith(".md"):
            item = _parse(p, name[:-3])
            if item:
                out.append(item)
    return out


def get(skill_id):
    for s in list_skills():
        if s["id"] == skill_id:
            return s
    return None


def prompt_for(ids, max_chars=6000):
    parts = []
    used = 0
    for sid in ids or []:
        s = get(str(sid))
        if not s:
            continue
        text = str(s.get("content") or "").strip()
        if not text:
            continue
        block = "【技能 " + s["id"] + "】\n" + text
        if used + len(block) > max_chars:
            block = block[:max(0, max_chars - used)]
        if block:
            parts.append(block)
            used += len(block)
        if used >= max_chars:
            break
    return "\n\n".join(parts)
