import os
import re

def fix_harness_runtime():
    p = "core/harness_runtime.py"
    if not os.path.exists(p):
        print("❌ 找不到 core/harness_runtime.py")
        return
    c = open(p, "r", encoding="utf-8").read()
    if "_invoke_tool_legacy" in c:
        print("✅ [1/2] 工具分派逻辑已存在")
        return

    # 1. 改名原函数
    c = c.replace(
        "def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:",
        "def _invoke_tool_legacy(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:"
    )
    
    # 2. 注入新的分派函数
    new_func = '''
    async def invoke_tool(self, module_id: str, params: Dict[str, Any] = None) -> ToolInvokeResponse:
        import sqlite3
        try:
            conn = sqlite3.connect('users.db')
            cur = conn.cursor()
            cur.execute("SELECT api_category FROM api_registry WHERE api_id=?", (module_id,))
            row = cur.fetchone()
            conn.close()
            cat = row[0] if row else 'harness'
        except Exception:
            cat = 'harness'
        
        if cat == 'render':
            return ToolInvokeResponse(module_id=module_id, success=True, result={"status": "rendered", "render": module_id, "params": params})
        
        return self._invoke_tool_legacy(module_id, params or {})
'''
    # 插入在改名的原函数之前
    match = re.search(r'(\s+)def _invoke_tool_legacy', c)
    if match:
        c = c[:match.start()] + "\n" + new_func + c[match.start():]
        open(p, "w", encoding="utf-8").write(c)
        print("✅ [1/2] 工具分派逻辑已成功注入 (harness_runtime.py)")
    else:
        print("❌ 找不到 _invoke_tool_legacy 的插入位置")

def fix_harness_routes():
    p = "core/api_routes/harness_routes.py"
    if not os.path.exists(p):
        print("❌ 找不到 core/api_routes/harness_routes.py")
        return
    c = open(p, "r", encoding="utf-8").read()
    if "verify_exec_token" in c:
        print("✅ [2/2] L3 执行门禁已存在")
        return

    # 1. 导入
    if "from ..services.license_service import get_cached_exec_token, verify_exec_token" not in c:
        c = c.replace(
            "from fastapi import APIRouter",
            "from fastapi import APIRouter\nfrom ..services.license_service import get_cached_exec_token, verify_exec_token"
        )
    
    # 2. 注入门禁逻辑
    gate_code = '''
    # ===== L3 执行层门禁 =====
    _tok = get_cached_exec_token()
    if not verify_exec_token(_tok):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="exec_token_invalid")
    # =======================
'''
    anchor = 'async def execute(body: ExecuteRequest, user_id: int = Depends(get_current_user)):'
    if anchor in c:
        c = c.replace(anchor, anchor + "\n" + gate_code)
        open(p, "w", encoding="utf-8").write(c)
        print("✅ [2/2] L3 执行门禁已成功注入 (harness_routes.py)")
    else:
        print("❌ 找不到 execute 函数的插入位置")

if __name__ == "__main__":
    fix_harness_runtime()
    fix_harness_routes()