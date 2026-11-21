# core/tool_registry.py
# -*- coding: utf-8 -*-
"""外部工具注册表（GitHub / 本地安装的工具）。

- 内置工具：harness_modules/<id>，不受本表约束（默认启用）
- 外部工具：harness_modules/_external/<id>，必须在本表登记且 enabled=true 才会被加载
- 本文件只做元数据与开关，不负责下载/安装（安装由后续 /tools/install 完成）
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

REGISTRY_PATH = os.path.join("data", "tool_registry.json")
_SCHEMA = 1
_CACHE = {"mtime": None, "data": None}


def _empty() -> Dict[str, Any]:
    return {"schema": _SCHEMA, "tools": {}}


def _load() -> Dict[str, Any]:
    try:
        if not os.path.exists(REGISTRY_PATH):
            return _empty()
        mtime = os.path.getmtime(REGISTRY_PATH)
        if _CACHE["data"] is not None and _CACHE["mtime"] == mtime:
            return _CACHE["data"]
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty()
        data.setdefault("schema", _SCHEMA)
        data.setdefault("tools", {})
        _CACHE["mtime"] = mtime
        _CACHE["data"] = data
        return data
    except Exception as e:
        print("[tool_registry] load failed: " + str(e))
        return _empty()


def _save(data: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        tmp = REGISTRY_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, REGISTRY_PATH)
        try:
            _CACHE["mtime"] = os.path.getmtime(REGISTRY_PATH)
            _CACHE["data"] = data
        except Exception:
            pass
        return True
    except Exception as e:
        print("[tool_registry] save failed: " + str(e))
        return False


def list_tools() -> Dict[str, Dict[str, Any]]:
    return dict(_load().get("tools") or {})


def get(module_id: str) -> Optional[Dict[str, Any]]:
    return (_load().get("tools") or {}).get(str(module_id))


def is_external(module_id: str) -> bool:
    entry = get(module_id)
    return bool(entry and entry.get("external"))


def is_enabled(module_id: str, default: bool = True) -> bool:
    """内置工具无登记时按 default；外部工具无登记时按 default=False。"""
    entry = get(module_id)
    if not entry:
        return default
    return bool(entry.get("enabled", default))


def register(module_id: str, source: Optional[Dict[str, Any]] = None,
             enabled: bool = False, version: str = "", extra: Optional[Dict[str, Any]] = None) -> bool:
    data = _load()
    entry = {
        "external": True,
        "enabled": bool(enabled),
        "version": str(version or ""),
        "source": source or {},
        "installed_at": datetime.now().isoformat(),
    }
    if extra:
        entry.update(extra)
    data["tools"][str(module_id)] = entry
    return _save(data)


def set_enabled(module_id: str, enabled: bool) -> bool:
    data = _load()
    entry = data["tools"].get(str(module_id))
    if not entry:
        return False
    entry["enabled"] = bool(enabled)
    entry["updated_at"] = datetime.now().isoformat()
    return _save(data)


def remove(module_id: str) -> bool:
    data = _load()
    if str(module_id) not in data["tools"]:
        return False
    del data["tools"][str(module_id)]
    return _save(data)


def enabled_external_ids() -> list:
    out = []
    for mid, entry in list_tools().items():
        if entry.get("external") and entry.get("enabled"):
            out.append(mid)
    return out
