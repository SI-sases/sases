import os

print("="*30)
print("1. subpage.js 中的 closeSubpage 函数：")
print("="*30)
p_sub = 'static/modules/subpage.js'
if os.path.exists(p_sub):
    with open(p_sub, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'function closeSubpage' in line:
            start = max(0, i-2)
            end = min(len(lines), i+20)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")

print("\n" + "="*30)
print("2. main.js 中绑定 subpage-back-btn 的代码：")
print("="*30)
p_main = 'static/modules/main.js'
if os.path.exists(p_main):
    with open(p_main, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'subpage-back-btn' in line:
            start = max(0, i-5)
            end = min(len(lines), i+15)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")
