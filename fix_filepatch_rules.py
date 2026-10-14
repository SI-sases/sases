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

# 锚点：file_patch 参数速查的三行
old_anchor = '''- file_patch: file_path(必填) + 三选一模式：
    锚点模式: anchor_pattern + position(before/after/replace_line) + new_content
    精确片段: old_snippet + new_snippet + expected_count'''

new_anchor = '''- file_patch: file_path(必填) + 三选一模式：
    锚点模式: anchor_pattern + position(before/after/replace_line) + new_content
    精确片段: old_snippet + new_snippet + expected_count

【file_patch 硬规则（v0.33.0，违反必失败）】
1. old_snippet 必须从 file_read/grep_code 的【实际输出】里逐字复制，禁止凭记忆写。
   如果当前任务还没读原文 → 必须先调 file_read 读一次再 file_patch。
   错误示例：文件里是 `int(os.environ.get("X", "16000"))`，却写成 `X = 10000`（幻觉）。
2. position 只接受 3 个值：before / after / replace_line。
   禁止用 replace / insert / overwrite / append，会直接报错。
   改一行用 replace_line；在某行前后插入用 before/after。
3. 改单行数值：优先 old_snippet + new_snippet + expected_count:1
4. 插入新代码：优先 anchor_pattern + position + new_content
5. 同一个文件的多处修改：合并成一次 file_patch，不要拆成多个任务。'''

if old_anchor in c:
    c = c.replace(old_anchor, new_anchor, 1)
    print("改动: 加 file_patch 硬规则")
else:
    print("警告：锚点未匹配，可能已改过")
    raise SystemExit(1)

# 语法检查
try:
    ast.parse(c)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法检查失败: {e}")
    print("回滚...")
    shutil.copy2(backup, FP)
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！下一步：")
print("1. 重启服务：Ctrl+C 后 python scripts/run_forever.py")
print("2. 重测：'把 core/config.py 的 COMMANDER_MAX_TOKENS 改成 30000'")
print("3. 期望：第一次 plan 就生成正确的 old_snippet，不重拆")
print("4. 验证后删除本脚本：del fix_filepatch_rules.py")