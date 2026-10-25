# harness_modules/file_write/main.py
"""file_write —— 直接写入文件内容（无长度限制）。

与 file_patch 的区别：
  - file_patch：支持片段替换、锚点插入、创建、覆写，参数多
  - file_write：只做"写入内容"，参数最少

用途：长文件（> 2000 字符）时使用。
"""
import os
from datetime import datetime

ALLOWED_DIRS = ("static/", "core/", "scripts/", "docs/", "harness_modules/", "data/", "logs/", "launcher/")
SELF_PROTECTED_FILES = {
    "harness_modules/file_write/main.py",
    "harness_modules/file_write/manifest.json",
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = ".backups"


def _validate_path(file_path):
    if not file_path or not isinstance(file_path, str):
        raise ValueError("缺少 file_path")
    p = file_path.replace("\\", "/").strip()
    if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        raise ValueError(f"禁止绝对路径: {p}")
    if ".." in p.split("/"):
        raise ValueError(f"禁止路径穿越: {p}")
    if not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError(f"只允许写入：{' / '.join(ALLOWED_DIRS)}，收到: {p}")
    if p in SELF_PROTECTED_FILES:
        raise ValueError(f"禁止修改受保护文件: {p}")
    return p


def run(params):
    file_path = params.get("file_path", "")
    content = params.get("content", "")
    safe_path = _validate_path(file_path)
    abs_path = os.path.abspath(safe_path)

    existed = os.path.exists(abs_path)
    old_length = 0
    backup_path = None

    if existed:
        try:
            old_length = os.path.getsize(abs_path)
            os.makedirs(BACKUP_DIR, exist_ok=True)
            safe_name = safe_path.replace("/", "__")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = os.path.join(BACKUP_DIR, f"{safe_name}.{ts}.bak")
            with open(abs_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except Exception as e:
            print(f"[file_write] backup failed: {e}")

    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)

    result = {
        "success": True,
        "mode": "overwrite" if existed else "create",
        "file_path": safe_path,
        "old_length": old_length,
        "new_length": len(content),
        "backup": backup_path,
        "restart_required": safe_path.startswith("core/"),
    }

    # 自动语法检查
    if safe_path.endswith(".py"):
        try:
            import ast
            ast.parse(content)
        except SyntaxError as e:
            result["success"] = False
            result["syntax_error"] = f"line {e.lineno}: {e.msg}"
            result["error"] = "SYNTAX_ERROR: " + result["syntax_error"]
    return result
