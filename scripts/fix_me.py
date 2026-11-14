import os

p = "core/api_routes/auth_routes.py"
if not os.path.exists(p):
    print("❌ 找不到 auth_routes.py")
    exit()

c = open(p, "r", encoding="utf-8").read()

if "/me" not in c:
    logic = '''
@router.get("/me")
async def get_me(user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else {"error": "User not found"}
'''
    c += logic
    open(p, "w", encoding="utf-8").write(c)
    print("✅ 后端 /auth/me 接口已补全")
else:
    print("✅ 后端 /auth/me 已存在")