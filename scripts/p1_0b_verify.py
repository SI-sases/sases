# -*- coding: utf-8 -*-
"""验证 4 个修复是否到位"""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent.parent
ok = True

# 1. file_patch 外层 try/except
fp = (ROOT / "harness_modules/file_patch/main.py").read_text(encoding="utf-8")
if "外层异常兜底" in fp:
    print("[OK] file_patch 外层异常兜底")
else:
    print("[FAIL] file_patch 外层异常兜底缺失"); ok = False

# 2. file_patch original 修复
if "回滚到刚写入的 new_content" in fp:
    print("[OK] original 未定义已修")
else:
    print("[WARN] original 修复不存在（可能不需要）")

# 3. decider 白名单
dec = (ROOT / "core/services/supervisor/decider.py").read_text(encoding="utf-8")
if "_WRITE_TOOLS" in dec and "file_write" in dec:
    print("[OK] decider 白名单已加 file_write")
else:
    print("[FAIL] decider 白名单缺 file_write"); ok = False

# 4. executor_callback 状态检查
ec = (ROOT / "core/services/swarm/executor_callback.py").read_text(encoding="utf-8")
if "run 状态=" in ec and "跳过 FORCE_RETRY" in ec:
    print("[OK] FORCE_RETRY 前状态检查已加")
else:
    print("[FAIL] FORCE_RETRY 前状态检查缺失"); ok = False

# 5. 语法检查
for path in ["harness_modules/file_patch/main.py",
             "core/services/supervisor/decider.py",
             "core/services/swarm/executor_callback.py"]:
    try:
        ast.parse((ROOT / path).read_text(encoding="utf-8"))
        print(f"[OK] {path} 语法通过")
    except SyntaxError as e:
        print(f"[FAIL] {path} 语法错: {e}"); ok = False

print("\n" + ("=== 全部通过 ===" if ok else "=== 有失败，回滚检查 ==="))
