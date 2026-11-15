# -*- coding: utf-8 -*-
"""给积分拦截加 debug print，下次测试能看到真实值"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEND = ROOT / "core/services/message/send.py"
content = SEND.read_text(encoding="utf-8")

if "[P1-0c-a-DEBUG]" in content:
    print("[SKIP] debug 已存在")
    sys.exit(0)

# 在 _need_credit_gate 判断前插入 debug
old = """                    _need_credit_gate = (
                        _force_swarm
                        or _numbered_prefix_matched
                        or content.strip().startswith(('#1', '#2', '#3', '#4'))
                    )
                    if _need_credit_gate:"""

new = """                    _need_credit_gate = (
                        _force_swarm
                        or _numbered_prefix_matched
                        or content.strip().startswith(('#1', '#2', '#3', '#4'))
                    )
                    # [P1-0c-a-DEBUG] 打出每个变量的值
                    print(f"[P1-0c-a-DEBUG] _force_swarm={_force_swarm}, _numbered_prefix_matched={_numbered_prefix_matched}, content[:10]={content.strip()[:10]!r}, _need={_need_credit_gate}")
                    if _need_credit_gate:"""

if old in content:
    content = content.replace(old, new, 1)
    SEND.write_text(content, encoding="utf-8")
    print(f"[OK] debug 已加，send.py 现在 {len(content)} 字符")
else:
    print("[ERROR] 锚点不匹配")
    sys.exit(1)

# 也把 get_balance 的返回值打出来
old2 = """                        _bal_gate = _cs_gate.get_balance(user_id)
                        if _bal_gate < 5:"""

new2 = """                        _bal_gate = _cs_gate.get_balance(user_id)
                        print(f"[P1-0c-a-DEBUG] get_balance(user_id={user_id}) = {_bal_gate}")
                        if _bal_gate < 5:"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    SEND.write_text(content, encoding="utf-8")
    print(f"[OK] get_balance debug 已加")
else:
    print("[WARN] get_balance 锚点不匹配，跳过")

# 语法验证
import ast
try:
    ast.parse(content)
    print("[OK] 语法通过")
except SyntaxError as e:
    print(f"[FAIL] 语法错: {e}")
