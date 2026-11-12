"""本地 license 验证 + check_exec token 缓存
- verify_license_json: 启动时验 license.json（兼容明文/签名两版）
- get_exec_token: 向云端请求 5 分钟 token（带本地缓存）
- get_cached_exec_token: 给 harness_runtime 用
- record_heartbeat_ok: 心跳成功后记时间（P1-A）
"""
import os
import sys
import json
import time
import base64
import threading
from datetime import datetime

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

# ---------- 公钥路径 ----------
def _find_pub_key():
    """优先 PyInstaller 目录，其次项目根，其次 CWD"""
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS, "core", "keys", "license_pub.pem"))
    candidates.append(os.path.join(os.path.dirname(__file__), "..", "keys", "license_pub.pem"))
    candidates.append(os.path.join(os.getcwd(), "core", "keys", "license_pub.pem"))
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            return p
    return None


_pub_key = None
def _load_pub():
    global _pub_key
    if _pub_key is not None:
        return _pub_key
    if not _HAS_CRYPTO:
        return None
    path = _find_pub_key()
    if not path:
        return None
    with open(path, "rb") as f:
        _pub_key = serialization.load_pem_public_key(f.read())
    return _pub_key


# ---------- 云端 URL ----------
def _cloud_url():
    return os.environ.get("SASES_CLOUD_URL", "http://47.96.87.147:8001").rstrip("/")


# ---------- 进程内 token 缓存 ----------
_cache_lock = threading.Lock()
_token_cache = {"token": None, "expire_at": 0}


def _store_exec_token(token, expire_at):
    with _cache_lock:
        _token_cache["token"] = token
        _token_cache["expire_at"] = int(expire_at or 0)


def get_cached_exec_token():
    with _cache_lock:
        return _token_cache["token"]


# ---------- 启动时：验 license.json ----------
def verify_license_json(path="license.json"):
    """返回 (ok: bool, reason: str)
    兼容两种格式：
      A. 明文：{"user_id":..,"expire_at":"..","key_code":".."}  -> 只验过期
      B. 签名：{"user_id":..,"device_fp":"..","expire_at":"..","sig":".."}  -> 验签 + 验过期
    """
    if not os.path.exists(path):
        return False, "no_license"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"parse_error:{e}"

    expire_at = data.get("expire_at")
    if not expire_at:
        return False, "no_expire_at"

    # 过期判断（本地时间，仅辅助；真正过期以云端 check_exec 为准）
    try:
        if expire_at < datetime.utcnow().isoformat()[:len(expire_at)]:
            return False, "expired_local"
    except Exception:
        pass

    # 如果有 sig 字段，走签名验证
    if "sig" in data and "device_fp" in data:
        if not _HAS_CRYPTO:
            return False, "no_crypto"
        pub = _load_pub()
        if pub is None:
            return False, "no_pub_key"
        try:
            msg = f"{data['user_id']}|{data['device_fp']}|{data['expire_at']}".encode("utf-8")
            sig = base64.b64decode(data["sig"])
            pub.verify(sig, msg)
            return True, "ok_signed"
        except Exception as e:
            return False, f"sig_invalid:{e}"

    # 明文格式：仅允许通过但打 warning（P0-C 兼容期）
    return True, "ok_legacy_plaintext"


# ---------- 向云端拿 token ----------
def get_exec_token(user_id, device_fp, task_hash=None):
    """返回 token 字符串；失败返回 None
    命中本地缓存 5 分钟内直接返回
    """
    now = time.time()
    with _cache_lock:
        if _token_cache["token"] and _token_cache["expire_at"] - 30 > now:
            return _token_cache["token"]

    import httpx
    url = f"{_cloud_url()}/auth/check_exec"
    try:
        r = httpx.post(
            url,
            json={"user_id": int(user_id), "device_fp": str(device_fp), "task_hash": task_hash},
            timeout=5.0,
            trust_env=False,
        )
        data = r.json()
    except Exception:
        # 云端不可达 -> 走降级
        return _fallback_token(user_id, device_fp)

    if not data.get("allowed"):
        return None

    token = data.get("token")
    expire_at = data.get("expire_at") or (int(now) + 300)
    _store_exec_token(token, expire_at)
    return token


# ---------- 验证 token（本地） ----------
def verify_exec_token(token):
    """验证 token：解析 payload，验签，检查 exp"""
    if not token:
        return False
    if token == "offline":
        # 降级路径
        try:
            load_heartbeat_state()
        except Exception:
            pass
        return (time.time() - _last_heartbeat_ok) <= 2 * 3600

    try:
        obj = json.loads(token) if isinstance(token, str) else token
        payload = obj["payload"]
        sig_b64 = obj["sig"]
    except Exception:
        return False

    # 过期检查
    exp = int(payload.get("exp", 0))
    if exp < int(time.time()):
        return False

    # 验签
    pub = _load_pub()
    if pub is None:
        return False
    try:
        msg = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = base64.b64decode(sig_b64)
        pub.verify(sig, msg)
        return True
    except Exception:
        return False


# ---------- 心跳降级（P1-A 提前写好） ----------
_HEARTBEAT_FILE = os.path.join(os.path.expanduser("~"), ".sases_heartbeat")
_last_heartbeat_ok = 0.0


def record_heartbeat_ok():
    global _last_heartbeat_ok
    _last_heartbeat_ok = time.time()
    try:
        with open(_HEARTBEAT_FILE, "w") as f:
            f.write(str(_last_heartbeat_ok))
    except Exception:
        pass


def load_heartbeat_state():
    global _last_heartbeat_ok
    if _last_heartbeat_ok:
        return
    try:
        with open(_HEARTBEAT_FILE) as f:
            _last_heartbeat_ok = float(f.read().strip())
    except Exception:
        _last_heartbeat_ok = 0.0


def _fallback_token(user_id, device_fp):
    """云端不可达时的降级：2 小时宽限内返回 'offline'，否则 None"""
    load_heartbeat_state()
    if time.time() - _last_heartbeat_ok <= 2 * 3600:
        return "offline"
    return None