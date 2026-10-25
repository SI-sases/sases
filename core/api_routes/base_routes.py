# core/api_routes/base_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import base_service

router = APIRouter(prefix="/base", tags=["base"])
security = HTTPBearer()


class UpgradeRequest(BaseModel):
    facility_type: str


class CollectRequest(BaseModel):
    facility_type: str


class AssignCaptainRequest(BaseModel):
    facility_type: str
    pet_id: int


class AssignMemberRequest(BaseModel):
    facility_type: str
    pet_id: int


class RemoveMemberRequest(BaseModel):
    facility_type: str
    pet_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/overview")
async def get_overview(user_id: int = Depends(get_current_user)):
    """获取基地总览：所有设施、等级、产出、任职情况"""
    return base_service.get_base_overview(user_id)


@router.get("/facilities")
async def list_facilities(user_id: int = Depends(get_current_user)):
    """列出所有设施"""
    base_service.initialize_facilities(user_id)
    facilities = base_service.list_facilities(user_id)
    return {"facilities": facilities}


@router.get("/facility/{facility_type}")
async def get_facility(facility_type: str, user_id: int = Depends(get_current_user)):
    """获取单个设施详情"""
    facility = base_service.get_facility(user_id, facility_type)
    if not facility:
        raise HTTPException(status_code=404, detail="设施不存在")
    return facility


@router.get("/facility/{facility_type}/upgrade-cost")
async def get_upgrade_cost(facility_type: str, user_id: int = Depends(get_current_user)):
    """查询升级消耗"""
    return base_service.get_upgrade_cost(user_id, facility_type)


@router.post("/upgrade")
async def upgrade_facility(body: UpgradeRequest, user_id: int = Depends(get_current_user)):
    """升级设施"""
    result = base_service.upgrade_facility(user_id, body.facility_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/collect")
async def collect_output(body: CollectRequest, user_id: int = Depends(get_current_user)):
    """收取设施产出"""
    result = base_service.collect_output(user_id, body.facility_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/assign-captain")
async def assign_captain(body: AssignCaptainRequest, user_id: int = Depends(get_current_user)):
    """任命设施队长"""
    result = base_service.assign_captain(user_id, body.facility_type, body.pet_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/assign-member")
async def assign_member(body: AssignMemberRequest, user_id: int = Depends(get_current_user)):
    """添加设施队员"""
    result = base_service.assign_member(user_id, body.facility_type, body.pet_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/remove-member")
async def remove_member(body: RemoveMemberRequest, user_id: int = Depends(get_current_user)):
    """移除设施队员"""
    result = base_service.remove_member(user_id, body.facility_type, body.pet_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
