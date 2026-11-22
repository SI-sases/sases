# core/services/skill_service.py
# -*- coding: utf-8 -*-
"""DSH 兼容技能：data/skills/<id>/SKILL.md 或 data/skills/<id>.md。

P5-1 扫描：两种布局都识别，输出 id/name/description。
P5-2 校验：frontmatter 缺 name/description、正文为空、id 非法 → errors，
          坏技能不进入 list_skills()（不静默混入列表），只在 list_skills(with_errors=True)
          的 invalid 里可见，供前端面板展示。
P5-5 DSH 同步：只做只读扫描兼容，不做自动安装；外部包未配置时明确返回 configured=False。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL_DIR = os.path.join(ROOT, "data", "skills")

# id 只允许小写字母/数字/下划线/短横线，且必须以字母或数字开头
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _valid_id(sid):
    return bool(_ID_RE.match(str(sid or "")))


def _parse(path, fallback_id):
    """解析单个技能文件，返回 (item, errors)。item 为 None 表示完全不可读。"""
    errors = []
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        return None, ["无法读取文件: " + str(e)]

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
        else:
            errors.append("frontmatter 未闭合（缺少结尾 ---）")

    name = str(meta.get("name") or "").strip()
    desc = str(meta.get("description") or "").strip()
    sid = name or str(fallback_id or "").strip()

    if not name:
        errors.append("frontmatter 缺少 name")
    if not desc:
        errors.append("frontmatter 缺少 description")
    if not str(body or "").strip():
        errors.append("正文为空")
    if not _valid_id(sid):
        errors.append("id 非法（只允许小写字母/数字/_/-，且以字母或数字开头）: " + str(sid))

    item = {
        "id": sid,
        "name": name or sid,
        "label": name or sid,
        "description": desc,
        "desc": desc,
        "content": body,
        "path": path,
        "errors": errors,
        "valid": not errors,
    }
    return item, errors


def _scan():
    """扫描技能目录，返回 (valid_list, invalid_list)。"""
    valid, invalid = [], []
    if not os.path.isdir(SKILL_DIR):
        return valid, invalid
    for name in sorted(os.listdir(SKILL_DIR)):
        p = os.path.join(SKILL_DIR, name)
        if os.path.isdir(p):
            sp = os.path.join(p, "SKILL.md")
            if os.path.isfile(sp):
                item, errs = _parse(sp, name)
            else:
                continue
        elif name.lower().endswith(".md"):
            item, errs = _parse(p, name[:-3])
        else:
            continue
        if item is None:
            invalid.append({"id": name, "name": name, "description": "",
                            "path": p, "errors": errs, "valid": False})
        elif errs:
            invalid.append(item)
        else:
            valid.append(item)
    return valid, invalid


def list_skills(with_errors=False):
    """默认只返回通过校验的技能；with_errors=True 时返回 (valid, invalid)。"""
    valid, invalid = _scan()
    if with_errors:
        return valid, invalid
    return valid


def list_invalid():
    return _scan()[1]


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


def dsh_status():
    """P5-5：DSH 外部包只读扫描兼容状态。不做自动安装。"""
    configured = os.path.isdir(SKILL_DIR)
    try:
        count = len([n for n in os.listdir(SKILL_DIR)]) if configured else 0
    except Exception:
        count = 0
    return {
        "configured": configured,
        "dir": SKILL_DIR,
        "entries": count,
        "mode": "readonly-scan",
        "auto_install": False,
        "message": ("已配置：只读扫描 " + SKILL_DIR) if configured
                   else "未配置：data/skills 目录不存在，DSH 技能同步不可用（不会自动安装）",
    }
