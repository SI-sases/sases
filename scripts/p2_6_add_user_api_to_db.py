import shutil
from datetime import datetime

TARGET = "core/db.py"
MARKER = "# ===== user_api_configs (P2.6) ====="

SQL_BLOCK = '''
        # ===== user_api_configs (P2.6) =====
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_api_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_name TEXT NOT NULL,
                api_desc TEXT,
                endpoint TEXT NOT NULL,
                method TEXT DEFAULT 'GET',
                auth_type TEXT DEFAULT 'none',
                auth_key_encrypted TEXT,
                auth_header_name TEXT DEFAULT 'Authorization',
                params_example TEXT,
                response_path TEXT,
                capability_tags TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_uac_user ON user_api_configs(user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_uac_name ON user_api_configs(api_name)")
        print("[db] user_api_configs ok")
        # ===== P2.6 end =====
'''

def main():
    content = open(TARGET, "r", encoding="utf-8").read()
    if MARKER in content:
        print("already patched, skip")
        return
    anchor = "if __name__ == '__main__':"
    if anchor not in content:
        print("ERROR: anchor not found")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, TARGET + ".bak_p2_6_" + ts)
    print("backup: " + TARGET + ".bak_p2_6_" + ts)
    idx = content.rfind(anchor)
    new_content = content[:idx] + SQL_BLOCK + "\n" + content[idx:]
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched: " + TARGET)

if __name__ == "__main__":
    main()