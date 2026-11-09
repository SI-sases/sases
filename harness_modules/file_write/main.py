# harness_modules/file_write/main.py
import os
import ast
import json

ALLOWED_DIRS = ("static/", "core/", "scripts/", "harness_modules/", "docs/", ".backups/")
FORBIDDEN_PARTS = (".env", "users.db", "secret_key", "api_key_encryption")
FORBIDDEN_EXT = {".key", ".bin", ".pem", ".crt", ".db", ".sqlite", ".sqlite3"}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _validate_path(file_path):
    if not file_path or not isinstance(file_path, str):
        raise ValueError("缺少 file_path 参数")
    p = file_path.replace(chr(92), "/").strip()
    if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        raise ValueError("禁止绝对路径: " + file_path)
    if ".." in p.split("/"):
        raise ValueError("禁止路径穿越: " + file_path)
    if not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError("只允许以下目录：" + " / ".join(ALLOWED_DIRS) + "，收到: " + file_path)
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            raise ValueError("拒绝写入敏感文件: " + file_path)
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        raise ValueError("拒绝写入敏感文件类型: " + ext)
    return p

def _check_syntax(safe_path, content):
    ext = os.path.splitext(safe_path)[1].lower()
    if ext == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            raise ValueError("Python 语法错误(SyntaxError): " + str(e))
    if ext == ".json":
        try:
            json.loads(content)
        except Exception as e:
            raise ValueError("JSON 解析失败: " + str(e))

def run(params):
    try:
        file_path = params.get("file_path", "")
        content = params.get("content", "")
        overwrite = bool(params.get("overwrite", False))
        if content is None:
            content = ""
        safe = _validate_path(file_path)
        abs_path = os.path.join(REPO_ROOT, safe)
        if os.path.exists(abs_path) and not overwrite:
            return {"success": False, "error": "文件已存在，如需覆盖请设置 overwrite=true: " + file_path}
        _check_syntax(safe, content)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open(abs_path, "r", encoding="utf-8") as f:
            back = f.read()
        if back != content:
            try:
                os.remove(abs_path)
            except Exception:
                pass
            return {"success": False, "error": "写入校验失败，已回滚: " + file_path}
        return {"success": True, "file_path": file_path, "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"success": False, "error": str(e)}
