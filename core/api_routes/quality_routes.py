# core/api_routes/quality_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import quality_service, debug_service

router = APIRouter(prefix="/quality", tags=["quality"])
security = HTTPBearer()


class FalsifyRequest(BaseModel):
    title: str
    detail: str = ""
    source_id: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/falsify")
async def submit_falsify(body: FalsifyRequest, user_id: int = Depends(get_current_user)):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    result = quality_service.submit_falsify_issue(
        user_id=user_id,
        title=body.title.strip(),
        detail=body.detail.strip(),
        source_id=body.source_id
    )
    return result


@router.get("/issues")
async def list_issues(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    mine: bool = False,
    limit: int = 50,
    user_id: int = Depends(get_current_user)
):
    filter_user_id = user_id if mine else None
    issues = quality_service.list_issues(source, severity, status, filter_user_id, limit)
    return {"issues": issues}


@router.get("/issues/{issue_id}")
async def get_issue(issue_id: int, user_id: int = Depends(get_current_user)):
    issue = quality_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="记录不存在")
    return issue


@router.post("/issues/{issue_id}/status")
async def update_issue_status(
    issue_id: int,
    body: StatusUpdateRequest,
    user_id: int = Depends(get_current_user)
):
    valid_statuses = ("pending", "cleaning", "cleaned", "archived")
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"状态必须是 {valid_statuses}")
    quality_service.update_status(issue_id, body.status)
    return {"status": "updated", "new_status": body.status}


@router.get("/rescue-pool")
async def get_rescue_pool(limit: int = 20, user_id: int = Depends(get_current_user)):
    """获取可转为智维空间解救任务的待处理问题"""
    pool = quality_service.get_rescue_task_pool(limit)
    return {"tasks": pool}


@router.get("/statistics")
async def get_statistics(user_id: int = Depends(get_current_user)):
    return quality_service.get_statistics()


@router.post("/debug/scan")
async def trigger_debug_scan(sample_limit: int = 20, user_id: int = Depends(get_current_user)):
    """手动触发一次除虫扫描（仅扫描最近 N 条）"""
    report = debug_service.scan_knowledge_base_sample(limit=sample_limit)
    return report


@router.post("/debug/scan-all")
async def trigger_full_scan(batch_size: int = 50, user_id: int = Depends(get_current_user)):
    """手动触发全量除虫扫描（谨慎使用，可能耗时较长）"""
    report = debug_service.scan_all_knowledge_base(batch_size=batch_size)
    return report
