# scripts/diagnose_code.py
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def search(pattern, paths, label):
    print(f"\n{'='*70}")
    print(f"【{label}】")
    print(f"模式: {pattern}")
    print('='*70)
    found = 0
    for base in paths:
        full = os.path.join(ROOT, base)
        files = []
        if os.path.isfile(full):
            files = [full]
        elif os.path.isdir(full):
            for dirpath, _, filenames in os.walk(full):
                if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
                    continue
                for fn in filenames:
                    if fn.endswith('.py'):
                        files.append(os.path.join(dirpath, fn))
        else:
            print(f"  [路径不存在] {base}")
            continue
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(pattern, line):
                            rel = os.path.relpath(f, ROOT)
                            print(f"  {rel}:{i}: {line.rstrip()[:140]}")
                            found += 1
            except Exception:
                pass
    if found == 0:
        print("  （未找到）")

# ---- 问题 1：提取器调用点 ----
search(r'record_pattern', ['core'], '问题1: record_pattern 在何处被调用')

# ---- 问题 2：domain 分类逻辑位置 ----
print(f"\n{'='*70}")
print("【问题2】domain 分类逻辑探测")
print('='*70)
for dirpath, _, filenames in os.walk(ROOT):
    if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        if 'domain' in fn.lower():
            print(f"  [文件名含 domain] {os.path.relpath(os.path.join(dirpath, fn), ROOT)}")
search(r'def .*domain|domain\s*=\s*[\'"]dev[\'"]|classify.*domain',
       ['core'], '问题2b: domain 分类函数')

# ---- 问题 3：pending 任务生命周期 ----
search(r'_save_pending|_delete_pending|cleanup_finished_swarm_tasks',
       ['core'], '问题3: pending 任务的写入与清理')

# ---- 问题 4：failure_pattern 写入 ----
search(r'failure_pattern', ['core'], '问题4: failure_pattern 写入条件')

# ---- 问题 5：execution_notes 写入 ----
search(r'import_execution_note|def _summarize',
       ['core'], '问题5: execution_notes 写入路径')

# ---- 问题 6：interrupted 来源 ----
search(r'[\'"]interrupted[\'"]|finish_run',
       ['core/services/supervisor_service.py', 'core/bootstrap.py'],
       '问题6: interrupted 标记位置')

# ---- 问题 7：swarm_reviews.command 字段填什么 ----
search(r'INSERT INTO swarm_reviews|swarm_reviews\s*\(|command\s*=',
       ['core/services/executor_service.py', 'core/services/swarm_service.py'],
       '问题7: swarm_reviews.command 来源')

# ---- 附加：swarm_reviews 建表语句 ----
search(r'CREATE TABLE.*swarm_reviews',
       ['core'], '附加: swarm_reviews 建表语句')

print("\n\n" + "="*70)
print("诊断完成。请把以上完整输出贴回。")
print("="*70)
