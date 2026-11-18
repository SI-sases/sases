# -*- coding: utf-8 -*-
"""开发者环境：send.py license 检查整段绕过"""
F = "core/services/message/send.py"
c = open(F, encoding="utf-8").read()

# 把整个 P0-D 预检块包在 if not DEV_BYPASS 里
OLD_START = '''    # ===== P0-D: 付费墙预检（#1~#4 执行类消息必须通过 license 检查）=====
    if isinstance(content, str):'''
NEW_START = '''    # ===== P0-D: 付费墙预检（#1~#4 执行类消息必须通过 license 检查）=====
    import os as _os_p0d
    _P0D_DEV_BYPASS = (_os_p0d.path.exists("enable_free_mode.txt") or _os_p0d.getenv("SASES_DEV_BYPASS_LICENSE") == "1")
    if _P0D_DEV_BYPASS:
        print("[license] DEV BYPASS: 跳过 P0-D 预检")
    elif isinstance(content, str):'''

if OLD_START not in c:
    print("[ERR] P0-D 起始锚点未找到")
    exit(1)

c = c.replace(OLD_START, NEW_START, 1)
open(F, "w", encoding="utf-8").write(c)
print("[OK] send.py P0-D 整段已包裹 DEV BYPASS")

# 语法校验
import ast
ast.parse(c)
print("[OK] 语法通过")
