import os

print("="*20 + " 1. send.py 中的 _classify_task_type 和 create_run 调用 " + "="*20)
p1 = 'core/services/message/send.py'
if os.path.exists(p1):
    with open(p1, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if '_classify_task_type' in line or 'create_run' in line:
            print(f"\n--- 第 {i+1} 行附近 ---")
            start = max(0, i-3)
            end = min(len(lines), i+6)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")

print("\n" + "="*20 + " 2. runs.py 中的 create_run 函数定义 " + "="*20)
p2 = 'core/services/supervisor/runs.py'
if os.path.exists(p2):
    with open(p2, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'def create_run' in line or 'INSERT INTO supervisor_runs' in line:
            print(f"\n--- 第 {i+1} 行附近 ---")
            start = max(0, i-2)
            end = min(len(lines), i+12)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")
