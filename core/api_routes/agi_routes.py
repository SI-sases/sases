# core/api_routes/agi_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import agi_service

router = APIRouter(prefix="/agi", tags=["agi"])
security = HTTPBearer()


class AGIRequest(BaseModel):
    task_type: str
    content: str
    media_data: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/execute")
async def execute_agi(body: AGIRequest, user_id: int = Depends(get_current_user)):
    try:
        result = await agi_service.execute_agi_task(body.task_type, body.content, body.media_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
