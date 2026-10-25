# core/api_routes/upload_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import upload_service

router = APIRouter(prefix="/upload", tags=["upload"])
security = HTTPBearer()


class UploadBody(BaseModel):
    original_name: str
    base64_data: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/image")
async def upload_image(body: UploadBody, user_id: int = Depends(get_current_user)):
    result = upload_service.upload_base64(user_id, body.original_name, body.base64_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'upload failed'))
    return result


@router.post("/file")
async def upload_file(body: UploadBody, user_id: int = Depends(get_current_user)):
    result = upload_service.upload_base64(user_id, body.original_name, body.base64_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'upload failed'))
    return result