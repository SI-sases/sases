import shutil
from datetime import datetime

TARGET = "core/db.py"
MARKER = "# ===== license_keys CDK ====="

SQL_BLOCK = '''
        # ===== license_keys CDK =====
        cur.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key_code TEXT PRIMARY KEY,
                key_type TEXT,
                duration_days INTEGER,
                seed_reward_total REAL,
                seed_reward_daily REAL,
                status TEXT DEFAULT 'unused',
                banned_at TEXT,
                ban_reason TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS device_bindings (
                user_id INTEGER,
                device_fingerprint TEXT,
                license_key TEXT,
                activated_at TEXT,
                expire_at TEXT,
                PRIMARY KEY (user_id, device_fingerprint)
            )
        """)
        print("[db] license_keys CDK ok")
        # ===== CDK end =====
'''

def main():
    content = open(TARGET, "r", encoding="utf-8").read()
    if MARKER in content:
        print("already patched")
        return
    anchor = "if __name__ == '__main__':"
    idx = content.rfind(anchor)
    new_content = content[:idx] + SQL_BLOCK + "\n" + content[idx:]
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched CDK to db.py")

if __name__ == "__main__":
    main()