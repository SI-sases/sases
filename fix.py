# fix.py
import os

# 1. 强行重写 stats_routes.py
code = '''from fastapi import APIRouter
from ..db import db_cursor
from datetime import datetime

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/health")
async def get_health():
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM supervisor_runs WHERE created_at LIKE ?", (f"{today_str}%",))
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM supervisor_runs WHERE created_at LIKE ? AND status='completed'", (f"{today_str}%",))
            success = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM supervisor_runs WHERE status IN ('running', 'running_resumed')")
            running = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM swarm_reviews WHERE created_at LIKE ?", (f"{today_str}%",))
            reviews = cur.fetchone()[0]
        return {"status": "ok", "today_total": total, "today_success": success, "success_rate": round(success / total, 2) if total > 0 else 0, "current_running": running, "today_reviews": reviews}
    except Exception as e:
        return {"status": "error", "message": str(e)}
'''
open('core/api_routes/stats_routes.py', 'w', encoding='utf-8').write(code)

# 2. 强行在 __init__.py 中导入
init_p = 'core/api_routes/__init__.py'
c_init = open(init_p, 'r', encoding='utf-8').read()
if 'stats_routes' not in c_init:
    c_init += '\nfrom . import stats_routes\n'
    open(init_p, 'w', encoding='utf-8').write(c_init)

# 3. 强行在 bootstrap.py 挂载
boot_p = 'core/bootstrap.py'
c_boot = open(boot_p, 'r', encoding='utf-8').read()
if 'stats_routes' not in c_boot.split('from .api_routes import (')[1].split(')')[0]:
    c_boot = c_boot.replace('from .api_routes import (', 'from .api_routes import (\n    stats_routes,')
if 'app.include_router(stats_routes.router)' not in c_boot:
    c_boot = c_boot.replace('app.include_router(license_routes.router)', 'app.include_router(license_routes.router)\n    app.include_router(stats_routes.router)')
open(boot_p, 'w', encoding='utf-8').write(c_boot)

print("✅ 物理重写完成，stats_routes 已死死焊入系统！")
