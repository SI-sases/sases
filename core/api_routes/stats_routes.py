from fastapi import APIRouter
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
