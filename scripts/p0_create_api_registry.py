# scripts/p0_create_api_registry.py
import os
import shutil
from datetime import datetime

TARGET = "core/db.py"
MARKER = "# ===== P0: api_registry ====="

SQL_BLOCK = '''
        # ===== P0: api_registry =====
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_registry (
                api_id TEXT PRIMARY KEY,
                endpoint TEXT,
                description TEXT,
                params_schema TEXT,
                capability_tags TEXT,
                api_category TEXT DEFAULT 'harness',
                task_mode TEXT DEFAULT 'sync',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_api_category ON api_registry(api_category, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_api_status ON api_registry(status)")
        print("[db] api_registry ok")
        # ===== P0 end =====
'''

def main():
    if not os.path.exists(TARGET):
        print("no file:", TARGET)
        return

    content = open(TARGET, "r", encoding="utf-8").read()

    if MARKER in content:
        print("already patched, skip")
        return

    anchor = "if __name__ == '__main__':"
    if anchor not in content:
        print("no anchor")
        return

    backup = TARGET + ".bak_before_p0_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup:", backup)

    idx = content.rfind(anchor)
    new_content = content[:idx] + SQL_BLOCK + "\n" + content[idx:]
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched:", TARGET)

if __name__ == "__main__":
    main()