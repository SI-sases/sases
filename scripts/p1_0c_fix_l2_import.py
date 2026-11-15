# -*- coding: utf-8 -*-
"""修复 reviewer_deep.py 的 LLM import"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RD = ROOT / "core/services/swarm/reviewer_deep.py"
content = RD.read_text(encoding="utf-8")

# 老的错误写法
old_import = 'from ..llm_client import call_llm  # 复用现有 LLM 客户端'
new_import = 'from .llm_parser import _call_llm as call_llm  # 复用现有 LLM 客户端'

if "from .llm_parser import _call_llm" in content:
    print("[SKIP] import 已修正")
else:
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print("[OK] import 已修正")
    else:
        print("[ERROR] 找不到 old import，打印当前 import 相关行")
        for i, line in enumerate(content.splitlines(), 1):
            if "import" in line and "llm" in line.lower():
                print(f"  {i:4d} | {line}")
        sys.exit(1)

# 修复调用签名（_call_llm 是 positional: user_content, system_prompt, ...）
old_call = '''        resp = await call_llm(
            system_prompt=system_prompt,
            user=f"触发原因：{trigger_reason}\\n请输出测试步骤 JSON。",
            max_tokens=800,
            temperature=0.1,
        )'''

new_call = '''        resp = await call_llm(
            f"触发原因：{trigger_reason}\\n请输出测试步骤 JSON。",
            system_prompt,
            max_tokens=800,
        )'''

if "触发原因：" in content and "system_prompt=system_prompt" in content:
    # 可能是旧格式，尝试替换
    if old_call in content:
        content = content.replace(old_call, new_call, 1)
        print("[OK] call_llm 调用格式已修正为 positional")
    else:
        # 兜底：可能是缩进不同
        print("[WARN] call_llm 调用格式可能已正确，或缩进不同，跳过")

RD.write_text(content, encoding="utf-8")
print(f"[OK] reviewer_deep.py 已更新，{RD.stat().st_size} bytes")

# 语法验证
import ast
try:
    ast.parse(content)
    print("[OK] 语法通过")
except SyntaxError as e:
    print(f"[FAIL] 语法错: {e}")
