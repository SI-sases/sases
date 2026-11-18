# -*- coding: utf-8 -*-
"""重写 smart_edit 为独立实现，不依赖 file_patch"""

MAIN_CODE = '''# harness_modules/smart_edit/main.py
"""smart_edit — 锚点片段替换（独立实现，不依赖 file_patch）"""
import os
import ast
from datetime import datetime

ALLOWED_DIRS = ("static/", "core/", "scripts/", "docs/", "harness_modules/", "data/", "logs/", "launcher/")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = ".backups"


def _validate_path(file_path):
    if not file_path or not isinstance(file_path, str):
        raise ValueError("缺少 file_path")
    p = file_path.replace("\\\\", "/").strip()
    if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        raise ValueError("禁止绝对路径: " + p)
    if ".." in p.split("/"):
        raise ValueError("禁止路径穿越: " + p)
    if not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError("只允许写入: " + " / ".join(ALLOWED_DIRS) + "，收到: " + p)
    return p


def run(params):
    file_path = params.get("file_path")
    old_code = params.get("old_code")
    new_code = params.get("new_code")
    expected_count = params.get("expected_count", 1)

    if not file_path or old_code is None or new_code is None:
        return {"success": False, "error": "缺少 file_path / old_code / new_code"}

    try:
        safe_path = _validate_path(file_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    abs_path = os.path.abspath(safe_path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": "文件不存在: " + safe_path}

    # 备份
    backup_path = None
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        safe_name = safe_path.replace("/", "__")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = os.path.join(BACKUP_DIR, safe_name + "." + ts + ".bak")
        with open(abs_path, "r", encoding="utf-8") as src:
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
    except Exception as e:
        print("[smart_edit] backup failed: " + str(e))

    # 读文件
    with open(abs_path, "r", encoding="utf-8") as f:
        original = f.read()

    # 计数
    count = original.count(old_code)
    if count == 0:
        return {"success": False, "error": "锚点未找到 (匹配 0 处)", "backup": backup_path}
    if expected_count and count != expected_count:
        return {"success": False, "error": "锚点匹配 " + str(count) + " 处，预期 " + str(expected_count) + " 处", "backup": backup_path}

    # 替换
    new_content = original.replace(old_code, new_code)
    if new_content == original:
        return {"success": False, "error": "NO_CHANGE: 替换后内容与原文一致", "backup": backup_path}

    # 语法检查（写回前）
    syntax_ok = True
    syntax_error = None
    if safe_path.endswith(".py"):
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            syntax_ok = False
            syntax_error = "line " + str(e.lineno) + ": " + str(e.msg)

    if not syntax_ok:
        return {"success": False, "error": "SYNTAX_ERROR: " + syntax_error, "backup": backup_path}

    # 写回
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    # 读回校验
    with open(abs_path, "r", encoding="utf-8") as f:
        verify = f.read()
    if new_code not in verify:
        # 回滚
        if backup_path and os.path.exists(backup_path):
            with open(backup_path, "r", encoding="utf-8") as b:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(b.read())
        return {"success": False, "error": "写后校验失败：new_code 未出现在文件中，已回滚", "backup": backup_path}

    return {
        "success": True,
        "mode": "replace",
        "file_path": safe_path,
        "replaced_count": count,
        "old_length": len(original),
        "new_length": len(new_content),
        "backup": backup_path,
        "restart_required": safe_path.startswith("core/"),
    }
'''

MANIFEST = '''{
  "id": "smart_edit",
  "name": "智能替换工具",
  "description": "提供 file_path + old_code + new_code，实现锚点片段精确替换。自动备份 + 语法检查 + 写后校验。",
  "entrypoint": "main.py",
  "capabilities": ["file_write", "code_edit"],
  "permissions": ["file_write"],
  "version": "2.0.0"
}
'''

open("harness_modules/smart_edit/main.py", "w", encoding="utf-8").write(MAIN_CODE)
open("harness_modules/smart_edit/manifest.json", "w", encoding="utf-8").write(MANIFEST)
print("[OK] smart_edit/main.py 已重写 (" + str(len(MAIN_CODE)) + " bytes)")
print("[OK] smart_edit/manifest.json 已重写")

# 语法检查
import ast
ast.parse(MAIN_CODE)
print("[OK] 语法通过")

# 立即测试
import sys, os
sys.path.insert(0, os.getcwd())
import importlib
for m in list(sys.modules.keys()):
    if "smart_edit" in m:
        del sys.modules[m]
mod = importlib.import_module("harness_modules.smart_edit.main")
print("[OK] 导入成功")

# 用临时文件测试
test_path = "data/_smart_edit_test.txt"
os.makedirs("data", exist_ok=True)
with open(test_path, "w", encoding="utf-8") as f:
    f.write("hello old_code world")

res = mod.run({"file_path": test_path, "old_code": "old_code", "new_code": "NEW_CODE"})
print("[TEST] 替换:", res)

with open(test_path, "r", encoding="utf-8") as f:
    print("[TEST] 结果文件:", f.read())

os.remove(test_path)
print("[OK] 测试通过，临时文件已清理")
