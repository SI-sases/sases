import os
from cryptography.fernet import Fernet

from core import config

KEY_FILE = config.API_KEY_ENCRYPTION_KEY_FILE

def _load_or_create_key():
    """加载或创建 Fernet 加密密钥"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

_fernet = Fernet(_load_or_create_key())

def encrypt_text(plain_text: str) -> str:
    """加密字符串，返回加密后的字符串（UTF-8）"""
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_text(cipher_text: str) -> str:
    """解密字符串，返回原始文本"""
    if not cipher_text:
        return ""
    try:
        return _fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""
