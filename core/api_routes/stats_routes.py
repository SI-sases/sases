# core/api_routes/stats_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/leaderboard")
async def get_leaderboard(user_id: int = Depends(get_current_user)):
    leaderboard = stats_service.get_leaderboard()
    return {"leaderboard": leaderboard}


@router.get("/harness-modules")
async def get_harness_modules(user_id: int = Depends(get_current_user)):
    modules = stats_service.get_harness_modules()
    return {"modules": modules}


@router.get("/llm-usage")
async def get_llm_usage(days: int = 7, user_id: int = Depends(get_current_user)):
    from ..services import llm_usage_service
    return {
        "summary": llm_usage_service.summary(user_id, days),
        "recent": llm_usage_service.recent(user_id, 20),
    }


@router.get("/agent-runs")
async def get_agent_runs(days: int = 7, user_id: int = Depends(get_current_user)):
    from datetime import datetime, timedelta
    from ..db import db_cursor
    from ..services import llm_usage_service
    cut = (datetime.utcnow() - timedelta(days=max(1, int(days or 7)))).isoformat()
    with db_cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS n FROM supervisor_runs WHERE created_at>=? GROUP BY status",
            (cut,),
        )
        by_status = {r["status"]: r["n"] for r in cur.fetchall()}
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)
    failed = by_status.get("failed", 0) + by_status.get("plan_failed", 0)
    usage = llm_usage_service.summary(user_id, days)
    return {
        "days": days,
        "runs": {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": by_status.get("running", 0),
            "success_rate": round(completed / total, 4) if total else 0.0,
            "by_status": by_status,
        },
        "llm": usage,
    }
