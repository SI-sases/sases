# core/services/user_service.py
from ..db import db_cursor


def get_user_profile(user_id: int):
    """获取用户完整资料"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, username, sases_id, credits, gender, region, signature
            FROM users WHERE id=?
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def update_user_profile(user_id: int, username: str = None, gender: str = None, region: str = None, signature: str = None):
    """更新用户资料，支持昵称、性别、地区、个性签名"""
    fields = []
    values = []

    if username is not None:
        fields.append("username=?")
        values.append(username)
    if gender is not None:
        fields.append("gender=?")
        values.append(gender)
    if region is not None:
        fields.append("region=?")
        values.append(region)
    if signature is not None:
        fields.append("signature=?")
        values.append(signature)

    if not fields:
        return True

    values.append(user_id)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
    with db_cursor(commit=True) as cur:
        cur.execute(sql, values)
    return True
