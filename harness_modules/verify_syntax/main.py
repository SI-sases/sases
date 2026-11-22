"""verify_syntax：统一走 syntax_service（Python compile + tree-sitter JS）。"""
import os


def run(params):
    file_path = str(params.get("file_path", "") or "")
    if not file_path or not os.path.isfile(file_path):
        return {"success": False, "syntax_ok": False, "error": "File not found"}
    try:
        from core.services.syntax_service import check
        r = check(file_path)
    except Exception as e:
        # 独立使用工具目录时兜底
        if not file_path.lower().endswith(".py"):
            return {"success": False, "syntax_ok": False, "error": "syntax checker unavailable: " + str(e)}
        try:
            import ast
            ast.parse(open(file_path, encoding="utf-8").read())
            r = {"ok": True, "engine": "ast"}
        except Exception as e2:
            r = {"ok": False, "engine": "ast", "error": str(e2)}
    out = {"success": bool(r.get("ok")), "syntax_ok": bool(r.get("ok")),
           "engine": r.get("engine")}
    if not r.get("ok"):
        out["error"] = r.get("error") or "syntax error"
        if r.get("line"):
            out["line"] = r["line"]
    return out
