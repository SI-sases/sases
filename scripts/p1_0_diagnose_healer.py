# -*- coding: utf-8 -*-
"""P1-0 诊断：Healer 是否还在 + prompt 现状（只读）"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

# ============ 1. Healer 文件是否存在 ============
print("=== 1. Healer 文件存在性 ===")
healer_paths = [
    "core/services/swarm/healer.py",
    "core/services/healer.py",
    "core/services/swarm/heal.py",
]
for p in healer_paths:
    full = ROOT / p
    if full.exists():
        size = full.stat().st_size
        print(f"  [EXIST] {p} ({size} bytes)")
    else:
        print(f"  [MISS ] {p}")

# 全项目搜 heal 相关文件
print("\n=== 1b. 全项目 heal* 文件 ===")
for p in ROOT.rglob("heal*.py"):
    if "venv" in str(p) or "python312" in str(p) or "__pycache__" in str(p):
        continue
    print(f"  {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")

# ============ 2. executor_callback.py 是否引用 healer ============
print("\n=== 2. executor_callback.py 引用 healer ===")
ec = ROOT / "core/services/swarm/executor_callback.py"
if ec.exists():
    content = ec.read_text(encoding="utf-8")
    for i, line in enumerate(content.splitlines(), 1):
        if "heal" in line.lower() or "script_fallback" in line.lower():
            print(f"  {i:4d} | {line.rstrip()}")
    if not any("heal" in l.lower() or "script_fallback" in l.lower()
               for l in content.splitlines()):
        print("  [无 heal 或 script_fallback 引用]")
else:
    print("  [executor_callback.py 不存在]")

# ============ 3. prompts.py 现状 ============
print("\n=== 3. prompts.py 关键规则检查 ===")
pp = ROOT / "core/services/swarm/prompts.py"
if pp.exists():
    content = pp.read_text(encoding="utf-8")
    checks = {
        "20 行限制": "20" in content and ("行" in content or "lines" in content),
        "run_python 大文件": "run_python" in content,
        "script_fallback": "script_fallback" in content or "降级" in content,
        "同类错误换方法": "连续" in content and ("错误" in content or "失败" in content),
    }
    for k, v in checks.items():
        print(f"  [{'OK ' if v else 'MISS'}] {k}")

    # 列出所有 prompt 常量名
    print("\n  所有 prompt 常量：")
    for i, line in enumerate(content.splitlines(), 1):
        if re.match(r"^[A-Z_]+_PROMPT\s*=", line.strip()):
            print(f"    {i:4d} | {line.strip()[:80]}")

# ============ 4. COMMANDER_SYSTEM_PROMPT 是否提到 file_patch 限制 ============
print("\n=== 4. COMMANDER_SYSTEM_PROMPT 里的 file_patch 规则 ===")
if pp.exists():
    content = pp.read_text(encoding="utf-8")
    m = re.search(r"COMMANDER_SYSTEM_PROMPT\s*=\s*[\"']{3}(.*?)[\"']{3}",
                  content, re.DOTALL)
    if m:
        prompt_text = m.group(1)
        # 找所有提到 file_patch 的段落
        for i, line in enumerate(prompt_text.splitlines(), 1):
            if "file_patch" in line and ("20" in line or "行" in line
                                         or "run_python" in line
                                         or "新建" in line or "创建" in line):
                print(f"  {i:4d} | {line.strip()[:120]}")
        if not any("20" in l and "file_patch" in l for l in prompt_text.splitlines()):
            print("  [COMMANDER_SYSTEM_PROMPT 里没有 '20 行' 相关规则]")
    else:
        print("  [无法提取 COMMANDER_SYSTEM_PROMPT]")

print("\n=== 诊断完成 ===")
