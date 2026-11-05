import os, zipfile, json
from datetime import datetime

BUILD_DIR = "D:/sases_build_temp"
VERSION = datetime.now().strftime("%Y.%m.%d.%H%M")
# 保留 "launcher" 目录，以便随时热更新 UI 源码
TARGETS = ["core", "static", "harness_modules", "launcher", "scripts/run_forever.py", "app_full.py"]

# 🔥 关键修复：排除 launcher/dist（编译出的 EXE）和 launcher/build（缓存），以及常见垃圾文件
SKIP_DIRS = [
    "__pycache__", 
    "static/downloads", 
    "static/.backups", 
    "static/_ui_shots", 
    "hive-nodes",
    "launcher/dist",     # 排除打包好的 EXE
    "launcher/build",    # 排除 PyInstaller 缓存
    "launcher/__pycache__"
]

SKIP_FILES = [".pyc", ".db", ".env", ".bak", ".spec"] # 顺便排除 .spec

os.makedirs(BUILD_DIR, exist_ok=True)
zip_path = os.path.join(BUILD_DIR, "code_update.zip")

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for target in TARGETS:
        if os.path.isfile(target):
            zipf.write(target, target)
        else:
            for root, dirs, files in os.walk(target):
                root_normalized = root.replace("\\", "/")
                
                # 检查当前目录是否被拉黑
                if any(skip in root_normalized for skip in SKIP_DIRS):
                    continue
                
                for file in files:
                    # 检查文件后缀和特殊文件
                    if any(file.endswith(ext) for ext in SKIP_FILES) or file == ".env":
                        continue
                    
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file_path)

manifest = {
    "version": VERSION,
    "update_url": "http://127.0.0.1:8002/code_update.zip" 
}
with open(os.path.join(BUILD_DIR, "version.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"纯净版热更新包生成成功: {zip_path}")
