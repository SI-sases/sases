# -*- coding: utf-8 -*-
"""P1-0：查看 executor_callback.py 第 38-95 行（只读）"""
from pathlib import Path

path = Path("core/services/swarm/executor_callback.py")
lines = path.read_text(encoding="utf-8").splitlines()

print(f"=== 文件共 {len(lines)} 行 ===")
print("=== 第 38-95 行 ===")
for i in range(37, min(95, len(lines))):
    print(f"{i+1:4d} | {lines[i]}")

# 额外扫描 task 变量定义
print("\n=== 所有 'task' 变量赋值（正则粗扫）===")
import re
for i, line in enumerate(lines):
    if re.search(r"\btask\s*=\s*[^=]", line) or re.search(r"\btask\s*:\s", line):
        print(f"{i+1:4d} | {line.rstrip()}")