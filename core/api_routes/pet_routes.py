# core/api_routes/pet_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import pet_service

router = APIRouter(prefix="/pet", tags=["pet"])
security = HTTPBearer()


class FeedRequest(BaseModel):
    pet_id: int
    exp_amount: int = 10


class EvolveRequest(BaseModel):
    pet_id: int


class StrengthenRequest(BaseModel):
    pet_id: int
    attribute: str = "strength"


class AwakenRequest(BaseModel):
    pet_id: int


class ReleaseRequest(BaseModel):
    pet_id: int


class CreatePetRequest(BaseModel):
    rarity: str = "C"
    camp: Optional[str] = None
    element: Optional[str] = None
    pet_name: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/list")
async def list_pets(limit: int = 100, user_id: int = Depends(get_current_user)):
    """获取我的所有宠物"""
    pets = pet_service.list_user_pets(user_id, limit=limit)
    return {"pets": pets}


@router.get("/{pet_id}")
async def get_pet(pet_id: int, user_id: int = Depends(get_current_user)):
    """获取宠物详情"""
    pet = pet_service.get_pet(pet_id)
    if not pet:
        raise HTTPException(status_code=404, detail="宠物不存在")
    if pet["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权查看该宠物")
    return pet


@router.post("/feed")
async def feed_pet(body: FeedRequest, user_id: int = Depends(get_current_user)):
    """喂养宠物"""
    result = pet_service.feed_pet(body.pet_id, user_id, body.exp_amount)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/evolve")
async def evolve_pet(body: EvolveRequest, user_id: int = Depends(get_current_user)):
    """进化宠物"""
    result = pet_service.evolve_pet(body.pet_id, user_id)
    return result


@router.post("/strengthen")
async def strengthen_pet(body: StrengthenRequest, user_id: int = Depends(get_current_user)):
    """强化宠物属性"""
    if body.attribute not in ("strength", "hp", "defense"):
        raise HTTPException(status_code=400, detail="属性必须是 strength / hp / defense")
    result = pet_service.strengthen_pet(body.pet_id, user_id, body.attribute)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/awaken")
async def awaken_pet(body: AwakenRequest, user_id: int = Depends(get_current_user)):
    """觉醒宠物，增加技能栏"""
    result = pet_service.awaken_pet(body.pet_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/release")
async def release_pet(body: ReleaseRequest, user_id: int = Depends(get_current_user)):
    """放生宠物"""
    result = pet_service.release_pet(body.pet_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/resources/all")
async def get_all_resources(user_id: int = Depends(get_current_user)):
    """获取所有游戏资源"""
    resources = pet_service.get_all_resources(user_id)
    return {"resources": resources}


@router.get("/resources/{resource_type}")
async def get_resource(resource_type: str, user_id: int = Depends(get_current_user)):
    """查询单个资源数量"""
    amount = pet_service.get_resource(user_id, resource_type)
    return {"resource_type": resource_type, "amount": amount}


@router.get("/statistics/overview")
async def get_statistics(user_id: int = Depends(get_current_user)):
    """获取用户宠物统计"""
    return pet_service.get_statistics(user_id)
