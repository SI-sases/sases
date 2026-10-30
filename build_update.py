import os, zipfile, json
from datetime import datetime

BUILD_DIR = "D:/sases_build_temp"
VERSION = datetime.now().strftime("%Y.%m.%d.%H%M")
TARGETS = ["core", "static", "harness_modules", "scripts/run_forever.py", "app_full.py"]

# 这里只是打包时的过滤规则，不是物理删除！
SKIP_DIRS = ["__pycache__", "static/downloads", "static/.backups", "static/_ui_shots", "hive-nodes"]
SKIP_FILES = [".pyc", ".db", ".env", ".bak"]

os.makedirs(BUILD_DIR, exist_ok=True)
zip_path = os.path.join(BUILD_DIR, "code_update.zip")

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for target in TARGETS:
        if os.path.isfile(target):
            zipf.write(target, target)
        else:
            for root, dirs, files in os.walk(target):
                root_normalized = root.replace("\\", "/")
                if any(skip in root_normalized for skip in SKIP_DIRS):
                    continue
                
                for file in files:
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
