# -*- coding: utf-8 -*-
"""精确读取 executor_callback.py 的 2 处 FORCE_RETRY（含缩进可见标记）"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ec = ROOT / "core/services/swarm/executor_callback.py"
lines = ec.read_text(encoding="utf-8").splitlines()

def show_range(start, end, label):
    print(f"\n{'='*70}")
    print(f"=== {label} ({start}-{end}) ===")
    print('='*70)
    for i in range(start - 1, min(end, len(lines))):
        line = lines[i]
        # 把每行开头的空格换成 · 方便看缩进
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        visual = '·' * indent + stripped
        print(f"  {i+1:4d} | {visual}")

# 第一处：诊断显示在 319 附近
show_range(300, 340, "第 1 处 FORCE_RETRY（约 319 行）")

# 第二处：诊断显示在 712 附近
show_range(695, 730, "第 2 处 FORCE_RETRY（约 712 行）")
