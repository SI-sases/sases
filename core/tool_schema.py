# core/tool_schema.py
# -*- coding: utf-8 -*-
"""P1-1：按 manifest.params 做轻量参数校验，避免错误参数进入工具体。"""


def _type_name(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (list, tuple)):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def _matches(v, expected):
    e = str(expected or "string").lower()
    t = _type_name(v)
    if e in ("int", "integer"):
        return t == "int"
    if e in ("float", "number"):
        return t in ("float", "int")
    if e in ("bool", "boolean"):
        return t == "bool"
    if e in ("string", "str"):
        return t == "string"
    if e in ("array", "list"):
        return t == "array"
    if e in ("object", "dict"):
        return t == "object"
    return True


def validate_params(manifest, params):
    """返回 (ok, error)。只校验声明的字段，未声明字段放行。"""
    spec = dict(getattr(manifest, "params", {}) or {})
    params = params or {}
    for name, rule in spec.items():
        if not isinstance(rule, dict):
            continue
        if rule.get("required") and (name not in params or params.get(name) in (None, "")):
            return False, "INVALID_ARGS: 缺少必填参数 " + name
        if name not in params or params.get(name) is None:
            continue
        value = params[name]
        if rule.get("type") and not _matches(value, rule.get("type")):
            return False, ("INVALID_ARGS: 参数 " + name + " 需要 " + str(rule.get("type"))
                           + "，收到 " + _type_name(value))
        if rule.get("enum") and value not in rule.get("enum"):
            return False, "INVALID_ARGS: 参数 " + name + " 不在允许值 " + str(rule.get("enum"))
    return True, ""
