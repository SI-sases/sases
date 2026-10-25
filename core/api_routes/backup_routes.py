# core/api_routes/backup_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from .. import backup_service

router = APIRouter(prefix="/backup", tags=["backup"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/list")
async def list_backups(user_id: int = Depends(get_current_user)):
    """列出所有备份文件"""
    backups = backup_service.list_backups()
    return {"backups": backups}


@router.post("/create")
async def create_backup(user_id: int = Depends(get_current_user)):
    """手动创建一次备份"""
    result = backup_service.create_backup()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/cleanup")
async def cleanup_backups(user_id: int = Depends(get_current_user)):
    """清理超过保留天数的备份"""
    result = backup_service.cleanup_old_backups()
    return result
