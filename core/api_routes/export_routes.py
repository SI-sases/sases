# core/api_routes/export_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import export_service

router = APIRouter(prefix="/export", tags=["export"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/data")
async def export_data(user_id: int = Depends(get_current_user)):
    data = export_service.export_user_data(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="用户不存在")
    return data
