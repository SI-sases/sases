# -*- coding: utf-8 -*-
"""验证 send.py 里有 debug 代码，然后确认服务状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"

content = SEND.read_text(encoding="utf-8")

# 检查 3 个关键标记
checks = {
    "P1-0c-a 积分拦截块": "P1-0c-a 积分拦截" in content,
    "P1-0c-a-DEBUG 打印": "P1-0c-a-DEBUG" in content,
    "get_balance debug": "get_balance(user_id=" in content,
}

print("=" * 60)
print("[文件验证] send.py 是否有新代码")
print("=" * 60)
for k, v in checks.items():
    print(f"  [{'OK' if v else 'MISS'}] {k}")

# 检查 if is_task: 附近的代码
print("\n[if is_task: 附近 25 行]")
lines = content.splitlines()
for i, line in enumerate(lines):
    if line.strip() == "if is_task:":
        for j in range(max(0, i - 2), min(len(lines), i + 25)):
            marker = ">>>" if i <= j <= i + 23 else "   "
            print(f"{marker} {j+1:4d} | {lines[j]}")
        break

# 语法验证
import ast
try:
    ast.parse(content)
    print("\n[OK] send.py 语法通过")
except SyntaxError as e:
    print(f"\n[FAIL] send.py 语法错: {e}")

# 检查是否有 python 进程在跑
print("\n[运行中的 python 进程]")
import subprocess
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
for line in r.stdout.splitlines():
    if "python" in line.lower():
        print(f"  {line.strip()}")
