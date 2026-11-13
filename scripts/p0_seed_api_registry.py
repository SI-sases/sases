# scripts/p0_seed_api_registry.py
import json, glob, os, sqlite3
from datetime import datetime

DB = "users.db"
now = datetime.utcnow().isoformat()

conn = sqlite3.connect(DB)
cur = conn.cursor()

mismatch = []
inserted = 0

# ===== 扫 33 个 harness manifest（api_id 用目录名） =====
for mf_path in sorted(glob.glob("harness_modules/*/manifest.json")):
    dir_name = os.path.basename(os.path.dirname(mf_path))
    with open(mf_path, encoding="utf-8") as f:
        mf = json.load(f)
    
    mid = mf.get("id", dir_name)
    if mid != dir_name:
        mismatch.append((mid, dir_name))
    
    api_id = dir_name
    endpoint = "local://harness_modules/" + dir_name
    desc = mf.get("description", "") or ""
    params_obj = mf.get("params", {}) or {}
    params = json.dumps(params_obj, ensure_ascii=False)
    
    caps = mf.get("capabilities", [])
    tags = ",".join(caps) if isinstance(caps, list) else str(caps or "")
    
    cur.execute(
        "INSERT OR REPLACE INTO api_registry "
        "(api_id, endpoint, description, params_schema, capability_tags, "
        " api_category, task_mode, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'harness', 'sync', 'active', ?, ?)",
        (api_id, endpoint, desc, params, tags, now, now)
    )
    inserted += 1

# ===== 手动补 3 条 =====
manual = [
    ("create_transfer", "/transfer/transfer", "转账给指定用户", "system"),
    ("send_message", "/messages/send", "发送消息到会话", "system"),
    ("chat_ui_render", "render://chat_ui", "前端渲染指令（不执行）", "render"),
]
for api_id, ep, desc, cat in manual:
    cur.execute(
        "INSERT OR REPLACE INTO api_registry "
        "(api_id, endpoint, description, params_schema, capability_tags, "
        " api_category, task_mode, status, created_at, updated_at) "
        "VALUES (?, ?, ?, '{}', '', ?, 'sync', 'active', ?, ?)",
        (api_id, ep, desc, cat, now, now)
    )
    inserted += 1

conn.commit()

# ===== 报告 =====
print("灌入完成：共 " + str(inserted) + " 条（harness=" + str(inserted-3) + ", manual=3）")
if mismatch:
    print("")
    print(str(len(mismatch)) + " 个 manifest id 与目录名不一致（用目录名入库）：")
    for mid, d in mismatch:
        print("  id=" + mid + "  dir=" + d)

cur.execute("SELECT api_category, COUNT(*) FROM api_registry GROUP BY api_category")
print("")
print("分类分布：")
for cat, cnt in cur.fetchall():
    print("  " + cat + ": " + str(cnt))

conn.close()