# -*- coding: utf-8 -*-
"""工具可见性过滤（工具减法第一步）。

只影响"注入给模型的 schema"，不删除任何工具实现：
隐藏的工具仍然在 harness_modules 下、仍可通过 tool_gateway 直接调用；
模型侧能力由 run_python / file_replace_range 等等价工具保留。
search_tools 仍能发现它们，但不会自动把 schema 加回本轮请求。

开关：环境变量 SASES_TOOL_HIDE="off" 时完全不过滤（回退到全量注入）。
本模块不 import 任何工具实现，避免循环依赖。
"""
import os

# 第一批隐藏：演示性质 / 可被 run_python 等核心工具替代 / 长期零调用
# 第二批隐藏：低频且可被核心工具组合替代（http_async / split_block / verify_* / smart_edit）
HIDDEN_DEFAULT = {
    # 同时保留下划线与连字符写法：manifest id 实际使用连字符
    "is_prime", "is-prime",
    "unit_converter", "unit-converter",
    "calculator",
    "fake_async",
    "string_utils", "string-utils",
    "text_stats", "text-stats",
    "count_chinese_chars", "count-chinese-chars",
    "base64_codec", "base64-codec",
    "json_formatter", "json-formatter",
    "extract_keypoints", "extract-keypoints",
    "file_copy", "file-copy",
    "delete_block", "delete-block",
    # Phase 2
    "http_async", "http-async",
    "split_block", "split-block",
    "verify_patch", "verify-patch",
    "verify_claim", "verify-claim",
    "smart_edit", "smart-edit",
}

def hidden_ids():
    """当前生效的隐藏集合；SASES_TOOL_HIDE=off 时返回空集。"""
    if str(os.getenv("SASES_TOOL_HIDE", "")).strip().lower() in ("off", "0", "false", "no"):
        return set()
    return set(HIDDEN_DEFAULT)


def is_visible(module_id):
    return str(module_id or "") not in hidden_ids()


def visible(tools):
    """过滤工具对象列表，保留 module_id 不在隐藏集合中的工具。"""
    hide = hidden_ids()
    if not hide:
        return list(tools or [])
    return [t for t in (tools or []) if str(getattr(t, "module_id", "") or "") not in hide]
