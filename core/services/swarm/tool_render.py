# core/services/swarm/tool_render.py
# -*- coding: utf-8 -*-
"""工具结果 → 人话文本（模型/用户可读），原始 JSON 仍保留给内部判定。

设计原则（对齐 DSH）：
- 只做展示层，不改变工具返回值，不参与审核判定
- 截断信息必须显式写出，禁止静默丢弃
"""
import json
import re


def _as_dict(raw):
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _truncate_lines(lines, limit):
    lines = list(lines)
    if len(lines) <= limit:
        return lines
    return lines[:limit] + ["... (truncated, showing %d of %d lines)" % (limit, len(lines))]


def render_grep(raw):
    d = _as_dict(raw)
    if not d or "matches" not in d:
        return None
    matches = d.get("matches") or []
    total = d.get("count")
    if total is None:
        total = len(matches)
    out = ["Found %d matches" % int(total)]
    if d.get("pattern"):
        out.append("pattern: " + str(d.get("pattern"))[:120])
    current = None
    shown = 0
    for m in matches:
        if shown >= 30:
            break
        f = str(m.get("file") or "?")
        if f != current:
            current = f
            out.append("")
            out.append(f)
        out.append("Line %s: %s" % (m.get("line", "?"), str(m.get("text") or "")[:200]))
        shown += 1
    if len(matches) > shown or int(total) > shown:
        out.append("")
        out.append("... (truncated, showing %d of %s matches)" % (shown, total))
    return "\n".join(out)


def render_read(raw):
    d = _as_dict(raw)
    if not d:
        return None
    content = d.get("content") or d.get("stdout")
    if content is None:
        return None
    path = d.get("file_path") or d.get("path") or "?"
    lines = str(content).splitlines()
    total = d.get("total_lines") or len(lines)
    head = "File: %s (%s lines)" % (path, total)
    body = "\n".join(_truncate_lines(lines, 40))
    return head + ("\n" + body if body else "")


def render_edit(raw, module_id=""):
    d = _as_dict(raw)
    if not d:
        return None
    if d.get("success") is False:
        return None
    path = d.get("file_path") or d.get("path") or ""
    if module_id == "smart_edit":
        n = d.get("replaced_count")
        suffix = ("，替换 %s 处" % n) if n else ""
        return ("Updated %s%s" % (path, suffix)).strip()
    if module_id == "file_write":
        return ("Wrote %s" % path).strip()
    if module_id == "file_replace_range":
        return ("Replaced lines in %s" % path).strip()
    return None


def render_run_python(raw):
    d = _as_dict(raw)
    if not d:
        return None
    out = d.get("stdout") or ""
    err = d.get("stderr") or ""
    text = str(out).strip()
    if err.strip():
        text += ("\n[stderr]\n" + str(err).strip()[:800])
    return text or None


def render_tool_text(module_id, raw):
    """按工具类型输出人话；无法识别时回退到截断后的原文。"""
    module_id = str(module_id or "")
    try:
        if module_id == "grep_code":
            text = render_grep(raw)
        elif module_id == "file_read":
            text = render_read(raw)
        elif module_id in ("smart_edit", "file_write", "file_replace_range"):
            text = render_edit(raw, module_id)
        elif module_id == "run_python":
            text = render_run_python(raw)
        else:
            text = None
        if text:
            return text[:3000]
    except Exception as e:
        print("[tool_render] render failed: " + str(e))
    text = str(raw or "").strip()
    return text[:800] if text else ""


def summarize_error(module_id, error_text):
    """统一错误展示：Error: <tool> <message>（对齐 DSH 的 'Error: ' 前缀）"""
    msg = str(error_text or "").strip()
    if msg.startswith("Harness 失败: "):
        msg = msg[len("Harness 失败: "):]
    if msg.startswith("Error: "):
        return msg[:500]
    return ("Error: " + str(module_id) + " " + msg).strip()[:500]
