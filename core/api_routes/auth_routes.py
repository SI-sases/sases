# core/api_routes/auth_routes.py
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from ..db import db_cursor
from ..auth_service import SECRET_KEY

router = APIRouter(tags=["auth"])
security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ========== 注册校验 ==========
import re

USERNAME_MIN, USERNAME_MAX = 3, 20
PASSWORD_MIN, PASSWORD_MAX = 8, 32


def _is_same_char(s: str) -> bool:
    return len(set(s)) == 1


def _is_sequential(s: str) -> bool:
    if len(s) < 3:
        return False
    diffs = [ord(s[i + 1]) - ord(s[i]) for i in range(len(s) - 1)]
    return all(d == 1 for d in diffs) or all(d == -1 for d in diffs)


def validate_username(username: str):
    if not username:
        return "用户名不能为空"
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        return f"用户名长度需在 {USERNAME_MIN}-{USERNAME_MAX} 字符之间"
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return "用户名只能包含字母、数字、下划线"
    if not re.match(r'^[A-Za-z0-9]', username):
        return "用户名必须以字母或数字开头"
    if _is_same_char(username):
        return "用户名不能全部是同一个字符"
    if _is_sequential(username):
        return "用户名不能是连续字符序列（如 123456、abcdef）"
    return None


def validate_password(password: str, username: str):
    if not password:
        return "密码不能为空"
    if not (PASSWORD_MIN <= len(password) <= PASSWORD_MAX):
        return f"密码长度需在 {PASSWORD_MIN}-{PASSWORD_MAX} 字符之间"
    if not re.search(r'[A-Za-z]', password):
        return "密码必须包含字母"
    if not re.search(r'\d', password):
        return "密码必须包含数字"
    if _is_same_char(password):
        return "密码不能全部是同一个字符"
    if _is_sequential(password):
        return "密码不能是连续字符序列"
    if password.lower() == username.lower():
        return "密码不能与用户名相同"
    return None


def validate_email(email: str):
    if not email:
        return None
    if len(email) > 120:
        return "邮箱过长"
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return "邮箱格式不正确"
    return None

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_minutes: int = 60 * 24 * 30) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def generate_sases_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "sases_" + ''.join(secrets.choice(alphabet) for _ in range(8))

def ensure_sases_id(user_id: int, cur) -> str:
    """确保用户拥有 sases_id，若没有则生成并更新"""
    cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    sases_id = row["sases_id"] if row else None
    if not sases_id:
        sases_id = generate_sases_id()
        cur.execute("UPDATE users SET sases_id=? WHERE id=?", (sases_id, user_id))
    return sases_id

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """返回用户字典，包含 id、username、sases_id"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id, username, sases_id FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        sases_id = ensure_sases_id(user_id, cur)

    return {
        "id": user["id"],
        "username": user["username"],
        "sases_id": sases_id
    }

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """返回纯用户ID（整数），供其他模块使用"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.post("/token")
async def login_for_access_token(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空")
    return await _login(username, password)

@router.post("/auth/login")
async def login_json(body: dict):
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空")
    return await _login(username, password)

async def _login(username: str, password: str):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="密码错误")

        # 确保 sases_id 存在
        sases_id = ensure_sases_id(user["id"], cur)

    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "username": user["username"],
        "sases_id": sases_id
    }

@router.post("/auth/register")
async def register(body: RegisterRequest):
    username = body.username.strip()
    password = body.password
    email = (body.email or "").strip() or None

    err = validate_username(username)
    if err:
        raise HTTPException(status_code=400, detail=err)

    err = validate_password(password, username)
    if err:
        raise HTTPException(status_code=400, detail=err)

    err = validate_email(email or "")
    if err:
        raise HTTPException(status_code=400, detail=err)

    password_hash = hash_password(password)
    sases_id = generate_sases_id()
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="用户名已存在")
            if email:
                cur.execute("SELECT id FROM users WHERE email=?", (email,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="该邮箱已被使用")
            cur.execute(
                "INSERT INTO users (username, password_hash, sases_id, email) VALUES (?, ?, ?, ?)",
                (username, password_hash, sases_id, email)
            )
            user_id = cur.lastrowid
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {e}")

    token = create_access_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
        "sases_id": sases_id
    }

class ResetPasswordRequest(BaseModel):
    username: str
    email: str
    new_password: str


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    username = body.username.strip()
    email = (body.email or "").strip()
    new_password = body.new_password

    if not username or not email or not new_password:
        raise HTTPException(status_code=422, detail="用户名、邮箱、新密码不能为空")

    err = validate_password(new_password, username)
    if err:
        raise HTTPException(status_code=400, detail=err)

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE username=? AND email=?", (username, email))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户名与邮箱不匹配")
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), row["id"]))

    return {"status": "ok", "message": "密码已重置，请用新密码登录"}



@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["id"],
        "username": user["username"],
        "sases_id": user["sases_id"]
    }
