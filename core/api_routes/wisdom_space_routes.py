# core/api_routes/wisdom_space_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import wisdom_space_service

router = APIRouter(prefix="/wisdom-space", tags=["wisdom-space"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/nodes")
async def get_nodes(user_id: int = Depends(get_current_user)):
    nodes = wisdom_space_service.get_nodes(user_id)
    return {"nodes": nodes}
