import os

p = "scripts/build_portable.py"
if not os.path.exists(p):
    print("❌ 找不到 scripts/build_portable.py")
    exit()

c = open(p, "r", encoding="utf-8").read()

# 1. 替换 copytree 那一行
old_copytree = "shutil.copytree(src, os.path.join(BUILD_DIR, item))"
new_copytree = "shutil.copytree(src, os.path.join(BUILD_DIR, item), ignore=shutil.ignore_patterns('users.db', '.env', 'license.json', 'sases.log', 'launcher_config.json', '.git', '__pycache__'))"

# 2. 替换 copy2 那一行
old_copy2 = "shutil.copy2(src, os.path.join(BUILD_DIR, item))"
new_copy2 = "if item not in ('users.db', '.env', 'license.json', 'sases.log', 'launcher_config.json'):\n                    shutil.copy2(src, os.path.join(BUILD_DIR, item))"

modified = False
if old_copytree in c:
    c = c.replace(old_copytree, new_copytree)
    modified = True
if old_copy2 in c:
    c = c.replace(old_copy2, new_copy2)
    modified = True

if modified:
    open(p, "w", encoding="utf-8").write(c)
    print("✅ 强制修复成功！现在打包会跳过 users.db 和 .env 了。")
else:
    print("⚠️ 没有找到目标字符串，请手动检查文件内容。")