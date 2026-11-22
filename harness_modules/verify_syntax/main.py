import ast
import os
import shutil
import subprocess
import sys

JS_EXTS = (".js", ".mjs", ".cjs", ".jsx")

PAIRS = {"(": ")", "[": "]", "{": "}"}
CLOSE = {v: k for k, v in PAIRS.items()}


def _js_balance(src):
    """轻量 JS 括号/字符串检查；node --check 不可用时兜底。"""
    stack = []
    i = 0
    n = len(src)
    line = 1
    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        # line comment
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            i = src.find("\n", i)
            if i == -1:
                break
            continue
        # block comment
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                return "unterminated block comment at line %d" % line
            line += src.count("\n", i, j)
            i = j + 2
            continue
        # strings / template literals
        if ch in ("'", '"', "`"):
            quote = ch
            start_line = line
            i += 1
            while i < n:
                c = src[i]
                if c == "\\":
                    i += 2
                    continue
                if c == "\n":
                    line += 1
                    if quote != "`":
                        return "unterminated string at line %d" % start_line
                if c == quote:
                    i += 1
                    break
                i += 1
            else:
                return "unterminated string/comment at line %d" % start_line
            continue
        if ch in PAIRS:
            stack.append((ch, line))
        elif ch in CLOSE:
            if not stack or stack[-1][0] != CLOSE[ch]:
                return "unexpected '%s' at line %d" % (ch, line)
            stack.pop()
        i += 1
    if stack:
        ch, ln = stack[-1]
        return "unclosed '%s' opened at line %d" % (ch, ln)
    return None


def _node_check(path):
    exe = shutil.which("node") or shutil.which("node.exe")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "--check", path], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=8)
        if r.returncode == 0:
            return {"success": True, "syntax_ok": True, "engine": "node"}
        detail = (r.stderr or r.stdout or "").strip()
        line = None
        for token in detail.replace(":", " ").split():
            if token.isdigit():
                line = int(token)
                break
        return {"success": False, "syntax_ok": False, "error": detail[:800],
                "line": line, "engine": "node"}
    except Exception:
        return None


def run(params):
    file_path = params.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        return {"success": False, "error": "File not found"}

    lower = file_path.lower()
    if lower.endswith(JS_EXTS):
        checked = _node_check(file_path)
        if checked is not None:
            return checked
        try:
            src = open(file_path, encoding="utf-8").read()
        except Exception as e:
            return {"success": False, "syntax_ok": False, "error": str(e)}
        err = _js_balance(src)
        if err:
            return {"success": False, "syntax_ok": False, "error": err, "engine": "balance"}
        return {"success": True, "syntax_ok": True, "engine": "balance"}

    if not lower.endswith(".py"):
        return {"success": False, "syntax_ok": False, "error": "Unsupported file type"}

    try:
        content = open(file_path, encoding="utf-8").read()
        ast.parse(content)
        return {"success": True, "syntax_ok": True}
    except SyntaxError as e:
        return {"success": False, "syntax_ok": False, "error": str(e),
                "line": getattr(e, "lineno", None)}
