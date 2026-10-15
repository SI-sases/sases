import os
import shutil
import ast
from datetime import datetime

FP = "core/services/swarm/prompts.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__swarm__prompts.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

before_len = len(c)

# 找 file_patch 的参数说明末尾，在其后插入其他工具
old = """- file_patch: file_path(必填) + 三选一模式：
    锚点模式: anchor_pattern + position(before/after/replace_line) + new_content
    精确片段: old_snippet + new_snippet + expected_count"""

new = """- file_patch: file_path(必填) + 三选一模式：
    锚点模式: anchor_pattern + position(before/after/replace_line) + new_content
    精确片段: old_snippet + new_snippet + expected_count
- grep_code: pattern(必填！不是 keyword/query), path, file_ext, max_results, context_lines(可选，显示前后N行)
- dir_tree: path(默认.), max_depth(默认2)
- run_python: code(Python源码字符串)
- api_call: url(必填), method(默认GET), headers, body
- verify_patch: file_path(必填), expect_contains, expect_not_contains
- harness_reload: 无参数
- web_fetch: url(必填)
- git_ops: action(必填: status/diff/log/add/commit/push/pull/rollback/snapshot)"""

if old in c:
    c = c.replace(old, new, 1)
    print("已补全 8 个工具的参数说明")
else:
    print("警告：file_patch 段落锚点未匹配")
    print("请检查 prompts.py 里 '精确片段' 附近")
    raise SystemExit(1)

try:
    ast.parse(c)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法失败: {e}")
    shutil.copy2(backup, FP)
    raise SystemExit(1)

after_len = len(c)
print(f"文件: {before_len} → {after_len}（+{after_len - before_len} 字符）")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)

print("\n完成！下一步：")
print("1. 重启服务")
print("2. 测：'用 file_patch 把 core/config.py 的 SUMMARY_MAX_TOKENS 改成 31000'")
print("3. 期望 params 里有具体值，如 {'pattern': 'SUMMARY_MAX_TOKENS', 'path': 'core/config.py'}")
print("4. del fix_tools_params.py")