# core/security.py
import os
import base64
import secrets
import string
import hmac
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET", "sases-dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", "43200"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_sases_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "sases_" + ''.join(secrets.choice(alphabet) for _ in range(8))

def encrypt_api_key(api_key: str) -> str:
    # 当前为简单 base64，后续可升级为 Fernet
    return base64.b64encode(api_key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    # 对应 base64 解码
    return base64.b64decode(encrypted.encode()).decode()

def normalize_provider(provider: str) -> str:
    """将供应商名称标准化，兼容大小写、空格、连字符等"""
    p = provider.lower().replace(" ", "").replace("-", "").replace("_", "")
    if p in ("deepseek", "deepseekai", "deepseekchat"):
        return "deepseek"
    elif p in ("kimi", "moonshot", "moonshotai"):
        return "moonshot"
    elif p in ("openai", "gpt", "chatgpt"):
        return "openai"
    elif p in ("claude", "anthropic"):
        return "claude"
    else:
        return p

# 签名密钥：从环境变量读取，若不存在则生成随机密钥（仅内存，不写文件）
SIGN_KEY = os.environ.get("SIGN_KEY", "").encode()
if not SIGN_KEY:
    SIGN_KEY = os.urandom(32)  # 每次启动都会不同，适合开发环境

def sign_state(data: str) -> str:
    return hmac.new(SIGN_KEY, data.encode(), hashlib.sha256).hexdigest()

def verify_state(data: str, signature: str) -> bool:
    expected = sign_state(data)
    return hmac.compare_digest(expected, signature)
