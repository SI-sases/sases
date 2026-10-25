"""core/hive/identity.py —— 节点身份（Ed25519）。

每个节点有唯一的密钥对，存于 hive-nodes/{node_id}/key.pem。
首次调用 load_or_create_key() 时自动生成，之后复用。
"""
import os
import base64

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def _key_dir(node_id):
    return os.path.join('hive-nodes', node_id)


def _key_path(node_id):
    return os.path.join(_key_dir(node_id), 'key.pem')


def load_or_create_key(node_id):
    """首次调用时生成密钥，后续从磁盘加载。"""
    path = _key_path(node_id)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    os.makedirs(_key_dir(node_id), exist_ok=True)
    key = ed25519.Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(path, 'wb') as f:
        f.write(pem)
    return key


def get_public_key_b64(node_id):
    """返回当前节点公钥的 base64 字符串。"""
    key = load_or_create_key(node_id)
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(pub).decode()


def sign(node_id, data):
    """对 bytes 签名，返回 base64 字符串。"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    key = load_or_create_key(node_id)
    return base64.b64encode(key.sign(data)).decode()


def verify(public_key_b64, signature_b64, data):
    """验签。失败返回 False。"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        pub.verify(sig_bytes, data)
        return True
    except Exception:
        return False


def get_key_fingerprint(node_id):
    """返回公钥的短指纹（前 16 字符），用于日志显示。"""
    pub = get_public_key_b64(node_id)
    import hashlib
    return hashlib.sha256(pub.encode()).hexdigest()[:16]
