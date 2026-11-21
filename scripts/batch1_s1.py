# -*- coding: utf-8 -*-
"""S1: enrich_plan_input 优先注入上一轮 task_result，而非用户原方案"""
F = "core/services/unified_context.py"
c = open(F, encoding="utf-8").read()

MARK = "# S1: 优先注入上一轮 answer"
if MARK in c:
    print("[SKIP] S1 已存在")
    exit(0)

ANCHOR = "        budget = _resolve_budget(user_id)\n\n        # 优先 doc_paste"
if ANCHOR not in c:
    print("[ERR] 锚点未找到")
    exit(1)

INJECT = '''        budget = _resolve_budget(user_id)

        # S1: 优先注入上一轮 answer（用户说"继续"接上文，不是重读方案）
        try:
            from core.db import db_cursor as _dbc_s1
            with _dbc_s1() as _c_s1:
                _c_s1.execute(
                    "SELECT task_id, content FROM safety_memory "
                    "WHERE user_id=? AND memory_type='task_result' "
                    "ORDER BY id DESC LIMIT 3",
                    (user_id,)
                )
                _r_s1 = _c_s1.fetchall()
            if _r_s1:
                _sums = []
                for _row in _r_s1:
                    _txt = (_row['content'] if isinstance(_row, dict) else _row[1]) or ''
                    if _txt.strip():
                        _sums.append(_txt[:600])
                if _sums:
                    _prev = '\\n\\n'.join(_sums)
                    print("[CTX] enrich_plan_input injected previous_answer len=" + str(len(_prev)))
                    return ("【上一轮执行摘要（接上文用）】\\n" + _prev +
                            "\\n\\n【用户当前指令】\\n" + user_input)
        except Exception as _e_s1:
            print("[CTX] S1 查上一轮失败: " + str(_e_s1))

        # 优先 doc_paste'''

c2 = c.replace(ANCHOR, INJECT, 1)
open(F, "w", encoding="utf-8").write(c2)
import ast
ast.parse(c2)
print("[OK] S1 已改，语法通过")
print("[INFO] 文件大小:", len(c2))