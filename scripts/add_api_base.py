import os
import sqlite3

def add_api_base():
    print("🛠 正在添加 API 底座...")
    
    # 1. 建表（api_registry, user_api_configs）
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS api_registry (api_id TEXT PRIMARY KEY, endpoint TEXT, description TEXT, params_schema TEXT, capability_tags TEXT, api_category TEXT DEFAULT 'harness', task_mode TEXT DEFAULT 'sync', status TEXT DEFAULT 'active', created_at TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS user_api_configs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, api_name TEXT NOT NULL, api_desc TEXT, endpoint TEXT NOT NULL, method TEXT DEFAULT 'GET', auth_type TEXT DEFAULT 'none', auth_key_encrypted TEXT, auth_header_name TEXT DEFAULT 'Authorization', params_example TEXT, response_path TEXT, capability_tags TEXT, status TEXT DEFAULT 'active', created_at TEXT NOT NULL)""")
    conn.commit()
    conn.close()
    print("✅ 1. 数据库 api_registry 和 user_api_configs 表已建立")

    # 2. 提取 user_api_routes 并挂载
    os.system("git show 0c56e67:core/api_routes/user_api_routes.py > core/api_routes/user_api_routes.py")
    
    p_init = "core/api_routes/__init__.py"
    c = open(p_init, "r", encoding="utf-8").read()
    if "user_api_routes" not in c:
        c = c.replace("from . import group_routes", "from . import group_routes\nfrom . import user_api_routes")
        open(p_init, "w", encoding="utf-8").write(c)
        
    p_boot = "core/bootstrap.py"
    c = open(p_boot, "r", encoding="utf-8").read()
    if "user_api_routes.router" not in c:
        c = c.replace("app.include_router(group_routes.router)", "app.include_router(group_routes.router)\n    from .api_routes import user_api_routes\n    app.include_router(user_api_routes.router)")
        open(p_boot, "w", encoding="utf-8").write(c)
        
    print("✅ 2. user_api_routes 路由已挂载")