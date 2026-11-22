# core/services/syntax_service.py
# -*- coding: utf-8 -*-
"""独立语法校验：Python compile + tree-sitter JS。

不经过 verify_syntax 工具，供 agent_loop 最终门禁使用。
"""
import os
import shutil
import subprocess

_JS_EXTS = (".js", ".mjs", ".cjs", ".jsx")


def _node_check(path):
    """有 Node/Electron 时用 node --check 做第二道语法关；无则跳过。"""
    exe = shutil.which("node")
    if not exe:
        for cand in (r"D:\Harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe",
                     r"D:\Harness\DeepSeek Harness.exe",
                     r"C:\Program Files\nodejs\node.exe"):
            if os.path.isfile(cand):
                exe = cand
                break
    if not exe:
        return None
    env = dict(os.environ)
    if exe.lower().endswith(".exe") and "harness" in exe.lower():
        env["ELECTRON_RUN_AS_NODE"] = "1"
    try:
        p = subprocess.run([exe, "--check", path], capture_output=True, text=True,
                           timeout=20, env=env)
        if p.returncode == 0:
            return {"ok": True, "engine": "node-check"}
        return {"ok": False, "engine": "node-check",
                "error": (p.stderr or p.stdout or "node --check failed")[:800]}
    except Exception:
        return None


def _check_python(path):
    try:
        with open(path, encoding="utf-8") as f:
            compile(f.read(), path, "exec")
        return {"ok": True, "engine": "python-compile"}
    except Exception as e:
        return {"ok": False, "engine": "python-compile", "error": str(e),
                "line": getattr(e, "lineno", None)}


def _first_error(node):
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or getattr(n, "is_missing", False):
            return n
        stack.extend(reversed(n.children))
    return None


def _check_js(path):
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_javascript as tsjs
    except Exception as e:
        return {"ok": False, "engine": "tree-sitter", "error": "tree-sitter 不可用: " + str(e)}
    try:
        lang = Language(tsjs.language())
        parser = Parser(lang)
        data = open(path, "rb").read()
        tree = parser.parse(data)
        if not tree.root_node.has_error:
            _n = _node_check(path)
            if _n and not _n.get("ok"):
                return _n
            return {"ok": True, "engine": "tree-sitter"}
        err = _first_error(tree.root_node)
        if not err:
            return {"ok": False, "engine": "tree-sitter", "error": "syntax error"}
        line, col = err.start_point
        return {"ok": False, "engine": "tree-sitter",
                "error": "syntax error near %s at line %d col %d" % (err.type, line + 1, col + 1),
                "line": line + 1, "column": col + 1}
    except Exception as e:
        return {"ok": False, "engine": "tree-sitter", "error": str(e)}


def check(path):
    path = str(path or "")
    if not path or not os.path.isfile(path):
        return {"ok": False, "engine": "none", "error": "File not found"}
    lower = path.lower()
    if lower.endswith(".py"):
        return _check_python(path)
    if lower.endswith(_JS_EXTS):
        return _check_js(path)
    return {"ok": False, "engine": "none", "error": "Unsupported file type"}
