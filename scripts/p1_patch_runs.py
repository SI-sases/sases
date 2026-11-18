# -*- coding: utf-8 -*-
"""P1-3: 给 create_run 和 finish_run 加 task_state 钩子"""
import os

F = "core/services/supervisor/runs.py"
c = open(F, encoding="utf-8").read()

# ---- 补丁 A: create_run ----
OLD_A = '''        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, _mr, _tt))
        return cur.lastrowid'''

NEW_A = '''        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, _mr, _tt))
        _new_id = cur.lastrowid
    try:
        from core.services.task_state_service import open_task
        open_task(conversation_id, _new_id, goal, user_id)
    except Exception as _e_ts_open:
        print('[task_state] open_task 失败: ' + str(_e_ts_open))
    return _new_id'''

if OLD_A not in c:
    print("[ERR] create_run 锚点未找到")
else:
    c = c.replace(OLD_A, NEW_A, 1)
    print("[OK] create_run 补丁 A 完成")

# ---- 补丁 B: finish_run ----
OLD_B = """    except Exception as _e_fin:
        print('[supervisor] finish_run 推送失败: ' + str(_e_fin))
    print('[supervisor] finish_run: ' + str(run_id) + ' -> ' + status)"""

NEW_B = """    except Exception as _e_fin:
        print('[supervisor] finish_run 推送失败: ' + str(_e_fin))
    try:
        from core.services.task_state_service import finish_task
        if _conv_id:
            finish_task(_conv_id, status)
    except Exception as _e_ts_fin:
        print('[task_state] finish_task 失败: ' + str(_e_ts_fin))
    print('[supervisor] finish_run: ' + str(run_id) + ' -> ' + status)"""

if OLD_B not in c:
    print("[ERR] finish_run 锚点未找到")
else:
    c = c.replace(OLD_B, NEW_B, 1)
    print("[OK] finish_run 补丁 B 完成")

# 写入
open(F, "w", encoding="utf-8").write(c)
print("[DONE] runs.py 已更新，大小 " + str(len(c)))
