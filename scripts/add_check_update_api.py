import ast

PATH = "core/api_routes/version_routes.py"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

if "check-update" in content:
    print("check-update 接口已存在，跳过")
else:
    new_api = '''

@router.post("/version/check-update")
def check_update():
    import subprocess
    has_update = False
    local_hash = ""
    remote_hash = ""
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=os.getcwd(), capture_output=True, timeout=30)
        local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=os.getcwd(), text=True).strip()
        remote_hash = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=os.getcwd(), text=True).strip()
        has_update = local_hash != remote_hash
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"has_update": has_update, "local": local_hash[:7], "remote": remote_hash[:7]}
'''
    content += new_api
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("check-update 接口已追加")

try:
    ast.parse(content)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法错误: {e}")
