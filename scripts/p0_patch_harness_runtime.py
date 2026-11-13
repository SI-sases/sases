# scripts/p0_patch_harness_runtime.py
import os
import shutil
from datetime import datetime

TARGET = "core/harness_runtime.py"
MARKER = "# ===== P0: api_category "
ANCHOR = """    def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
        import time as _t2"""

DISPATCH = """    def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
        # ===== P0: api_category =====
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
            return ToolInvokeResponse(
                module_id=module_id,
                success=True,
                result={
                    "status": "rendered",
                    "render": module_id,
                    "params": params,
                    "needs_frontend": True,
                    "review_strategy": "skip",
                },
            )
        # ===== P0 end =====

        import time as _t2"""

def main():
    if not os.path.exists(TARGET):
        print("no file: " + TARGET)
        return

    content = open(TARGET, "r", encoding="utf-8").read()

    if MARKER in content:
        print("already patched, skip")
        return

    if ANCHOR not in content:
        print("anchor not found, check file structure")
        return

    backup = TARGET + ".bak_before_p0_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup: " + backup)

    new_content = content.replace(ANCHOR, DISPATCH, 1)
    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched: " + TARGET)
    print("  added: render category dispatch (18 lines)")

if __name__ == "__main__":
    main()
