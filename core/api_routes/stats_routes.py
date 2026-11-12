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
