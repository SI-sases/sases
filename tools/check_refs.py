# -*- coding: utf-8 -*-
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))

# 收集所有 py 文件
all_py = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    # 跳过虚拟环境和缓存
    if 'venv' in dirpath or '__pycache__' in dirpath or '.git' in dirpath:
        continue
    for f in filenames:
        if f.endswith('.py'):
            all_py.append(os.path.join(dirpath, f))

# 读取所有内容
all_content = {}
for path in all_py:
    try:
        with open(path, encoding='utf-8', errors='ignore') as fp:
            all_content[path] = fp.read()
    except Exception:
        pass

# 检查根目录每个文件
root_files = [f for f in os.listdir(ROOT) if f.endswith('.py') and os.path.isfile(os.path.join(ROOT, f))]

print(f"{'文件':<40} {'被引用次数':<10} {'最后修改'}")
print("=" * 80)

import datetime

for f in sorted(root_files):
    name = f[:-3]  # 去掉 .py
    count = 0
    for path, content in all_content.items():
        # 跳过自己
        if os.path.basename(path) == f:
            continue
        # 匹配 import name 或 from name
        pattern = r'\b' + re.escape(name) + r'\b'
        if re.search(pattern, content):
            count += 1

    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, f)))
    mtime_str = mtime.strftime('%Y-%m-%d')

    print(f"{f:<40} {count:<10} {mtime_str}")
