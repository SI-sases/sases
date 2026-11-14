# scripts/scan_user_api_configs.py
import os
import sqlite3

TARGET = "user_api_configs"
results = []

# 扫描所有 .db 文件（跳过 venv）
for root, dirs, files in os.walk("."):
    # 跳过 venv / 缓存
    if any(x in root for x in ["venv", "__pycache__", ".git", "node_modules"]):
        continue
    for f in files:
        if f.endswith(".db"):
            path = os.path.join(root, f)
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (TARGET,)
                )
                row = cur.fetchone()
                if row:
                    # 表存在，统计行数 + 字段
                    cur.execute("SELECT COUNT(*) FROM " + TARGET)
                    cnt = cur.fetchone()[0]
                    cur.execute("PRAGMA table_info(" + TARGET + ")")
                    cols = [r[1] for r in cur.fetchall()]
                    results.append((path, "HAS", cnt, cols))
                else:
                    results.append((path, "no", 0, []))
                conn.close()
            except Exception as e:
                results.append((path, "ERR: " + str(e)[:50], 0, []))

print("=" * 70)
print("扫描结果：")
print("=" * 70)
for path, status, cnt, cols in results:
    if status == "HAS":
        print("[FOUND] " + path)
        print("        行数: " + str(cnt))
        print("        字段: " + ", ".join(cols))
    elif status == "no":
        print("[no]    " + path)
    else:
        print("[skip]  " + path + " (" + status + ")")

found = [r for r in results if r[1] == "HAS"]
print("")
print("=" * 70)
if found:
    print("找到 " + str(len(found)) + " 个有 " + TARGET + " 表的库")
    print("")
    print("从找到的库导出建表语句（复制到下一步用）：")
    print("=" * 70)
    path = found[0][0]
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (TARGET,)
    )
    row = cur.fetchone()
    if row:
        print(row[0])
    conn.close()
else:
    print("所有库都没有 " + TARGET + " 表")
    print("确认：只能按 user_api_routes.py 反推重建")
print("=" * 70)