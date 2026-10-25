# core/api_routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import user_service

router = APIRouter(prefix="/user", tags=["user"])
security = HTTPBearer()


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    signature: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/profile")
async def get_profile(user_id: int = Depends(get_current_user)):
    profile = user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    return profile


@router.put("/profile")
async def update_profile(body: ProfileUpdateRequest, user_id: int = Depends(get_current_user)):
    user_service.update_user_profile(
        user_id,
        username=body.username,
        gender=body.gender,
        region=body.region,
        signature=body.signature
    )
    return {"status": "updated"}
