# core/services/capsule_service.py
# -*- coding: utf-8 -*-
"""胶囊注册表：把本地工具 / 外部 API / 技能按"权限域"分组，供前端胶囊面板渲染。"""
import os
from typing import Any, Dict, List

from ..db import db_cursor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL_DIR = os.path.join(ROOT, "data", "skills")

_GROUPS = [
    ("read", "读取与检索", "read", True,
     ["file_read", "grep_code", "dir_tree", "verify_claim", "verify_patch", "read_user_doc"]),
    ("write", "写入与修改", "write", False,
     ["file_write", "smart_edit", "file_replace_range", "run_python", "delete_block", "split_block"]),
    ("network", "网络与网页", "network", False,
     ["web_fetch", "api_call"]),
    ("git", "Git", "write", False,
     ["git_ops"]),
]


def _tool_map() -> Dict[str, Any]:
    try:
        from ..harness_runtime import harness_runtime
        return {t.module_id: t for t in harness_runtime.list_tools()}
    except Exception as e:
        print("[capsule] 读取工具失败: " + str(e))
        return {}


def _skills() -> List[Dict[str, Any]]:
    out = []
    try:
        if os.path.isdir(SKILL_DIR):
            for name in sorted(os.listdir(SKILL_DIR)):
                if not name.endswith(".md"):
                    continue
                sid = name[:-3]
                title = sid
                try:
                    with open(os.path.join(SKILL_DIR, name), "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("#"):
                                title = line.lstrip("#").strip() or sid
                                break
                except Exception:
                    pass
                out.append({"id": sid, "label": title, "type": "skill",
                            "risk": "read", "desc": "技能：注入指令，不直接执行代码"})
    except Exception as e:
        print("[capsule] 读取技能失败: " + str(e))
    return out


def list_capsules(user_id: int) -> Dict[str, Any]:
    tools = _tool_map()
    groups = []

    for gid, label, risk, default_on, ids in _GROUPS:
        items = []
        for tid in ids:
            t = tools.get(tid)
            if not t:
                continue
            items.append({
                "id": tid,
                "label": t.name or tid,
                "type": "tool",
                "risk": risk,
                "desc": (t.description or "")[:120],
            })
        if items:
            groups.append({
                "id": gid, "label": label, "risk": risk,
                "default_on": default_on, "items": items,
            })

    # 外部 API
    api_items = []
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, api_name, api_desc, endpoint, method FROM user_api_configs "
                "WHERE user_id=? ORDER BY id DESC",
                (user_id,),
            )
            for r in cur.fetchall():
                d = dict(r)
                api_items.append({
                    "id": "ext_api_" + str(d["id"]),
                    "label": d.get("api_name") or ("API #" + str(d["id"])),
                    "type": "api",
                    "risk": "network",
                    "desc": (str(d.get("method") or "GET") + " " + str(d.get("endpoint") or "")
                             + (("｜" + str(d.get("api_desc"))) if d.get("api_desc") else ""))[:160],
                })
    except Exception as e:
        print("[capsule] 读取外部 API 失败: " + str(e))
    if api_items:
        groups.append({"id": "external", "label": "外部 API", "risk": "network",
                       "default_on": False, "items": api_items})

    # 技能
    skills = _skills()
    if skills:
        groups.append({"id": "skill", "label": "技能", "risk": "read",
                       "default_on": False, "items": skills})

    return {"groups": groups, "count": sum(len(g["items"]) for g in groups)}
