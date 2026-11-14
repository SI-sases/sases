import os

p = "scripts/build_portable.py"
if os.path.exists(p):
    c = open(p, "r", encoding="utf-8").read()
    if "ignore_patterns" not in c:
        # 尝试在 copytree 或 shutil.copy 处加入 ignore
        print("⚠️ 请手动检查 build_portable.py，当前未发现过滤逻辑，以下是你需要确保在拷贝代码文件前加入的：")
        print("""
# 在复制项目文件到打包目录时，务必过滤掉以下文件和目录：
ignore_list = ['users.db', '.env', 'license.json', 'sases.log', 'launcher_config.json', '.git', '__pycache__']
# 如果你用的是 shutil.copytree，请加上：
# shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*ignore_list))
# 如果你用的是自定义遍历，请加上： if any(x in f for x in ignore_list): continue
        """)
    else:
        print("✅ 已有过滤逻辑")
else:
    print("❌ 找不到 scripts/build_portable.py")