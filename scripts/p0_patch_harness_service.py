# scripts/p0_patch_harness_service.py
import os
import shutil
from datetime import datetime

TARGET = "core/services/harness_service.py"
MARKER = "# ===== P0: render "
ANCHOR = """    base_dir = _get_modules_dir()
    module_dir = os.path.join(base_dir, module_id)
    if not os.path.isdir(module_dir):"""

DISPATCH = """    # ===== P0: render 分类拦截 =====
    try:
        import sqlite3 as _sqlite_p0
        _conn_p0 = _sqlite_p0.connect("users.db")
        _cur_p0 = _conn_p0.cursor()
        _cur_p0.execute("SELECT api_category FROM api_registry WHERE api_id=?", (module_id,))
        _row_p0 = _cur_p0.fetchone()
        _conn_p0.close()
        _cat_p0 = _row_p0[0] if _row_p0 else None
    except Exception:
        _cat_p0 = None
    if _cat_p0 == "render":
        return {
            "status": "rendered",
            "render": module_id,
            "params": params,
            "needs_frontend": True,
            "review_strategy": "skip",
        }
    # ===== P0 end =====

    base_dir = _get_modules_dir()
    module_dir = os.path.join(base_dir, module_id)
    if not os.path.isdir(module_dir):"""

def main():
    if not os.path.exists(TARGET):
        print("no file: " + TARGET)
        return

    content = open(TARGET, "r", encoding="utf-8").read()

    if MARKER in content:
        print("already patched, skip")
        return

    if ANCHOR not in content:
        print("anchor not found")
        return

    backup = TARGET + ".bak_before_p0_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup: " + backup)

    new_content = content.replace(ANCHOR, DISPATCH, 1)
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched: " + TARGET)

if __name__ == "__main__":
    main()