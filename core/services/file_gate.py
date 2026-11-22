# core/services/file_gate.py
# -*- coding: utf-8 -*-
"""静态前端写后语义门：语法之外，拦截重复 id 等明显破坏。

职责（只做确定性检查，不写库、不改文件）：
1. JS/MJS/CJS 文件：调用 `node --check` 做真实语法校验（node 不可用时降级跳过）。
2. HTML/HTM/JS：检查重复 id（同一文件内重复 id 通常就是坏改动）。
"""
import os
import re
import shutil
import subprocess

_ID_RE = re.compile(r"""id\s*=\s*["']([^"']+)["']""", re.I)
_JS_EXT = (".js", ".mjs", ".cjs")
_FE_EXT = (".js", ".mjs", ".cjs", ".html", ".htm")

# node 可执行文件缓存：None=未探测，False=不可用，str=路径
_NODE_BIN = None


def _node_bin():
    """定位 node 可执行文件；找不到返回 None。"""
    global _NODE_BIN
    if _NODE_BIN is not None:
        return _NODE_BIN or None
    cand = shutil.which("node")
    if not cand:
        for p in (r"D:\Harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe",
                  r"C:\Program Files\nodejs\node.exe",
                  r"C:\Program Files (x86)\nodejs\node.exe"):
            if os.path.isfile(p):
                cand = p
                break
    _NODE_BIN = cand or False
    return cand or None


def node_check(path):
    """对 JS 文件跑 `node --check`。返回 {ok, error, skipped}。"""
    node = _node_bin()
    if not node:
        return {"ok": True, "skipped": True, "error": ""}
    try:
        proc = subprocess.run(
            [node, "--check", str(path)],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "node --check 超时"}
    except Exception as e:
        return {"ok": True, "skipped": True, "error": "node 调用失败: " + str(e)}
    if proc.returncode == 0:
        return {"ok": True, "error": ""}
    detail = (proc.stderr or proc.stdout or "").strip()
    return {"ok": False, "error": "node --check 失败: " + detail[:600]}


def check_duplicate_ids(raw):
    """检查文本里的重复 id，返回重复 id 列表（已排序去重）。"""
    ids = _ID_RE.findall(raw or "")
    seen = {}
    for i in ids:
        seen[i] = seen.get(i, 0) + 1
    return sorted({i for i, n in seen.items() if n >= 2})


def check_structure(old_path, new_path):
    """写后结构门：不允许删除错误判断/return/关闭页等关键控制流。"""
    try:
        old = open(old_path, encoding="utf-8", errors="ignore").read()
        new = open(new_path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return {"ok": True}
    critical = ("if (data.error", "if (detail.error", "return;", "closeSubpage", "catch (e)")
    lost = [t for t in critical if old.count(t) > new.count(t)]
    if lost:
        return {"ok": False, "error": "关键控制流被删除: " + ", ".join(lost)}
    # 模板字符串截断：闭合 tag 数量不能少
    for tag in ("</div", "</span", "</button"):
        if old.count(tag) > new.count(tag):
            return {"ok": False, "error": "HTML 闭合标签被删除: " + tag}
    return {"ok": True}


def check_frontend(path):
    """前端写后语义门。返回 {ok, error, checks}。"""
    low = str(path or "").lower().replace("\\", "/")
    if not low.endswith(_FE_EXT):
        return {"ok": True, "checks": []}
    try:
        raw = open(path, encoding="utf-8", errors="ignore").read()
    except Exception as e:
        return {"ok": False, "error": "读取失败: " + str(e), "checks": []}
    checks = []
    # 1) JS 语法：node --check（真实解析，比正则可靠）
    if low.endswith(_JS_EXT):
        _nc = node_check(path)
        checks.append({"name": "node_check", "ok": bool(_nc.get("ok")),
                       "skipped": bool(_nc.get("skipped"))})
        if not _nc.get("ok"):
            return {"ok": False, "error": _nc.get("error") or "node --check 失败",
                    "checks": checks}
    # 2) 重复 id：同一文件内重复通常就是坏改动
    bad = check_duplicate_ids(raw)
    checks.append({"name": "duplicate_id", "ok": not bad})
    if bad:
        return {"ok": False, "error": "重复 id: " + ", ".join(bad[:8]), "checks": checks}
    return {"ok": True, "checks": checks}
