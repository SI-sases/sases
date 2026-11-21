# core/api_routes/tools_routes.py
# -*- coding: utf-8 -*-
"""工具市场 API：catalog / 安装（ZIP、git 白名单）/ 启停 / 卸载。"""
import hmac
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..db import db_cursor
from .auth_routes import get_current_user_id
from .. import tool_install_service as svc
from ..services import capsule_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/usage")
def tool_usage(days: int = 30, user_id: int = Depends(get_current_user_id)):
    from ..services import tool_usage_service
    return {"days": days, "usage": tool_usage_service.summary(user_id, days)}


@router.get("/slim-report")
def tool_slim_report(days: int = 30, user_id: int = Depends(get_current_user_id)):
    """按真实调用给出工具去留建议；不删除任何工具。"""
    from ..services import tool_usage_service
    from .. import harness_runtime
    usage = {r["tool_id"]: r for r in tool_usage_service.summary(user_id, days)}
    rows = []
    try:
        tools = harness_runtime.harness_runtime.list_tools()
    except Exception:
        tools = []
    for t in tools:
        mid = getattr(t, "module_id", "") or ""
        if not mid:
            continue
        u = usage.get(mid) or {}
        rows.append({
            "tool_id": mid,
            "name": getattr(t, "name", "") or "",
            "core": mid not in harness_runtime.EXTENSION_TOOL_IDS,
            "calls": int(u.get("calls") or 0),
            "success_rate": u.get("success_rate") or 0.0,
            "suggestion": "keep" if int(u.get("calls") or 0) > 0 else "hide_or_archive",
        })
    rows.sort(key=lambda r: (r["calls"], r["core"]))
    return {"days": days, "tools": rows,
            "zero_use": [r["tool_id"] for r in rows if r["calls"] == 0]}

ADMIN_TOKEN_FILE = os.path.join("data", "tools_admin_token.txt")


def _admin_token_ok(request: Request) -> bool:
    token = (request.headers.get("x-admin-token") or "").strip()
    if not token:
        return False
    expected = (os.getenv("SASES_TOOLS_ADMIN_TOKEN") or "").strip()
    if not expected and os.path.exists(ADMIN_TOKEN_FILE):
        try:
            with open(ADMIN_TOKEN_FILE, "r", encoding="utf-8") as f:
                expected = f.read().strip()
        except Exception:
            expected = ""
    return bool(expected) and hmac.compare_digest(token, expected)


def _is_admin_user(user_id: int) -> bool:
    try:
        with db_cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE id=?", (user_id,))
            row = cur.fetchone()
        val = (row["is_admin"] if isinstance(row, dict) else row[0]) if row else 0
        return bool(val)
    except Exception:
        return False


def require_admin(request: Request, user_id: int = Depends(get_current_user_id)):
    if _is_admin_user(user_id) or _admin_token_ok(request):
        return user_id
    raise HTTPException(status_code=403, detail="需要管理员权限（is_admin=1 或 X-Admin-Token）")


@router.get("/catalog")
async def get_catalog(user_id: int = Depends(get_current_user_id)):
    return svc.catalog()


@router.get("/capsules")
async def get_capsules(user_id: int = Depends(get_current_user_id)):
    return capsule_service.list_capsules(user_id)


class GitInstallBody(BaseModel):
    repo: str
    ref: str = ""
    subpath: str = ""
    force: bool = False


@router.post("/install/git")
async def install_git(body: GitInstallBody, request: Request, user_id: int = Depends(get_current_user_id)):
    admin = _is_admin_user(user_id) or _admin_token_ok(request)
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        return svc.install_from_git(body.repo, body.ref, body.subpath, body.force, installed_by=user_id)
    except svc.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="安装失败: " + str(e))


@router.post("/install/zip")
async def install_zip(request: Request, file: UploadFile = File(...),
                      force: bool = False, user_id: int = Depends(get_current_user_id)):
    admin = _is_admin_user(user_id) or _admin_token_ok(request)
    if not admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = await file.read()
    try:
        return svc.install_from_zip(data, filename=file.filename or "", force=force, installed_by=user_id)
    except svc.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="安装失败: " + str(e))


@router.post("/{module_id}/enable")
async def enable_tool(module_id: str, request: Request, user_id: int = Depends(get_current_user_id)):
    if not (_is_admin_user(user_id) or _admin_token_ok(request)):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        return svc.set_enabled(module_id, True)
    except svc.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{module_id}/disable")
async def disable_tool(module_id: str, request: Request, user_id: int = Depends(get_current_user_id)):
    if not (_is_admin_user(user_id) or _admin_token_ok(request)):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        return svc.set_enabled(module_id, False)
    except svc.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{module_id}")
async def delete_tool(module_id: str, request: Request, user_id: int = Depends(get_current_user_id)):
    if not (_is_admin_user(user_id) or _admin_token_ok(request)):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        return svc.uninstall(module_id)
    except svc.InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
