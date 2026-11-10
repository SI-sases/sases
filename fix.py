# fix.py
import re

# 1. 修复 file_patch 的假成功
p1 = 'harness_modules/file_patch/main.py'
with open(p1, 'r', encoding='utf-8') as f:
    c1 = f.read()

# 注入新旧内容一致性校验
if 'if original == new_content:' not in c1:
    c1 = c1.replace(
        'if new_content is not None:\n            with open(file_path, \'w\', encoding=\'utf-8\') as f:',
        'if new_content is not None:\n            if original == new_content:\n                return {"success": False, "error": "新旧内容完全一致，未做任何修改"}\n            with open(file_path, \'w\', encoding=\'utf-8\') as f:'
    )

with open(p1, 'w', encoding='utf-8') as f:
    f.write(c1)
print("✅ file_patch 假成功拦截已注入！")

# 2. 升级医生 Prompt：关注“故意制造”或“raise”字眼
p2 = 'core/services/supervisor/diagnose_service.py'
with open(p2, 'r', encoding='utf-8') as f:
    c2 = f.read()

if '如果你看到日志中包含' not in c2:
    c2 = c2.replace(
        '【核心铁律】',
        '【核心铁律】\n0. 如果你看到日志中包含“故意制造”、“raise”等字眼，说明代码中被人为埋了雷。请直接开处方：`#4: 修改 对应文件，删除 raise 语句`。'
    )

with open(p2, 'w', encoding='utf-8') as f:
    f.write(c2)
print("✅ 医生防误诊提示词已注入！")
