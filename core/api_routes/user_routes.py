# -*- coding: utf-8 -*-
"""用户公开信息路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import db_cursor
from .auth_routes import get_current_user

router = APIRouter(tags=["user"])

class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    signature: Optional[str] = None

@router.get("/u/{sases_id}")
async def get_user_card(sases_id: str):
    """公开名片页：根据 sases_id 返回用户名、handle、display_name。"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT sases_id, handle, display_name FROM users WHERE sases_id = ?",
            (sases_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "sases_id": row["sases_id"],
        "handle": row["handle"],
        "display_name": row["display_name"],
    }

@router.get("/user/profile")
async def get_user_profile(user_info = Depends(get_current_user)):
    # 兼容 get_current_user 返回字典或直接返回 ID 的情况
    _uid = user_info.get('id', user_info.get('user_id')) if isinstance(user_info, dict) else user_info
    with db_cursor() as cur:
        cur.execute("SELECT id, username, sases_id, handle, display_name, gender, region, signature, credits FROM users WHERE id=?", (_uid,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        return dict(row)

@router.put("/user/profile")
async def update_user_profile(body: UpdateProfileRequest, user_info = Depends(get_current_user)):
    _uid = user_info.get('id', user_info.get('user_id')) if isinstance(user_info, dict) else user_info
    with db_cursor(commit=True) as cur:
        if body.nickname is not None:
            cur.execute("UPDATE users SET display_name=? WHERE id=?", (body.nickname, _uid))
            # 同步更新历史会话的标题
            cur.execute("UPDATE conversations SET title=? WHERE target_user_id=? AND is_friend_chat=1", (body.nickname, _uid))
        if body.gender is not None:
            cur.execute("UPDATE users SET gender=? WHERE id=?", (body.gender, _uid))
        if body.region is not None:
            cur.execute("UPDATE users SET region=? WHERE id=?", (body.region, _uid))
        if body.signature is not None:
            cur.execute("UPDATE users SET signature=? WHERE id=?", (body.signature, _uid))
    return {"status": "updated"}
