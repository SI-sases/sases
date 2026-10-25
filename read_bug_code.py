import os

print("="*30)
print("1. 启动器 main_window.py 的 start 方法及测速代码：")
print("="*30)
p_launcher = 'launcher/ui/main_window.py'
if os.path.exists(p_launcher):
    with open(p_launcher, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'def start(self):' in line or 'SASES_API_URL' in line or 'urlopen' in line:
            print(f"\n--- 第 {i+1} 行附近 ---")
            start = max(0, i-2)
            end = min(len(lines), i+20)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")

print("\n" + "="*30)
print("2. 前端 subpage.js 或 main.js 中的 openSubpage 定义：")
print("="*30)
for p_js in ['static/modules/subpage.js', 'static/modules/main.js']:
    if os.path.exists(p_js):
        with open(p_js, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if 'function openSubpage' in line or 'const openSubpage' in line or 'window.openSubpage =' in line or 'returnAction' in line:
                print(f"\n--- {p_js} 第 {i+1} 行附近 ---")
                start = max(0, i-2)
                end = min(len(lines), i+25)
                for j in range(start, end):
                    print(f"{j+1}: {lines[j].rstrip()}")
