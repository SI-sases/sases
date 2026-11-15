# -*- coding: utf-8 -*-
"""精确读取 send.py 的意图识别段 + 派单入口"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"
lines = SEND.read_text(encoding="utf-8").splitlines()

def show(start, end, label):
    print(f"\n{'='*70}")
    print(f"=== {label} ({start}-{end}) ===")
    print('='*70)
    for i in range(start - 1, min(end, len(lines))):
        line = lines[i]
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        visual = '·' * indent + stripped
        print(f"  {i+1:4d} | {visual}")

# 段 1：意图识别完成点（is_task 赋值 + 后续）
show(630, 680, "意图识别: is_task 赋值后")

# 段 2：派单入口（if is_task:）
show(880, 920, "派单入口: if is_task:")
