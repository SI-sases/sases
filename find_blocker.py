p = 'launcher/ui/main_window.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "未激活或已过期" in line:
        print(f"--- 找到拦截弹窗，位置 L{i} ---")
        for j in range(max(0, i-8), min(len(lines), i+5)):
            print(f"{j+1} | {lines[j].rstrip()}")
        print("-" * 40)