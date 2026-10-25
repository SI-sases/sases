import os

print("="*30)
print("1. me_settings.js 中的 openAboutPage 真实代码：")
print("="*30)
p_js = 'static/modules/me_settings.js'
if os.path.exists(p_js):
    with open(p_js, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    start_line = 0
    for i, line in enumerate(lines):
        if 'function openAboutPage' in line:
            start_line = i
            break
    if start_line > 0:
        for j in range(start_line, min(len(lines), start_line + 40)):
            print(f"{j+1}: {lines[j].rstrip()}")
    else:
        print("未找到 openAboutPage")

print("\n" + "="*30)
print("2. file_patch/main.py 中的校验代码：")
print("="*30)
p_fp = 'harness_modules/file_patch/main.py'
if os.path.exists(p_fp):
    with open(p_fp, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'verify' in line.lower() or 'subprocess' in line:
            print(f"\n--- 第 {i+1} 行附近 ---")
            start = max(0, i-2)
            end = min(len(lines), i+10)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].rstrip()}")
