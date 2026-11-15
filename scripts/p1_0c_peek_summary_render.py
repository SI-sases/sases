# -*- coding: utf-8 -*-
"""诊断：chat_ui.js 怎么渲染 [SUMMARY]"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "static/modules/chat_ui.js"

if not UI.exists():
    print("[MISS] chat_ui.js 不存在")
    sys.exit(1)

content = UI.read_text(encoding="utf-8")
lines = content.splitlines()

print("=" * 60)
print("[chat_ui.js 里所有 [SUMMARY] 相关代码]")
print("=" * 60)
for i, line in enumerate(lines, 1):
    if "SUMMARY" in line or "summary" in line.lower():
        # 打印前后 3 行上下文
        for j in range(max(0, i-3), min(len(lines), i+3)):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d} | {lines[j]}")
        print()

# 也看后端有没有过滤
print("\n" + "=" * 60)
print("[后端 messages 返回是否过滤 SUMMARY]")
print("=" * 60)
for py in ROOT.rglob("*.py"):
    if any(x in str(py) for x in ["venv", "python312", "__pycache__",
                                    "build_portable", "_archive", "core.bak"]):
        continue
    try:
        content = py.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "[SUMMARY]" in content:
        for i, line in enumerate(content.splitlines(), 1):
            if "[SUMMARY]" in line and "推送" not in line:
                print(f"  {py.relative_to(ROOT)}:{i}: {line.strip()[:120]}")
