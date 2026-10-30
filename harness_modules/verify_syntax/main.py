import sys
import os
import ast

def run(params):
    file_path = params.get("file_path", "")
    if file_path.lower().endswith((".html", ".css", ".md", ".json")):
        return {"success": True, "message": "Skip AST for non-python file"}
    if not file_path or not os.path.exists(file_path):
        return {"success": False, "error": "File not found"}
    try:
        content = open(file_path, encoding="utf-8").read()
        ast.parse(content)
        return {"success": True, "syntax_ok": True}
    except SyntaxError as e:
        return {"success": False, "syntax_ok": False, "error": str(e)}
