# -*- coding: utf-8 -*-
"""R3: task_summarizer 两处打回加 reason_type + 写 task_context"""
F = "core/services/supervisor/decider.py"
c = open(F, encoding="utf-8").read()

MARK = "reason_type='no_write'"
if MARK in c:
    print("[SKIP] R3 已存在")
    exit(0)

# 1. L35 打回：no_write
ANCHOR1 = "return {'goal_achieved': False, 'goal_reason': '没有产生真实的文件修改', 'next_hint': '请执行真实的 smart_edit / file_replace_range / file_write 或 run_python 修改'}"
NEW1 = '''_r3_ok = True
        try:
            from ...services.memory_service import remember as _r3_rm
            _r3_rm(
                user_id=task.get('user_id'),
                memory_type='task_context',
                content='上一轮被打回：no_write | 原因：没有产生真实的文件修改 | 引导：请用 smart_edit/file_replace_range/file_write/run_python',
                task_id='run_' + str(task.get('supervisor_run_id')),
                importance=0.8,
            )
        except Exception as _r3_e:
            print('[R3] 写打回原因失败: ' + str(_r3_e))
        return {'goal_achieved': False, 'reason_type': 'no_write', 'goal_reason': '没有产生真实的文件修改', 'missing': ['实际修改'], 'next_hint': '请执行真实的 smart_edit / file_replace_range / file_write 或 run_python 修改'}'''

if ANCHOR1 not in c:
    print("[ERR] L35 锚点未找到")
    exit(1)
c = c.replace(ANCHOR1, NEW1, 1)

# 2. L276 打回：fake_success（整行匹配，用 startswith 方式）
import re
lines = c.split('\n')
_found_276 = False
for i, line in enumerate(lines):
    if "'任务要求修改但无 file_write/smart_edit/file_replace_range/run_python 任何写操作成功凭证'" in line and 'return {' in line:
        # 找这行的缩进
        indent = line[:len(line) - len(line.lstrip())]
        # 替换整行（注意保留后面原有的 missing/next_hint 不动）
        lines[i] = (indent + "try:\n" +
                    indent + "    from ...services.memory_service import remember as _r3_rm2\n" +
                    indent + "    _r3_rm2(\n" +
                    indent + "        user_id=task.get('user_id'),\n" +
                    indent + "        memory_type='task_context',\n" +
                    indent + "        content='上一轮被打回：fake_success | 原因：无写操作凭证',\n" +
                    indent + "        task_id='run_' + str(task.get('supervisor_run_id')),\n" +
                    indent + "        importance=0.8,\n" +
                    indent + "    )\n" +
                    indent + "except Exception as _r3_e2:\n" +
                    indent + "    print('[R3] 写打回原因失败2: ' + str(_r3_e2))\n" +
                    line.replace("'goal_achieved': False,", "'goal_achieved': False, 'reason_type': 'fake_success',", 1))
        _found_276 = True
        break

if not _found_276:
    print("[WARN] L276 锚点未找到，只改了 L35")
else:
    c = '\n'.join(lines)

open(F, "w", encoding="utf-8").write(c)
import ast
ast.parse(c)
print("[OK] R3 已改：L35 no_write + L276 fake_success")
print("[INFO] 文件大小:", len(c))